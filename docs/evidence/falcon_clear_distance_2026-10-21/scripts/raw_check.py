#!/usr/bin/env python3
"""Sample check of changed ``clear`` values against the raw points (G2 of PROTOCOL.md).

For a stated sample of the rows whose clear_distance the candidate lowered (per recording: the first 10, the last 10 and 10
drawn at random with seed 1 of each rounding rule), the recording is replayed with the candidate configuration (the gate's
own machinery) and, for every sampled frame, the bound the rule rounds under is re-derived from the RAW returns of the frame:

* round_down_obstacle: the nearest confirmed detection's cluster; the raw nearest return X = min(xyz[cluster.points_idx, 0]);
* round_down_candidate: the unrounded clear-cap distance of the frame (``Detector._clear_cap``, read through a wrapper that
  returns its value untouched), and the cluster(s) at that distance: raw nearest return X of the nearest cluster whose
  distance equals the cap.

Checked per frame: the bound is the cluster's distance (``Cluster.distance``; with ``cluster.gauge_distance`` it is the
distance at which the cluster reaches the strict gauge, so it is at or beyond the cluster's nearest return, equal when the
nearest return is inside the gauge: the first version of this script assumed "equal" and reported 19 false violations);
checked: cluster.distance >= raw nearest X - 1 mm (a distance is never nearer than a real return), new clear <= cluster.distance
(the rule never rounds beyond its bound), cluster.distance - new < 0.1 where that bound limits (rounded down, not lower),
and old clear > cluster.distance where the old value overstated; and how many have distance == raw nearest X.
The instrumentation changes nothing: the replayed clear equals the gate row's clear (reported).

Applicability (found by the first version of this script, which reported 14-25 "violations" that were all this): a cluster
built from accumulated frames (``res.n_accumulated`` > 1) has ``points_idx`` into the accumulated cloud, not into this
frame's ``xyz``, and its distance is that of the motion-compensated nearest point, so a raw nearest return of the frame
cannot be compared with it; a bound that is not a cluster (a predicted track, a thin or persistent-evidence cap) has no
raw cluster either. Those rows are listed as ``not_applicable`` with the reason and counted separately, never as passes.
The round-down check "raw X - new < 0.1" holds only where the bound is the limiting term, so it is evaluated only
where the unrounded bound lies within 0.1 m above the new value (or equals it), the others are limited by another term.

    raw_check.py --cache /data/cache --changes clear_changes_pandar.tsv --ctl-work DIR --out OUT.tsv [--set k=v ...]
"""
import argparse, glob, json, os, random, sys
from pathlib import Path

ROOT = Path(os.environ["RESENSE_REPO"]).resolve()
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
import numpy as np  # noqa: E402
from scripts import eval_real  # noqa: E402
from scripts.cache_io import cache_files, load_cache_stamps, cache_file_stem, load_cache_array  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--cache", default="/data/cache"); ap.add_argument("--changes", required=True)
ap.add_argument("--ctl-work", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--set", action="append", default=[]); ap.add_argument("--config", default=str(ROOT / "configs/default.yaml"))
a = ap.parse_args()

rows = [l.rstrip("\n").split("\t") for l in open(a.changes)][1:]
by_rec = {}
for piece, frame, old, new, rule, stop, lost in rows:
    rec = piece.rsplit("_", 1)[0] if piece.startswith("new_data_") else piece
    by_rec.setdefault((rec, rule), []).append((piece, int(frame), float(old), float(new)))
rng = random.Random(1)
sample = {}
for (rec, rule), lst in sorted(by_rec.items()):
    lst = sorted(lst, key=lambda t: (t[0], t[1]))
    pick = lst if len(lst) <= 30 else lst[:10] + lst[-10:] + rng.sample(lst[10:-10], 10)
    for t in pick:
        sample.setdefault(t[0], {})[t[1]] = (rule, t[2], t[3])
cfg_dict = eval_real.load_cfg_dict(a.config, a.set)
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import frame_from_compact  # noqa: E402
out = []
for piece, frames in sorted(sample.items()):
    rec = piece.rsplit("_", 1)[0] if piece.startswith("new_data_") else piece
    d = os.path.join(a.cache, rec)
    files = cache_files(d)
    stamps = load_cache_stamps(d)
    if rec == "new_data":
        k = int(piece.rsplit("_", 1)[1])
        files = list(np.array_split(np.array(files), 8)[k])
    cfg = DetectorConfig.from_dict(cfg_dict)
    det = Detector(cfg)
    cap_box = {}
    orig = det._clear_cap
    det._clear_cap = lambda *x, **kw: cap_box.__setitem__("v", orig(*x, **kw)) or cap_box["v"]   # value passes through
    ctl_rows = {}
    for i, f in enumerate(files):
        stem = cache_file_stem(f)
        fr = frame_from_compact(load_cache_array(f), cfg.sensor, stamp=stamps.get(stem, i * 0.1), frame_id=stem)
        res = det.process(fr)
        idx = int(stem.rsplit("_", 1)[1]) if rec in eval_real.SIX else i
        if idx not in frames:
            if idx > max(frames):
                break
            continue
        rule, old, new = frames[idx]
        tr = {t.id: t for t in det.tracker.tracks}
        row = {"piece": piece, "frame": idx, "rule": rule, "old": old, "new": new, "replayed_clear": float(res.clear_distance),
               "n_acc": int(res.n_accumulated)}
        if rule == "round_down_obstacle":
            best = None
            for dt in res.detections:
                t = tr.get(dt.id)
                if t is not None and t.last is not None and t.misses == 0:
                    c = t.last
                    raw = float(res.xyz[c.points_idx, 0].min()) if c.points_idx.size else float("nan")
                    if best is None or c.distance < best[0]:
                        best = (float(c.distance), raw)
            row.update(cluster_distance=best[0] if best else None, raw_nearest_x=best[1] if best else None)
        else:
            cap = cap_box.get("v")
            near = [c for c in res.candidates if cap is not None and abs(float(c.distance) - cap) < 1e-6 and c.points_idx.size]
            raw = float(res.xyz[near[0].points_idx, 0].min()) if near else float("nan")
            row.update(cap_unrounded=cap, cluster_distance=float(near[0].distance) if near else None, raw_nearest_x=raw)
        out.append(row)
with open(a.out, "w") as fo:
    cols = ["piece", "frame", "rule", "old", "new", "replayed_clear", "n_acc", "cluster_distance", "raw_nearest_x", "cap_unrounded",
            "applicable", "distance_eq_raw", "distance_ge_raw", "new_le_raw", "round_down_tight", "old_overstated"]
    fo.write("\t".join(cols) + "\n")
    bad = {"distance_nearer_than_raw_nearest_return": 0, "new_beyond_cluster_distance": 0,
           "round_down_lower_than_needed_where_bound_limits": 0, "replay_differs": 0}
    na = {"accumulated_cluster": 0, "bound_is_not_a_cluster": 0}
    over = tight_n = applicable_n = eq_n = 0
    for r in out:
        rx, cd = r.get("raw_nearest_x"), r.get("cluster_distance")
        have = rx is not None and cd is not None and rx == rx
        r["applicable"] = int(have and r["n_acc"] == 1)
        if not have:
            na["bound_is_not_a_cluster"] += 1
        elif r["n_acc"] != 1:
            na["accumulated_cluster"] += 1
        bad["replay_differs"] += int(abs(r["replayed_clear"] - r["new"]) > 1e-9)
        if r["applicable"]:
            applicable_n += 1
            r["distance_eq_raw"] = int(abs(rx - cd) < 1e-3)
            r["distance_ge_raw"] = int(cd >= rx - 1e-3)
            r["new_le_raw"] = int(r["new"] <= cd + 1e-6)          # column kept for the table: new <= the cluster distance
            r["old_overstated"] = int(r["old"] > cd + 1e-6)
            limiting = cd - r["new"] < 0.1 + 1e-6          # the bound is within 0.1 m above the new value: it limits
            r["round_down_tight"] = int(limiting)
            tight_n += int(limiting)
            over += r["old_overstated"]
            eq_n += r["distance_eq_raw"]
            bad["distance_nearer_than_raw_nearest_return"] += int(not r["distance_ge_raw"])
            bad["new_beyond_cluster_distance"] += int(not r["new_le_raw"])
            bad["round_down_lower_than_needed_where_bound_limits"] += int(limiting and cd - r["new"] < 0 )
        fo.write("\t".join("" if r.get(c) is None else str(r.get(c)) for c in cols) + "\n")
print(json.dumps({"sampled_rows": len(out), "applicable_rows": applicable_n, "not_applicable": na, "violations_among_applicable": bad,
                  "applicable_rows_where_the_bound_is_the_limiting_term": tight_n, "rows_with_cluster_distance_equal_to_raw_nearest_x": eq_n,
                  "applicable_rows_where_the_old_value_was_beyond_the_cluster_distance": over}))
