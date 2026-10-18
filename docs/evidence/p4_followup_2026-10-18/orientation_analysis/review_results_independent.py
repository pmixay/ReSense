#!/usr/bin/env python3
"""Independently recheck the completed bounded mapping capture; never run Detector."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
from itertools import groupby
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(row):
    value = json.loads(json.dumps(row))
    for field in ("decode_ms", "detect_ms", "total_ms"):
        del value[field]
    for holder, msgkey, decisionkey in (
        (value, "msgs", "dlevel"),
        (value["health_detail"], "messages", "decision_level"),
    ):
        messages = holder[msgkey]
        assert holder[decisionkey] in ("ok", "warn", "error")
        latency = [m for m in messages if m.startswith("latency p95 ")]
        if latency and holder["level"] == "warn":
            holder["level"] = holder[decisionkey]
        holder[msgkey] = [m for m in messages if m not in latency]
    del value["health_detail"]["latency_p95_ms"]
    return value


def spans(indices):
    return [
        [(run := [v for _, v in group])[0], run[-1]]
        for _, group in groupby(enumerate(indices), lambda pair: pair[1] - pair[0])
    ]


def main():
    summary = json.loads((HERE / "summary.json").read_text())
    registration = json.loads((HERE / "registration.json").read_text())
    assert summary["rows"] == registration["maximum_rows"] == 2984
    assert summary["registration_sha256"] == digest(HERE / "registration.json")
    assert summary["source"] == registration["source"]
    assert registration["harness_sha256"] == digest(HERE / "run_mapping.py")
    assert registration["protocol_sha256"] == digest(HERE / "PROTOCOL.md")
    assert summary["source_unchanged"] and summary["harness_unchanged"]
    assert len(summary["source"]["files"]) == 38
    for name, expected in summary["source"]["files"].items():
        data = subprocess.check_output(
            ["git", "show", f"{summary['source']['commit']}:{name}"], cwd=ROOT
        )
        assert hashlib.sha256(data).hexdigest() == expected
    assert set(summary["bags"]) == {
        "doubleT_obstacle",
        "roundT_squareT_pressureGate_squareT",
    }
    report = {
        "status": "INDEPENDENT_EXPLICIT_MAPPING_RESULT_PASS",
        "checked_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": summary["source"]["commit"],
        "bags": {},
        "inputs": {},
    }
    total = 0
    for bag, cases in summary["bags"].items():
        expected = 201 if bag == "doubleT_obstacle" else 545
        assert [c["name"] for c in cases] == [
            "upright",
            "case04_explicit",
            "case05_explicit",
            "case05_wrong",
        ]
        baseline = None
        baseline_stop = None
        report["bags"][bag] = {}
        for case in cases:
            path = HERE / case["raw"]
            assert digest(path) == case["raw_sha256"]
            report["inputs"][case["raw"]] = digest(path)
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            assert len(rows) == case["frames"] == expected
            assert [r["i"] for r in rows] == list(range(expected))
            total += len(rows)
            stops = [r["i"] for r in rows if r["decision"] == "STOP"]
            normalized = [canonical(r) for r in rows]
            if baseline is None:
                baseline, baseline_stop = normalized, stops
            changed = [
                i
                for i, (old, new) in enumerate(zip(baseline, normalized, strict=True))
                if old != new
            ]
            lost, added = (
                sorted(set(baseline_stop) - set(stops)),
                sorted(set(stops) - set(baseline_stop)),
            )
            assert (
                stops == case["stop_indices"] and spans(stops) == case["stop_intervals"]
            )
            assert lost == case["lost_stop"] and added == case["added_stop"]
            assert changed == case["changed_non_timing_rows"]
            assert dict(Counter(r["decision"] for r in rows)) == case["decisions"]
            if case["name"] != "case05_wrong":
                assert not changed and not lost and not added
            report["bags"][bag][case["name"]] = {
                "frames": len(rows),
                "decisions": dict(Counter(r["decision"] for r in rows)),
                "stop_intervals": spans(stops),
                "lost_stop": lost,
                "added_stop": added,
                "changed_non_timing_rows": len(changed),
                "stop_confirmed": sum(
                    r["decision"] == "STOP"
                    and r["mount_detail"]["orientation_confirmed"]
                    for r in rows
                ),
                "stop_status_ok": sum(
                    r["decision"] == "STOP" and r["mount"] == "ok" for r in rows
                ),
                "go_confirmed_status_ok": [
                    r["i"]
                    for r in rows
                    if r["decision"] == "GO"
                    and r["mount"] == "ok"
                    and r["mount_detail"]["orientation_confirmed"]
                ],
            }
    assert total == 2984
    wrong = report["bags"]["roundT_squareT_pressureGate_squareT"]["case05_wrong"]
    assert (
        wrong["stop_confirmed"],
        wrong["stop_status_ok"],
        wrong["go_confirmed_status_ok"],
    ) == (509, 327, [311, 316])
    report["rows"] = total
    report["scope"] = (
        "Captured exact serialized parity for two explicit mappings; wrong automatic mapping remains failed. No ROS, physical-remount, all-24-orientation or final P4 acceptance claim."
    )
    for name in (
        "summary.json",
        "registration.json",
        "PROTOCOL.md",
        "run_mapping.py",
        "execute_mapping.py",
        "HARNESS_REVIEW.md",
        Path(__file__).name,
    ):
        report["inputs"][name] = digest(HERE / name)
    (HERE / "independent_result_review.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps({"status": report["status"], "rows": total}))


if __name__ == "__main__":
    main()
