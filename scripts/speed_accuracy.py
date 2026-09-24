#!/usr/bin/env python3
"""Coverage and accuracy of the LiDAR-only speed estimator against the ICP reference.

    python scripts/speed_accuracy.py out/speed [--json out/speed/accuracy.json]

Reads the per-frame rows of ``scripts/speed_reference.py``. Everything is compared as a
displacement per frame (the estimator's m/s times the interval the detector used, the
reference's ICP X translation) and printed in m/s at the 10 Hz rotation. Per recording:

* reference: frames with a valid reference, its noise (the scatter of the per-frame value
  against the mean of its two neighbours, robust), the speed range and the distance travelled;
* estimator: coverage (frames with a confident estimate, of all frames and of the frames in
  which the train moves at >= 1 m/s), and the error of the confident estimates against the
  reference: median |error|, p90, the share of estimates off by more than 1 and 3 m/s;
* the raw profile cue (whatever its confidence) and what the estimator says while the train
  stands (|v| < 0.3 m/s) or backs up (v < -0.3 m/s).
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np


def load(path):
    return [json.loads(line) for line in open(path, encoding="utf-8")]


def per_bag(rows):
    n = len(rows)
    ok = [r for r in rows if r.get("ref_ok")]
    fr = np.array([r["frame"] for r in ok])
    v = np.array([r["ref_speed"] for r in ok])            # m/s at the rotation rate
    out = {"frames": n, "ref_valid": len(ok)}
    if not ok:
        return out
    med = np.array([np.median(v[(fr >= f - 2) & (fr <= f + 2)]) for f in fr])
    # noise: a frame against the mean of its two neighbours (white noise sigma -> sqrt(1.5) sigma;
    # the train's acceleration changes the speed by < 0.15 m/s per frame, linear over 3 frames)
    nb = [(v[i] - 0.5 * (v[i - 1] + v[i + 1])) for i in range(1, v.size - 1)
          if fr[i - 1] == fr[i] - 1 and fr[i + 1] == fr[i] + 1]
    out["ref_noise_ms"] = round(float(np.median(np.abs(nb)) * 1.4826 / np.sqrt(1.5)), 3) if nb else None
    out["ref_scan_icp_diff_m"] = round(float(np.median([abs(r["ref_dx"] - r["scan_dx"]) for r in ok])), 4)
    out["ref_speed_range"] = [round(float(v.min()), 1), round(float(np.median(v)), 1), round(float(v.max()), 1)]
    out["distance_m"] = round(float(sum(r["ref_dx"] for r in rows if r.get("ref_dx") is not None)), 1)
    ref = dict(zip(fr.tolist(), med.tolist()))
    # estimator (confident)
    moving = [r for r in rows if ref.get(r["frame"]) is not None and ref[r["frame"]] >= 1.0]
    est = [r for r in rows if r.get("est_speed") is not None]
    out["est_frames"] = len(est)
    out["coverage_all"] = round(len(est) / n, 3)
    out["coverage_moving"] = round(sum(1 for r in moving if r.get("est_speed") is not None) / len(moving), 3) if moving else None
    out["moving_frames"] = len(moving)

    def err_stats(pairs, key):
        e = np.array([abs(a - b) for a, b in pairs])
        if e.size == 0:
            return {key: 0}
        return {key: int(e.size), "median_abs_ms": round(float(np.median(e)), 2),
                "p90_abs_ms": round(float(np.percentile(e, 90)), 2),
                "share_gt1ms": round(float((e > 1.0).mean()), 3), "share_gt3ms": round(float((e > 3.0).mean()), 3)}

    def disp(r, val):
        gap = r.get("gap") or 0.1
        return val * gap / (0.1 * max(1, round(gap / 0.1)))    # the estimator's m/s -> m/s at 10 Hz

    pairs = [(disp(r, r["est_speed"]), ref[r["frame"]]) for r in est if ref.get(r["frame"]) is not None]
    out["confident"] = err_stats(pairs, "n")
    raw = [(disp(r, r["est_profile"]), ref[r["frame"]]) for r in rows
           if r.get("est_profile") is not None and ref.get(r["frame"]) is not None and ref[r["frame"]] >= 1.0]
    out["raw_profile"] = err_stats(raw, "n")
    stand = [r for r in rows if ref.get(r["frame"]) is not None and abs(ref[r["frame"]]) < 0.3]
    back = [r for r in rows if ref.get(r["frame"]) is not None and ref[r["frame"]] < -0.3]
    out["standing_frames"] = len(stand)
    out["standing_with_estimate"] = sum(1 for r in stand if r.get("est_speed") is not None)
    out["standing_estimate_ge1"] = sum(1 for r in stand if (r.get("est_speed") or 0) >= 1.0)
    out["backing_frames"] = len(back)
    out["backing_with_estimate"] = sum(1 for r in back if r.get("est_speed") is not None)
    out["accumulated_frames"] = sum(1 for r in rows if r.get("n_acc", 1) > 1)
    ego_ms = np.array([r["egomotion_ms"] for r in rows])
    out["egomotion_ms_median_p95"] = [round(float(np.median(ego_ms)), 1), round(float(np.percentile(ego_ms, 95)), 1)]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir")
    ap.add_argument("--json", default="")
    a = ap.parse_args()
    res = {}
    for p in sorted(glob.glob(os.path.join(a.dir, "*.jsonl"))):
        rows = load(p)
        if rows:
            res[os.path.splitext(os.path.basename(p))[0]] = per_bag(rows)
    for bag, s in res.items():
        print(bag, json.dumps(s))
    if a.json:
        json.dump(res, open(a.json, "w", encoding="utf-8"), indent=1)


if __name__ == "__main__":
    main()
