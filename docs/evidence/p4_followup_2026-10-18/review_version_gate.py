#!/usr/bin/env python3
"""Independently compare completed 1.2.0 gate rows and archive; no detector runs."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULT = ROOT / "docs/evidence/version_1.2.0_2026-10-18"
SOURCE = Path("/home/resense/data/version_1_2_0_candidate")
WORK = Path("/home/resense/data/version_1_2_0_gate_work")
CONTROL = Path("/home/resense/data/final_gate_work_cecab1b")
COMMIT = "e9d8fc649f2dd51dd5cd1e4b04ac8c306cc02569"
NATIVE = "511f7766639f0ddab471a77263f7a343de19d0a8217dd7cd3a11635c8a7db2c8"
PIECES = [
    "doubleT_obstacle",
    "doubleT_platform",
    "roundT_doubleT",
    "roundT_pressureGate_roundT",
    "roundT_squareT_pressureGate_squareT",
    "squareT_platform_squareT_switch",
    "cloud_with_fake_obj",
    *(f"new_data_{i}" for i in range(8)),
]


def read(path: Path) -> dict:
    return json.loads(path.read_bytes())


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value: bool, message: str) -> None:
    if not value:
        raise ValueError(message)


def operational(row: dict) -> dict:
    """Remove only the recorded latency telemetry; preserve decision health."""
    row = deepcopy(row)
    row.pop("timing_ms")
    health = row["health"]
    for key in ("latency_p95_ms", "latency_basis", "latency_sample_age_frames"):
        health.pop(key, None)
    messages = health["messages"]
    clean = [message for message in messages if not message.startswith("latency p95 ")]
    if clean != messages and health["level"] == "warn":
        require(
            health["decision_level"] in ("ok", "warn", "error"),
            "missing decision health",
        )
        health["level"] = health["decision_level"]
    health["messages"] = clean
    return row


def intervals(rows: list[dict]) -> list[list[int]]:
    spans = []
    for index, row in enumerate(rows):
        if row["obstacle"]:
            if spans and spans[-1][1] == index - 1:
                spans[-1][1] = index
            else:
                spans.append([index, index])
    return spans


def review() -> dict:
    receipt = read(RESULT / "gate_execution.json")
    require(
        receipt["status"] == "finished" and receipt["returncode"] == 0,
        "producer incomplete",
    )
    require(receipt["source_commit"] == COMMIT, "wrong candidate source")
    require(
        receipt["source_unchanged"] and receipt["native_unchanged"],
        "producer source drift",
    )
    core = receipt["source_files"]
    historical = read(ROOT / "docs/evidence/detector_freeze_2026-10-18_lidar.json")
    require(
        set(core) == set(historical["files"]) and len(core) == 38,
        "wrong frozen inventory",
    )
    for name, expected in core.items():
        data = subprocess.check_output(
            ["git", "show", f"{COMMIT}:{name}"], cwd=ROOT, timeout=30
        )
        require(
            hashlib.sha256(data).hexdigest() == expected == sha(SOURCE / name),
            f"source mismatch {name}",
        )
    digest = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    require(digest == receipt["source_sha256"], "wrong combined source digest")
    require(len(receipt["native_libraries"]) == 1, "wrong native inventory")
    for name, expected in receipt["native_libraries"].items():
        require(expected == NATIVE == sha(SOURCE / name), "native binary mismatch")
    for name, expected in receipt["input_receipt_sha256"].items():
        require(sha(Path(name)) == expected, "intake receipt mismatch")
    require(
        receipt["preflight"]
        == {"version": "1.2.0", "native": True, "replay_default": 0},
        "wrong defaults",
    )
    report = read(RESULT / "gate.json")
    require(
        sha(RESULT / "gate.json") == receipt["report_sha256"],
        "producer report mismatch",
    )
    require(
        report["code"]["commit"] == COMMIT
        and report["code"]["uncommitted_detector_changes"] == [],
        "uncommitted or wrong measured source",
    )
    require(
        report["config"]["set"] == [] and report["run"]["nominal_stamps"] is False,
        "overridden input/config",
    )
    gate = report["gate"]
    require(gate["passed"] is True and gate["same"] == 208, "gate not complete/equal")
    for key in (
        "allow",
        "worse_gated",
        "missing_gated",
        "worse_allowed",
        "missing_allowed",
    ):
        require(gate[key] == [], f"gate has {key}")
    author = read(RESULT / "gate_acceptance.json")
    require(
        author["status"] == "COMPLETE_GATE_AND_VERSION_ONLY_PARITY_PASS",
        "author verification incomplete",
    )
    for name, expected in author["input_sha256"].items():
        require(sha(Path(name)) == expected, "author review input changed")
    frame_review = read(RESULT / "gate_frame_review.json")
    expected_names = {f"{name}.jsonl" for name in PIECES}
    for key in ("reference_raw_hashes", "candidate_raw_hashes"):
        require(
            set(frame_review[key]) == expected_names,
            "wrong complete-review raw inventory",
        )
    reference_report = (
        ROOT / "docs/evidence/lidar_adaptation_2026-10-18/default_off/gate.json"
    )
    require(
        sha(reference_report) == historical["validation"]["sha256"],
        "historical gate changed",
    )
    scored_inputs = {
        str(reference_report),
        str(RESULT / "gate.json"),
        str(CONTROL / "setF_straight.json"),
        str(WORK / "setF_straight.json"),
        str(ROOT / "docs/evidence/lidar_adaptation_2026-10-18/review_gate_frames.py"),
    }
    require(
        set(frame_review["input_sha256"]) == scored_inputs,
        "unexpected complete-review inputs",
    )
    for name, expected in frame_review["input_sha256"].items():
        require(sha(Path(name)) == expected, "complete-scoring review input changed")
    require(
        (CONTROL / "config.yaml").read_bytes() == (WORK / "config.yaml").read_bytes(),
        "effective work configurations differ",
    )

    pieces = []
    for name in PIECES:
        paths = [folder / f"{name}.jsonl" for folder in (CONTROL, WORK)]
        require(
            sha(paths[0]) == frame_review["reference_raw_hashes"][paths[0].name],
            "reference raw changed after complete-scoring review",
        )
        require(
            sha(paths[1]) == frame_review["candidate_raw_hashes"][paths[1].name],
            "candidate raw changed after complete-scoring review",
        )
        before, after = [
            [json.loads(line) for line in path.read_text().splitlines()]
            for path in paths
        ]
        require(len(before) == len(after) > 0, f"row count mismatch {name}")
        for index, (left, right) in enumerate(zip(before, after, strict=True)):
            require(
                operational(left) == operational(right),
                f"operational difference {name}:{index}",
            )
        require(
            intervals(before) == intervals(after), f"STOP interval difference {name}"
        )
        pieces.append(
            {
                "name": name,
                "rows": len(after),
                "stop_frames": sum(r["obstacle"] for r in after),
                "stop_intervals": intervals(after),
                "reference_sha256": sha(paths[0]),
                "candidate_sha256": sha(paths[1]),
            }
        )
    require(sum(p["rows"] for p in pieces) == 15269, "incomplete ordinary coverage")
    require(sum(p["stop_frames"] for p in pieces) == 805, "wrong ordinary STOP count")
    require(
        sum(len(p["stop_intervals"]) for p in pieces) == 51, "wrong STOP interval count"
    )

    old_f, new_f = [read(folder / "setF_straight.json") for folder in (CONTROL, WORK)]
    require(
        old_f["parameters"] == new_f["parameters"], "Set F protocol/input differences"
    )
    require(
        old_f["sequences"] == new_f["sequences"], "Set F placement/scoring differences"
    )
    keys = {(s["kind"], int(s["file0"].split("_")[2])) for s in new_f["sequences"]}
    expected_keys = {
        (kind, start)
        for kind in ("person", "box1.0", "box0.5", "trolley", "cable")
        for start in (46, 68, 98, 140, 168, 172)
    }
    require(
        keys == expected_keys and len(new_f["sequences"]) == 30,
        "incomplete Set F membership",
    )
    require(
        sum(len(s["rows"]) for s in new_f["sequences"]) == 3060, "incomplete Set F rows"
    )
    require(
        sum(r["hit"] for s in new_f["sequences"] for r in s["rows"]) == 1064,
        "wrong Set F hits",
    )

    manifest_path = RESULT / "raw/gate_manifest.json"
    manifest = read(manifest_path)
    archive_path = RESULT / "raw/gate.tar.gz"
    require(sha(archive_path) == manifest["archive_sha256"], "archive hash mismatch")
    members = {row["member"]: row for row in manifest["members"]}
    expected_members = {f"gate/work/{name}.jsonl" for name in PIECES}
    expected_members |= {
        "gate/work/config.yaml",
        "gate/work/setF_straight.json",
        "gate/report.json",
        "gate/run/status.json",
        "gate/run/wrapper.py",
        "gate/run/console.txt",
        "gate/run/wrapper_console.txt",
    }
    expected_members |= {
        f"gate/intake/{Path(name).name}" for name in receipt["input_receipt_sha256"]
    }
    require(set(members) == expected_members, "wrong archive member inventory")
    require(
        len(members) == len(manifest["members"]) == manifest["member_count"],
        "duplicate archive manifest",
    )
    seen = set()
    with tarfile.open(archive_path, "r:gz") as archive:
        for info in archive:
            require(
                info.isfile() and info.name in members and info.name not in seen,
                "unexpected archive entry",
            )
            entry = members[info.name]
            with archive.extractfile(info) as stream:
                data = stream.read()
            require(
                info.size == entry["bytes"] == len(data), "archive member size mismatch"
            )
            require(
                hashlib.sha256(data).hexdigest()
                == entry["sha256"]
                == sha(Path(entry["source"])),
                "archive/source member hash mismatch",
            )
            seen.add(info.name)
    require(seen == expected_members, "missing archive member")
    inputs = [
        Path(__file__),
        RESULT / "finalize_gate.py",
        RESULT / "gate.json",
        RESULT / "gate_execution.json",
        RESULT / "gate_acceptance.json",
        RESULT / "gate_frame_review.json",
        manifest_path,
        HERE / "source_continuity.json",
    ]
    return {
        "status": "INDEPENDENT_VERSION_GATE_REVIEW_PASS",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": COMMIT,
        "source_sha256": digest,
        "ordinary_rows": 15269,
        "ordinary_stop_frames": 805,
        "ordinary_stop_intervals": 51,
        "pieces": pieces,
        "set_F_sequences": 30,
        "set_F_rows": 3060,
        "set_F_hits": 1064,
        "archive_members": len(seen),
        "archive_sha256": sha(archive_path),
        "input_sha256": {str(p): sha(p) for p in inputs},
        "limits": [
            "Final P4 acceptance remains pending; this is an agent evidence-integrity and parity review.",
            "No detector was run. Recorded rows are serialized outputs, not all full-precision internals.",
            "Set F is shared scoring/placement equality; full detections are absent, so no independent reassociation.",
            "Only recorded latency telemetry was normalized; shared-host timing proves no throughput gain.",
            "Existing X3/Falcon/DDS retain their prior identities; this is the fresh default gate only.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=HERE / "version_gate_review.json")
    args = parser.parse_args()
    result = review()
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])


if __name__ == "__main__":
    main()
