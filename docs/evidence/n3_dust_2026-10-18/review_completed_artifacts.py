"""Independent complete-record checks; no point-cloud rendering or detector calls."""

from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path

for variable in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(variable, "1")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_level(folder, bag, level, count):
    summary = json.loads((folder / "summary.json").read_text())
    measurement = summary["recordings"][bag]["levels"][level]
    path = folder / f"{bag}_{level}.jsonl.gz"
    assert sha(path) == measurement["raw_sha256"]
    rows = [json.loads(line) for line in gzip.open(path, "rt")]
    metadata = json.loads((Path("/home/resense/data/decoded") / bag / "meta.json").read_text())
    assert len(rows) == len(metadata) == measurement["frames"] == count
    assert [row["frame"] for row in rows] == list(range(count))
    assert [row["stamp"] for row in rows] == [item["stamp"] for item in metadata]
    stops = []
    for row in rows:
        health = row["health"]
        decision = ("STOP" if row["obstacle"] else "FAULT" if health["level"] == "error"
                    else "CAUTION" if row["warning"] or health.get("decision_level", health["level"]) == "warn"
                    else "GO")
        assert row["decision"] == decision
        if decision == "STOP":
            stops.append(row["frame"])
    counts = Counter(row["decision"] for row in rows)
    for name in ("GO", "STOP", "CAUTION", "FAULT"):
        assert counts[name] == measurement.get(name, 0)
    episodes = sum(i - 1 not in set(stops) for i in stops)
    assert episodes == measurement.get("stop_episodes", 0)
    return rows, {"frames": count, "counts": counts, "stop_frames": stops,
                  "stop_episodes": episodes, "raw_sha256": sha(path)}


def main():
    # Matching is the declared legacy metric, independently recalculated from raw
    # records and labels. Its source is identical in the immutable experiment.
    import sys
    sys.path.insert(0, str(ROOT))
    from resense.metrics import _assign_detections, gt_objects

    dark = HERE / "candidate_dark_person"
    source = json.loads((dark / "summary.json").read_text())
    assert source["source_hashes"]["resense/metrics.py"] == sha(ROOT / "resense/metrics.py")
    labels_path = ROOT / "labels/doubleT_obstacle.json"
    labels = json.loads(labels_path.read_text())
    dark_result = {}
    for level in ("clean", "low", "medium", "high"):
        rows, stats = read_level(dark, "doubleT_obstacle", level, 201)
        objects = {}
        for row in rows:
            i = row["frame"]
            visible = [g for g in labels.get(f"{i:05d}", [])
                       if g.get("n_points", 1) > 0 and g.get("plausible", True)]
            assigned = _assign_detections(row["detections"], gt_objects(visible))
            assert sorted(row["matched_labels"]) == sorted(visible[k]["label"] for k in assigned)
            for index, obj in enumerate(visible):
                record = objects.setdefault(obj["label"], {"inside": [], "outside": [], "unknown": []})
                if index in assigned:
                    relation = obj.get("in_gauge", True)
                    record["inside" if relation is True else "outside" if relation is False else "unknown"].append(i)
        stats["matched_object_frames_by_declared_relation"] = objects
        dark_result[level] = stats
    for level in ("low", "medium", "high"):
        for name, rows in dark_result[level]["matched_object_frames_by_declared_relation"].items():
            rows["lost_clean_by_relation"] = {
                relation: sorted(set(dark_result["clean"]["matched_object_frames_by_declared_relation"][name][relation])
                                 - set(rows[relation])) for relation in ("inside", "outside", "unknown")}

    fields = ("augmentation", "stamp", "frame", "obstacle", "warning", "nearest_distance", "detections",
              "warnings", "track", "n_points", "n_corridor", "n_candidates", "ego_speed", "n_accumulated")
    health_result = {}
    for level in ("clean", "medium", "high"):
        old, old_stats = read_level(HERE / "baseline", "doubleT_platform", level, 345)
        new, new_stats = read_level(HERE / "health_only_platform", "doubleT_platform", level, 345)
        mismatches = {field: [i for i, (a, b) in enumerate(zip(old, new)) if a[field] != b[field]] for field in fields}
        assert not any(mismatches.values())
        assert old_stats["stop_frames"] == new_stats["stop_frames"]
        assert all(a["health"]["level"] != "error" or b["health"]["level"] == "error" for a, b in zip(old, new))
        health_result[level] = {"frames": 345, "before_sha256": old_stats["raw_sha256"],
                                "after_sha256": new_stats["raw_sha256"], "exact_field_mismatches": mismatches,
                                "stop_frames": len(new_stats["stop_frames"]),
                                "stop_episodes": new_stats["stop_episodes"],
                                "degraded_frames": sum(r["health"].get("decision_level") in ("warn", "error") for r in new),
                                "go_frames": sum(r["decision"] == "GO" for r in new),
                                "nonzero_clear_frames": sum(r["clear_distance"] > 0 for r in new)}
    result = {"reviewer": "c2_implementation; independent of generator and evaluation authors",
              "script_sha256": sha(Path(__file__)), "label_sha256": sha(labels_path),
              "dark_complete_frames": 804, "dark": dark_result,
              "health_only_complete_frames": 1035, "health_only": health_result,
              "scope": "Original coordinate-v1 experiment artifacts. Counts and hashes checked independently; "
                       "not a corrected-coordinate rerun, new ground truth or detector replay. Legacy association "
                       "is approximate; inside/outside labels retain their declared meaning."}
    (HERE / "independent_completed_artifact_review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"dark_frames": 804, "health_only_frames": 1035, "health_only_safety_mismatches": 0}))


if __name__ == "__main__":
    main()
