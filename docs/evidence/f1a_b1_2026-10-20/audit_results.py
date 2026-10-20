#!/usr/bin/env python3
"""Re-derive claims from complete raw outputs, retaining all per-frame differences."""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import regression_gate as gate  # noqa: E402

WORK = Path("/tmp/opencode")


def read(name):
    return json.loads((WORK / f"f1a-b1-{name}.json").read_text())


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def non_timing(row):
    r = deepcopy(row)
    r.pop("timing_ms", None)
    h = r.get("health", {})
    h.pop("latency_p95_ms", None)
    h["messages"] = [m for m in h.get("messages", []) if "latency" not in m]
    return r


def differences(a, b):
    assert len(a) == len(b)
    different, timing_health_only = [], []
    for i, (x, y) in enumerate(zip(a, b)):
        nx, ny = non_timing(x), non_timing(y)
        if nx == ny:
            continue
        # Only forgive health levels when a real latency message explains them.
        latency = any("latency" in m for r in (x, y) for m in r.get("health", {}).get("messages", []))
        if latency:
            for r in (nx, ny):
                r["health"].pop("level", None)
                r["health"].pop("decision_level", None)
            if nx == ny:
                timing_health_only.append(i)
                continue
        different.append({"frame": i, "fields": sorted(k for k in nx.keys() | ny.keys() if nx.get(k) != ny.get(k))})
    return {"frames": len(a), "different": different, "latency_health_only": timing_health_only}


def stop_diff(a, b):
    assert len(a) == len(b)
    return {"lost": [i for i, (x, y) in enumerate(zip(a, b)) if x["obstacle"] and not y["obstacle"]],
            "added": [i for i, (x, y) in enumerate(zip(a, b)) if y["obstacle"] and not x["obstacle"]]}


def ride_summary(rr):
    # Independent counting, without the existing episodes.py helper.
    starts, low_any, prev, in_low = [], 0, False, False
    for r in rr:
        stop = r["obstacle"]
        low = any(d["kind"] == "low" for d in r["detections"])
        if stop and not prev:
            starts.append({"frame": r["frame"], "low_onset": low})
            in_low = False
        if stop and low and not in_low:
            low_any += 1
            in_low = True
        prev = stop
    return {"frames": len(rr), "stop_frames": sum(r["obstacle"] for r in rr),
            "stop_events": len({d["id"] for r in rr if r["obstacle"] for d in r["detections"]}),
            "episodes": starts, "low_onset": sum(r["low_onset"] for r in starts), "low_any": low_any}


def probe_changes(left, right):
    assert len(left) == len(right)
    changed_payloads = []
    for x, y in zip(left, right):
        assert x["i"] == y["i"] and x["frame_id"] == y["frame_id"]
        if x["dets"] != y["dets"] or x["warns"] != y["warns"]:
            changed_payloads.append(x["i"])
    return {"rows": len(left), "changed_payload_frames": changed_payloads, **stop_diff(left, right)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    plain = rows(WORK / "f1a-b1-base-plain.jsonl")
    traced = rows(WORK / "f1a-b1-base-traced.jsonl")
    candidate = rows(WORK / "f1a-b1-ride-final.jsonl")
    assert len(plain) == len(traced) == len(candidate) == 11271
    instrumentation = differences(plain, traced)
    assert not instrumentation["different"], instrumentation["different"][:3]
    control = deepcopy(plain[:1])
    control[0]["obstacle"] = not control[0]["obstacle"]
    assert len(differences(plain[:1], control)["different"]) == 1
    base, final = read("gate-baseline"), read("gate-final")
    comparison = gate.compare(base, final, [])
    work_a, work_b = (WORK / f"f1a-b1-{n}-work" for n in ("gate-baseline", "gate-final"))
    assert {p.name for p in work_a.glob("*.jsonl")} == {p.name for p in work_b.glob("*.jsonl")}
    per_file = {}
    for path in sorted(work_a.glob("*.jsonl")):
        left, right = rows(path), rows(work_b / path.name)
        per_file[path.name] = {**stop_diff(left, right), **differences(left, right)}
    set_f_base, set_f_final = (json.loads((work / "setF_straight.json").read_text()) for work in (work_a, work_b))
    set_f = {"sequences": len(set_f_base["sequences"]),
             "rows": sum(len(s["rows"]) for s in set_f_base["sequences"]),
             "all_sequence_fields_equal": set_f_base["sequences"] == set_f_final["sequences"],
             "all_kind_metrics_equal": base["set_F_straight"]["kinds"] == final["set_F_straight"]["kinds"]}
    assert set_f["sequences"] == 30 and set_f["rows"] == 3060
    control = deepcopy(set_f_base["sequences"])
    control[0]["rows"][0]["hit"] = not control[0]["rows"][0]["hit"]
    assert control != set_f_base["sequences"]
    physical_base, physical_final = read("physical-baseline-v2"), read("physical-final-v2")
    assert set(physical_base) == set(physical_final)
    physical = {}
    for key, left in physical_base.items():
        right = physical_final[key]
        assert len(left) == len(right)
        physical[key] = {"baseline": [r["frame"] for r in left if r["matched_stop"]],
                         "candidate": [r["frame"] for r in right if r["matched_stop"]],
                         "lost": [x["frame"] for x, y in zip(left, right) if x["matched_stop"] and not y["matched_stop"]]}
    falcon_base, falcon_final = (rows(WORK / f"f1a-b1-falcon-{tag}.jsonl") for tag in ("baseline", "final"))
    assert len(falcon_base) == len(falcon_final) == 4443
    x3 = read("x3-final")
    x3_reference = json.loads(Path(x3["reference"]).read_text())
    x3_raw = {key: probe_changes(rows(Path(x3_reference["entries"][key]["raw_path"])),
                                 rows(Path(e["raw_path"]))) for key, e in x3["entries"].items()}
    assert len(x3_raw) == 40 and sum(r["rows"] for r in x3_raw.values()) == 29765
    report = {"instrumentation": instrumentation, "comparer_positive_control": True,
              "ride_base": ride_summary(plain), "ride_candidate": ride_summary(candidate),
              "ride_stop_diff": stop_diff(plain, candidate),
              "gate_vs_starting_main": {"passed": not any(r["fails"] for r in comparison),
                                        "failed": [r for r in comparison if r["fails"]],
                                        "changed": [r for r in comparison if r["verdict"] != "same"]},
              "gate_vs_seal": final["gate"], "gate_per_file": per_file, "physical": physical,
              "falcon": probe_changes(falcon_base, falcon_final),
              "x3_passed": x3["passed"], "x3_raw_changes": x3_raw, "set_F": set_f}
    a.out.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"ride": {tag: {**{k: v for k, v in report[tag].items() if k != "episodes"},
                                      "episode_count": len(report[tag]["episodes"])}
                              for tag in ("ride_base", "ride_candidate")},
                      "ride_stop_diff": report["ride_stop_diff"],
                      "seal_gate_passed": final["gate"]["passed"],
                      "main_gate_failed": report["gate_vs_starting_main"]["failed"],
                      "set_F": set_f, "falcon": report["falcon"], "x3_passed": x3["passed"],
                      "x3_cases": len(x3_raw), "x3_stop_changes": {
                          key: r for key, r in x3_raw.items() if r["lost"] or r["added"]}}, indent=2))


if __name__ == "__main__":
    main()
