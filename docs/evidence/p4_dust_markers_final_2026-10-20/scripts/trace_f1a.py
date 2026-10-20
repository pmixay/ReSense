"""Which low clusters does F1a (``lowobj.local_rail_margin``) mark weak, frame by frame?  A read-only trace.

The jury runner's own NodeReplica loop, with ``resense.detector.rail_reference_check`` wrapped: the wrapper calls the
original, records every cluster it returns (distance, size, number of points, height_max) and returns the original's
result unchanged. Writes <out>.jsonl (the runner's record per frame, for the identity check against a plain run) and
<out>.f1a.json (per frame: the weak clusters). Extra --set overrides as in judge_runner_set.py.

    RESENSE_REPO=<checkout> PYTHONPATH=<checkout>:<checkout>/ros2_ws/src/resense_ros python trace_f1a.py <bag> <out> [--set k=v ...]
"""
import json
import os
import sys

import yaml

REPO = os.environ["RESENSE_REPO"]
sys.path.insert(0, os.path.join(REPO, "docs/evidence/judgement_2026-10-13/scripts"))
import judge_runner as jr  # noqa: E402
import resense.detector as det  # noqa: E402

bag, out = sys.argv[1], sys.argv[2]
sets, it = {}, iter(sys.argv[3:])
for a in it:
    if a == "--set":
        k, v = next(it).split("=", 1)
        sets[k] = yaml.safe_load(v)

weak_log = []
_orig = det.rail_reference_check


def wrapped(*args, **kw):
    res = _orig(*args, **kw)
    for c in res:
        weak_log.append({"d": round(float(c.distance), 2), "size": [round(float(v), 2) for v in c.size],
                         "n": int(c.points_idx.size), "hmax": round(float(c.height_max), 3),
                         "bbox_x": [round(float(c.bbox_min[0]), 2), round(float(c.bbox_max[0]), 2)]})
    return res


det.rail_reference_check = wrapped
rep = jr.NodeReplica(overrides=sets)
frames = []
with open(out + ".jsonl", "w") as fj:
    n = 0
    for db3 in jr.db3_files(bag):
        for ts, topic, raw in jr.iter_raw(db3):
            weak_log.clear()
            msg, stamp, res, dm, tm = rep.process_raw(raw, topic, n)
            r = jr.record(n, ts / 1e9, stamp, res, dm, tm, msg.header.frame_id, topic)
            fj.write(json.dumps(r) + "\n")
            if weak_log:
                frames.append({"i": n, "weak": list(weak_log)})
            n += 1
json.dump({"bag": bag, "sets": sets, "frames": n, "weak_frames": frames}, open(out + ".f1a.json", "w"))
print(f"{n} frames, F1a marked weak low clusters in {len(frames)} frames", file=sys.stderr)
