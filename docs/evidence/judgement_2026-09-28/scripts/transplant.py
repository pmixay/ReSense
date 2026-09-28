"""Judge's range test with a real person. The person of doubleT_obstacle (bag frames 20-49, where the
labelled person is inside the envelope) is cut out with its label box and pasted onto the track axis
of an obstacle-free recording at 60-200 m, thinned at random to (55.5 / r)^2 of its points (the
LiDAR's angular footprint shrinks with range). Placement uses the detector's own track model of the
unmodified target frame (axis centre and rail-head height at that range) and its mount rotation.
Each case: 60 warm-up frames, then 30 frames with the person at a fixed distance ahead of the train
(the train stationary relative to the object, as in doubleT_obstacle); the control is the same
window without the person. No occlusion shadow is cut behind the person.

    DATA=/home/user/data python transplant.py <target bag> <window start> 60,80,100,130,160,200
"""
import json
import os
import sys

import numpy as np

from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame, frame_from_compact
from resense.io import iter_bag_compact

DATA = os.environ.get("DATA", "/home/user/data") + "/for_hackathon"
LABELS = os.environ.get("LABELS", "labels/doubleT_obstacle.json")
cfg = DetectorConfig()


def frames(bag, start, n):
    return [frame_from_compact(arr, cfg.sensor, stamp=t, frame_id=fid)
            for _, t, fid, arr in iter_bag_compact(f"{DATA}/{bag}", start=start, limit=n)]


def person_templates(src_start=20, n=30):
    """Point sets of the real person relative to (its front, the track axis, the rail head)."""
    labels = json.load(open(LABELS))
    det = Detector(cfg)
    out = []
    for i, f in enumerate(frames("doubleT_obstacle", 0, src_start + n)):
        res = det.process(f)          # from frame 0, so the track model and the calibration settle
        rows = [r for r in labels.get(f"{i:05d}", []) if r["name"] == "person"]
        if i < src_start or not rows:
            continue
        (x0, y0, z0), (x1, y1, z1) = rows[0]["bbox"]
        raw = f.xyz                   # the labels are in the configured (raw) vehicle frame
        m = ((raw[:, 0] > x0 - 0.1) & (raw[:, 0] < x1 + 0.1) & (raw[:, 1] > y0 - 0.1) & (raw[:, 1] < y1 + 0.1)
             & (raw[:, 2] > z0 - 0.02) & (raw[:, 2] < z1 + 0.1))
        p = (raw[m] @ det.mount_rotation.T).astype(np.float64)    # processed frame, as the track model
        xf = p[:, 0].min()
        rel = np.c_[p[:, 0] - xf, p[:, 1] - res.track.center_y(xf), p[:, 2] - res.track.rail_z(xf)]
        out.append((rel, f.intensity[m], rows[0]))
    return out


def with_person(f, rel, inten, track, R, rng_m):
    proc = np.c_[rng_m + rel[:, 0], track.center_y(rng_m) + rel[:, 1], track.rail_z(rng_m) + rel[:, 2]]
    raw = (proc @ R).astype(np.float32)       # processed = R @ raw
    ring = None if f.ring is None else np.concatenate([f.ring, np.zeros(len(raw), f.ring.dtype)])
    return Frame(xyz=np.vstack([f.xyz, raw]), intensity=np.concatenate([f.intensity, inten.astype(f.intensity.dtype)]),
                 ring=ring, stamp=f.stamp, frame_id=f.frame_id, meta=f.meta)


def run_case(bag, start, n, ranges, templates, seed=0):
    warm = min(60, start)
    base = frames(bag, start - warm, n + warm)
    det0 = Detector(cfg)
    models = []
    for f in base:
        r = det0.process(f)
        models.append((r.track, det0.mount_rotation.copy(), r.obstacle))
    result = {"bag": bag, "start": start,
              "control_stop_frames": int(sum(models[warm + k][2] for k in range(n))), "ranges": {}}
    for rng_m in ranges:
        rs = np.random.default_rng(seed)
        det = Detector(cfg)
        stops = hits = 0
        first = None
        dists = []
        for j, f in enumerate(base):
            if j >= warm:
                rel, inten, _ = templates[(j - warm) % len(templates)]
                keep = rs.random(len(rel)) < min(1.0, (55.5 / rng_m) ** 2)
                track, R, _ = models[j]
                f = with_person(f, rel[keep], inten[keep], track, R, rng_m)
            res = det.process(f)
            if j < warm:
                continue
            hit = res.obstacle and res.nearest_distance is not None and abs(res.nearest_distance - rng_m) < 4.0
            stops += bool(res.obstacle)
            hits += bool(hit)
            if hit:
                first = j - warm if first is None else first
                dists.append(round(float(res.nearest_distance), 1))
        result["ranges"][rng_m] = {"stop_frames": stops, "stop_at_person": hits, "first_hit_frame": first,
                                   "n_frames": n, "points_kept_frac": round(min(1.0, (55.5 / rng_m) ** 2), 3),
                                   "dist_range": [min(dists), max(dists)] if dists else None}
        print(bag, start, rng_m, result["ranges"][rng_m], file=sys.stderr, flush=True)
    return result


if __name__ == "__main__":
    tpl = person_templates()
    print(json.dumps(run_case(sys.argv[1], int(sys.argv[2]), 30, [float(r) for r in sys.argv[3].split(",")], tpl)))
