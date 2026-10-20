"""Counterfactual replay: the jury runner with the returns inside selected marker boxes deleted.

``--dust``: every dust box (extent < 0.1 m) in the frames where it is marked, box grown by --margin (0.05 m): the cloud
without the organizers' dust. ``--object ID [--frames a,b]``: the returns inside the box of marker id ID (a real object)
in those frames: the positive control (removing a real object must change the output). Writes <out>.jsonl and
<out>.removed.json (returns removed per frame). Compare with the delivered-bag run using field_diff.py.

    RESENSE_REPO=<checkout> PYTHONPATH=... python remove_boxes.py <bag> <markers.jsonl> <out> (--dust | --object ID [--frames a,b]) [--margin 0.05]
"""
import argparse
import json
import os
import sys

import yaml

import numpy as np

REPO = os.environ["RESENSE_REPO"]
sys.path.insert(0, os.path.join(REPO, "docs/evidence/judgement_2026-10-13/scripts"))
import judge_runner as jr  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("bag")
ap.add_argument("markers")
ap.add_argument("out")
ap.add_argument("--dust", action="store_true")
ap.add_argument("--object", type=int)
ap.add_argument("--frames")
ap.add_argument("--margin", type=float, default=0.05)
ap.add_argument("--random-seed", type=int,
                help="control for --dust: delete, in the same frames, the same NUMBER of returns as the dust boxes hold, but "
                     "chosen at random among the frame's returns 3-8 m ahead, |lateral| < 2.5 m (outside the dust boxes)")
ap.add_argument("--random-frames", help="with --random-seed: instead, these frames, with --random-n returns each")
ap.add_argument("--random-n", type=int, default=8)
ap.add_argument("--set", action="append", default=[], help="config override section.key=value (YAML value), as judge_runner_set.py")
a = ap.parse_args()
sets = {k: yaml.safe_load(v) for k, v in (kv.split("=", 1) for kv in a.set)}
assert (a.dust or a.random_frames is not None) != (a.object is not None)
lo_f, hi_f = (map(int, a.frames.split(","))) if a.frames else (0, 10 ** 9)
boxes = {}
for line in open(a.markers):
    r = json.loads(line)
    for m in r["markers"]:
        if m["type"] == "LINE_LIST" and m["action"] == 0 and m["n_points"]:
            lo, hi = np.array(m["pts_min"]), np.array(m["pts_max"])
            if a.dust and (hi - lo).max() < 0.1:
                boxes.setdefault(r["i"], []).append((lo, hi))
            if a.object is not None and m["id"] == a.object and lo_f <= r["i"] <= hi_f:
                boxes.setdefault(r["i"], []).append((lo, hi))
removed = {}
rand_frames = {int(f) for f in a.random_frames.split(",")} if a.random_frames else None


def tf(xyz_s, inten, ring, idx):
    if rand_frames is not None:
        if idx not in rand_frames:
            return xyz_s, inten, ring
        n_drop = a.random_n
        dust_drop = np.zeros(len(xyz_s), bool)
    elif idx not in boxes:
        return xyz_s, inten, ring
    else:
        dust_drop = np.zeros(len(xyz_s), bool)
        for lo, hi in boxes[idx]:
            dust_drop |= ((xyz_s >= lo - a.margin) & (xyz_s <= hi + a.margin)).all(1)
        n_drop = int(dust_drop.sum())
    if a.random_seed is not None:
        rng = np.random.default_rng([a.random_seed, idx])
        fwd, lat = -xyz_s[:, 1], xyz_s[:, 0]
        pool = np.flatnonzero((fwd > 3) & (fwd < 8) & (np.abs(lat) < 2.5) & ~dust_drop)
        drop = np.zeros(len(xyz_s), bool)
        drop[rng.choice(pool, size=n_drop, replace=False)] = True
    else:
        drop = dust_drop
    removed[idx] = int(drop.sum())
    keep = ~drop
    return xyz_s[keep], inten[keep], None if ring is None else ring[keep]


rep = jr.NodeReplica(overrides=sets)
with open(a.out + ".jsonl", "w") as fj:
    n = 0
    for db3 in jr.db3_files(a.bag):
        for ts, topic, raw in jr.iter_raw(db3):
            msg, stamp, res, dm, tm = rep.process_raw(raw, topic, n, transform=tf)
            fj.write(json.dumps(jr.record(n, ts / 1e9, stamp, res, dm, tm, msg.header.frame_id, topic)) + "\n")
            n += 1
json.dump({"removed_per_frame": removed, "total": sum(removed.values())}, open(a.out + ".removed.json", "w"))
print(f"{n} frames; returns removed {sum(removed.values())} in {len(removed)} frames", file=sys.stderr)
