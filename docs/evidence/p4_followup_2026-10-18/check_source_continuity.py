#!/usr/bin/env python3
"""Verify the copied P4 reports and two immutable Git source inventories.

No detector is imported or executed. Historical equality ends at cf18848;
the separate e9d8fc6 proof permits only the four declared version replacements.
Neither source check constitutes P4 release acceptance.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path

P4_COMMIT = "1b880168ce2dbeec2071838892ac05eed5a9166a"
CHECKED = "b4235623327f084e84b2a8c582655548b29140c9"
COMPLETED = "cf188486f5c2339cd74adcb52ecdd21a59f8fad0"
MEASURED = "cecab1b696b8c2e101207601acd8faed96c8bfb8"
CANDIDATE = "e9d8fc649f2dd51dd5cd1e4b04ac8c306cc02569"
P4_DIRECTORY = "docs/evidence/p1_branch_check_2026-10-18"
SEAL = "docs/evidence/detector_freeze_2026-10-18_lidar.json"
SEAL_SHA256 = "f75231a9d52124620ec7f23ee7ecf0050bf4e668ee2e10fdb660c3dba06bbc3c"
FROZEN_DIRECTORIES = (
    "resense/",
    "native/",
    "configs/",
    "ros2_ws/src/resense_ros/config/",
)
BUILD_FILES = {"setup.py", "pyproject.toml", "scripts/build_native.sh"}
ROS_PACKAGE = "ros2_ws/src/resense_ros/"
REPLAY_FILES = {
    "scripts/check_interactive_replay.py",
    "scripts/replay_node_frames.py",
    "scripts/reset_replay.py",
    "scripts/play_bag.sh",
    "scripts/run_demo.sh",
    "scripts/record_rviz_chain.sh",
    "docs/evidence/n1_n4_2026-10-18/replay_gauge.py",
}
GAUGE_FILES = {
    "resense/gauge.py",
    "resense/config.py",
    "configs/default.yaml",
    "ros2_ws/src/resense_ros/config/detector.yaml",
    "ros2_ws/src/resense_ros/resense_ros/gauge_display.py",
    "ros2_ws/src/resense_ros/resense_ros/decision_policy.py",
    "ros2_ws/src/resense_ros/resense_ros/detector_node.py",
    "ros2_ws/src/resense_ros/launch/detector.launch.py",
    "ros2_ws/src/resense_ros/rviz/resense.rviz",
}
VERSION_PATTERNS = {
    "pyproject.toml": r'(?m)^version\s*=\s*"([^"]+)"',
    "resense/__init__.py": r'(?m)^__version__\s*=\s*"([^"]+)"',
    "ros2_ws/src/resense_ros/package.xml": r"<version>\s*([^<\s]+)\s*</version>",
    "ros2_ws/src/resense_ros/setup.py": r'(?m)^\s*version\s*=\s*"([^"]+)"',
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repo: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args], timeout=30)


def blob(repo: Path, commit: str, path: str) -> bytes:
    return git(repo, "show", f"{commit}:{path}")


def inventory(repo: Path, commit: str) -> set[str]:
    return set(git(repo, "ls-tree", "-r", "--name-only", commit).decode().splitlines())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def version_only(repo: Path, paths: set[str], frozen: set[str]) -> dict:
    """Prove actual committed candidate edits, without waiving its fresh gate."""
    changed = set(
        git(repo, "diff", "--name-only", COMPLETED, CANDIDATE).decode().splitlines()
    )
    documents = {"CHANGELOG.md", "docs/evidence/version_1.2.0_2026-10-18/PLAN.md"}
    require(
        changed == set(VERSION_PATTERNS) | documents,
        "unexpected candidate change scope",
    )
    candidate_names = inventory(repo, CANDIDATE)
    require(
        {
            p
            for p in candidate_names
            if p.startswith(FROZEN_DIRECTORIES) or p in BUILD_FILES
        }
        == frozen,
        "candidate frozen inventory changed",
    )
    old_names = inventory(repo, COMPLETED)
    require(
        {p for p in candidate_names if p.startswith(ROS_PACKAGE)}
        == {p for p in old_names if p.startswith(ROS_PACKAGE)},
        "candidate ROS inventory changed",
    )
    version_rows = {}
    for path in sorted(paths | set(VERSION_PATTERNS)):
        old = blob(repo, COMPLETED, path)
        new = blob(repo, CANDIDATE, path)
        if path in VERSION_PATTERNS:
            text = old.decode()
            match = re.search(VERSION_PATTERNS[path], text)
            require(
                match is not None and match.group(1) == "1.1.0",
                "unexpected version baseline",
            )
            expected = text[: match.start(1)] + "1.2.0" + text[match.end(1) :]
            require(
                new == expected.encode(),
                f"not an exact version-only replacement: {path}",
            )
            require(
                sum(
                    a != b
                    for a, b in zip(old.splitlines(), new.splitlines(), strict=True)
                )
                == 1,
                "expected one changed version line",
            )
            version_rows[path] = {
                "before_sha256": sha(old),
                "candidate_sha256": sha(new),
                "from": "1.1.0",
                "to": "1.2.0",
                "changed_lines": 1,
                "inside_seal": path in frozen,
            }
        else:
            require(old == new, f"candidate changes non-version runtime bytes: {path}")
    return {
        "status": "EXACT_FOUR_VERSION_LINES_WITH_DOCUMENTATION_ONLY",
        "baseline_commit": COMPLETED,
        "candidate_commit": CANDIDATE,
        "all_changed_paths": sorted(changed),
        "documentation_paths": sorted(documents),
        "version_replacements": version_rows,
        "changed_frozen_files": sorted(set(VERSION_PATTERNS) & frozen),
        "scope": "Source diff only; fresh committed gate and final P4 review are separate requirements.",
    }


def check(repo: Path, evidence: Path) -> dict:
    seal_bytes = blob(repo, COMPLETED, SEAL)
    require(sha(seal_bytes) == SEAL_SHA256, "unexpected completed source seal")
    seal = json.loads(seal_bytes)
    require(seal["measured_commit"] == MEASURED, "wrong measured source")
    before = inventory(repo, CHECKED)
    after = inventory(repo, COMPLETED)
    frozen = set(seal["files"])
    require(len(frozen) == 38, "expected exactly 38 frozen files")
    for names in (before, after):
        actual = {
            p for p in names if p.startswith(FROZEN_DIRECTORIES) or p in BUILD_FILES
        }
        require(actual == frozen, "frozen source inventory changed")
    ros = {p for p in after if p.startswith(ROS_PACKAGE)}
    require(
        ros == {p for p in before if p.startswith(ROS_PACKAGE)}, "ROS inventory changed"
    )
    groups = {
        "frozen_source": frozen,
        "actual_ros_node_launch_display_package": ros,
        "replay_and_display_checks": REPLAY_FILES,
        "gauge_contract_and_renderer": GAUGE_FILES,
    }
    rows = {}
    for path in sorted(set.union(*groups.values())):
        old = blob(repo, CHECKED, path)
        new = blob(repo, COMPLETED, path)
        require(old == new, f"source changed: {path}")
        if path in frozen:
            require(sha(new) == seal["files"][path], f"seal hash mismatch: {path}")
        rows[path] = {"sha256": sha(new), "bytes": len(new), "equal": True}
    digest = sha(
        json.dumps(seal["files"], sort_keys=True, separators=(",", ":")).encode()
    )
    require(digest == seal["source_sha256"], "frozen combined digest mismatch")

    intake_path = evidence / "p4_intake_manifest.json"
    intake = json.loads(intake_path.read_bytes())
    require(intake["source_commit"] == P4_COMMIT, "wrong P4 source commit")
    require(intake["checked_work_commit"] == CHECKED, "wrong P4 checked commit")
    source_names = {
        p for p in inventory(repo, P4_COMMIT) if p.startswith(P4_DIRECTORY + "/")
    }
    require(len(source_names) == 5, "expected exactly five original reports")
    require(len(intake["members"]) == 5, "wrong intake member count")
    require(
        {r["source_path"] for r in intake["members"]} == source_names,
        "intake inventory mismatch",
    )
    destinations = set()
    for row in intake["members"]:
        expected_dest = "p4_original/" + Path(row["source_path"]).name
        require(row["destination"] == expected_dest, "unexpected intake destination")
        destinations.add(expected_dest)
        data = blob(repo, P4_COMMIT, row["source_path"])
        require(data == (evidence / expected_dest).read_bytes(), "modified P4 report")
        require(
            sha(data) == row["sha256"] and len(data) == row["bytes"],
            "intake hash/size mismatch",
        )
        require(
            git(repo, "rev-parse", f"{P4_COMMIT}:{row['source_path']}").decode().strip()
            == row["git_blob"],
            "intake Git blob mismatch",
        )
    local_originals = {
        p.relative_to(evidence).as_posix()
        for p in (evidence / "p4_original").rglob("*")
        if p.is_file()
    }
    require(local_originals == destinations, "extra/missing copied P4 report")

    versions = {}
    for path, pattern in VERSION_PATTERNS.items():
        found = re.search(pattern, blob(repo, COMPLETED, path).decode())
        require(
            found is not None and found.group(1) == "1.1.0",
            "unexpected historical version",
        )
        versions[path] = found.group(1)
    return {
        "status": "SOURCE_CONTINUITY_AND_EXACT_REPORT_INTAKE_PASS",
        "checked_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "p4_report_commit": P4_COMMIT,
        "checked_commit": CHECKED,
        "completed_evidence_commit": COMPLETED,
        "measured_core_commit": MEASURED,
        "seal": {"path": SEAL, "sha256": SEAL_SHA256, "source_sha256": digest},
        "groups": {
            name: {"count": len(paths), "paths": sorted(paths)}
            for name, paths in groups.items()
        },
        "unique_compared_files": len(rows),
        "files": rows,
        "version_declarations": versions,
        "candidate_version_only": version_only(repo, set(rows), frozen),
        "p4_report_files_verified": 5,
        "input_sha256": {
            "p4_intake_manifest.json": sha(intake_path.read_bytes()),
            "check_source_continuity.py": sha(Path(__file__).read_bytes()),
        },
        "limits": [
            "Historical equality is b423562-to-cf18848; e9d8fc6 is checked only for exact version-only edits.",
            "Source equality does not extend P4's executed replica checks to the actual ROS node or renderer.",
            "The P4 reports reference external raw captures; those bytes were not imported or reanalysed here.",
            "This is an integrity/continuity receipt, not P4 final safety approval, J1, release or deployment.",
            "No detector, renderer, player or regression gate was executed by this checker.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo", type=Path, default=Path(__file__).resolve().parents[3]
    )
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).with_name("source_continuity.json")
    )
    args = parser.parse_args()
    result = check(args.repo.resolve(), Path(__file__).resolve().parent)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(
        f"PASS: {result['unique_compared_files']} unique source files; five exact P4 reports"
    )


if __name__ == "__main__":
    main()
