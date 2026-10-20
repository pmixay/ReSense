"""N5 on the final source (f56ad5e): score the per-frame runs of the three marked bags against the frozen N5 labels, compare
with the v1.1.0 reports, and test the 20.10 marker supplement against the repository's own scorer.

    python n5_final_scoring.py            # from the repository root; reads only committed files

1. final run == v1.1.0 run for the N5 report of each bag (the whole report, ``inputs`` excluded);
2. the supplement merged exactly as committed: the scorer must accept it (it does not: ``n_points`` is null);
3. the supplement with ``n_points`` set to 1 (the only change: the object is published by the organizers' topic only
   while it has returns, so 1 is a lower bound) — what the 34 rows do to the score.
"""
import copy
import json
import lzma
import os
import sys
import tarfile

sys.path.insert(0, os.getcwd())
from scripts.score_team_labels import score

E = "docs/evidence"
sup = json.load(open(f"{E}/n5_markers_2026-10-20/labels_n5_marker_supplement.json"))
tar = tarfile.open(f"{E}/synthetic_labels_2026-10-17/runs/detector_runs.tar.xz")


def final(b):
    return [json.loads(x) for x in lzma.open(f"{E}/p4_dust_markers_final_2026-10-20/runs/final_f56ad5e_{b}.jsonl.xz", "rt")]


def v110(b):
    return [json.loads(x) for x in tar.extractfile(f"v110_synthetic_{b}.jsonl").read().decode().splitlines() if x.strip()]


for b in ("platform", "switch", "tunnels"):
    labels = json.load(open(f"{E}/n5_labels_2026-10-17/labels_synthetic_{b}.json"))
    rf, r1 = score(final(b), labels), score(v110(b), labels)
    same = json.dumps(rf, sort_keys=True) == json.dumps(r1, sort_keys=True)
    s = rf["summary"]
    print(f"{b:9s} frames {rf['frames']}: N5 report of the final run == v1.1.0 report: {same} | "
          f"certain-inside matched {s['certain_inside_matched_bounds']} of {s['certain_inside_object_frames']}, "
          f"recall bounds {s['certain_inside_recall_bounds']}, STOP detections {s['stop_detections']} (unmatched {s['unmatched_stop_detections']})")

labels = json.load(open(f"{E}/n5_labels_2026-10-17/labels_synthetic_tunnels.json"))
run = final("tunnels")
base = score(run, labels)
asis = copy.deepcopy(labels)
fixed = copy.deepcopy(labels)
for frame, rows in sup["rows"].items():
    asis[frame].extend(copy.deepcopy(rows))
    for r in rows:
        r = dict(r)
        r["n_points"] = 1
        fixed[frame].append(r)
try:
    score(run, asis)
    print("supplement as committed: accepted")
except Exception as exc:                                    # the point of this step
    print(f"supplement as committed: REJECTED by scripts/score_team_labels.py: {type(exc).__name__}: {exc}")
after = score(run, fixed)
b, a = base["summary"], after["summary"]
print("supplement with n_points=1: accepted. possible-inside object frames", b["possible_inside_object_frames"], "->", a["possible_inside_object_frames"],
      "| certain-inside matched", b["certain_inside_matched_bounds"], "->", a["certain_inside_matched_bounds"],
      "| gauge relation frames", base["annotation_gauge_relation_frames"], "->", after["annotation_gauge_relation_frames"])
o = after["objects"]["box_left_0"]
print("box_left_0:", {k: o[k] for k in ("point_supported_frames", "first_frame", "last_frame", "first_visible_m", "gauge_relation_frames",
                                         "stop_match_frames_bounds", "warning_match_frames_bounds", "certain_inside_frames")})
