"""Positive control for the dust measurement: does `--set dust.enabled=true` make the jury runner's detector react
to dust at all, and does a dust-free run of the same frames stay unchanged?

Runs the first --frames frames of a bag three times through the jury runner's NodeReplica (the runner itself,
imported, not re-implemented): (a) as delivered, dust.enabled=false; (b) the same with uniform volumetric returns
added in the gauge interior (sensor frame: forward 5-60 m, |lateral| < 1 m, 2 m of height; density --density per
m^3, seeded); (c) the same dust, dust.enabled=true. Prints, per frame range, the decisions, health levels and
messages. The control passes if (b) differs from (a) only by dust effects the guard is not responsible for, (c)
differs from (b) by the guard (degraded visibility), and (a) with dust.enabled=true equals (a).

    RESENSE_REPO=<checkout> PYTHONPATH=<checkout>:<checkout>/ros2_ws/src/resense_ros OPENBLAS_CORETYPE=Haswell \
      OMP_NUM_THREADS=1 python dust_control.py <bag dir> --frames 40 --density 1.0 --out <file>
"""
import argparse
import json
import os
import sys

import numpy as np

REPO = os.environ["RESENSE_REPO"]
sys.path.insert(0, os.path.join(REPO, "docs/evidence/judgement_2026-10-13/scripts"))
import judge_runner as jr  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("bag")
ap.add_argument("--frames", type=int, default=40)
ap.add_argument("--density", type=float, default=1.0)
ap.add_argument("--seed", type=int, default=7)
ap.add_argument("--out")
a = ap.parse_args()

raws = []
for db3 in jr.db3_files(a.bag):
    for ts, topic, raw in jr.iter_raw(db3):
        raws.append((ts, topic, raw))
        if len(raws) >= a.frames:
            break


def make_transform(density):
    def tf(xyz_s, inten, ring, idx):
        if density <= 0:
            return xyz_s, inten, ring
        rng = np.random.default_rng([a.seed, idx])
        vol = 55.0 * 2.0 * 2.0
        n = int(rng.poisson(vol * density))
        fwd = rng.uniform(5.0, 60.0, n)
        lat = rng.uniform(-1.0, 1.0, n)
        up = rng.uniform(-1.5, 0.5, n)
        pts = np.stack([lat, -fwd, up], 1).astype(xyz_s.dtype)       # sensor frame: left +x, forward -y, up +z
        i2 = rng.uniform(0, 5.0, n).astype(inten.dtype)
        r2 = None if ring is None else np.zeros(n, dtype=ring.dtype)
        return (np.concatenate([xyz_s, pts]), np.concatenate([inten, i2]),
                None if ring is None else np.concatenate([ring, r2]))
    return tf


def run(density, dust_on):
    rep = jr.NodeReplica(overrides={"dust.enabled": True} if dust_on else {})
    assert (rep.detector.dust_guard is not None) == dust_on, "the override did not reach the detector"
    tf = make_transform(density)
    rows = []
    for n, (ts, topic, raw) in enumerate(raws):
        msg, stamp, res, dm, tm = rep.process_raw(raw, topic, n, transform=tf)
        r = jr.record(n, ts / 1e9, stamp, res, dm, tm, msg.header.frame_id, topic)
        r["guard"] = None if rep.detector.dust_guard is None else {k: (v if isinstance(v, (int, float, bool, str, type(None))) else str(v))
                                                                    for k, v in vars(rep.detector.dust_guard.last).items()} \
            if hasattr(rep.detector.dust_guard, "last") and hasattr(rep.detector.dust_guard.last, "__dict__") else None
        rows.append(r)
    return rows


TIMING = {"decode_ms", "detect_ms", "total_ms", "guard"}
def same(x, y):
    return all(x[k] == y[k] for k in x if k not in TIMING and k != "msgs" and k != "level") and \
        [m for m in x["msgs"] if not m.startswith("latency")] == [m for m in y["msgs"] if not m.startswith("latency")]


A = run(0.0, False)
A_on = run(0.0, True)
B = run(a.density, False)
C = run(a.density, True)
lines = []
def summ(name, rows):
    import re
    from collections import Counter
    msgs = sorted({re.sub(r"\d+", "N", m) for r in rows for m in r["msgs"] if not m.startswith("latency")})
    lines.append(f"{name}: decisions {dict(Counter(r['decision'] for r in rows))}, health levels "
                 f"{dict(Counter(r['level'] for r in rows))}, clear min/median {min(r['clear'] for r in rows)}/"
                 f"{sorted(r['clear'] for r in rows)[len(rows)//2]}, messages {msgs}")
summ("(a) no dust, guard off", A)
summ("(a') no dust, guard ON ", A_on)
summ(f"(b) dust {a.density}/m3, guard off", B)
summ(f"(c) dust {a.density}/m3, guard ON ", C)
lines.append(f"(a') equals (a) in every non-timing field: {all(same(x, y) for x, y in zip(A, A_on))} "
             f"({sum(not same(x, y) for x, y in zip(A, A_on))} of {len(A)} frames differ)")
lines.append(f"(c) differs from (b) in {sum(not same(x, y) for x, y in zip(B, C))} of {len(B)} frames; "
             f"(b) differs from (a) in {sum(not same(x, y) for x, y in zip(A, B))} frames")
print("\n".join(lines))
if a.out:
    open(a.out, "w").write("\n".join(lines) + "\n")
