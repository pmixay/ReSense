"""Per marked object: STOP frames and first STOP distance of one run versus an ensemble of perturbed runs of the same
configuration (the runs of remove_boxes.py with a few returns deleted at random). The spread of the ensemble is the noise
floor an M-1 difference has to exceed. Uses score_m1.py's matching.

    python noise_floor.py --markers <dir> --base <prefix> --ens <prefix1> <prefix2> ...    (prefix + "_<bag>.jsonl")
"""
import argparse
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("score_m1", os.path.join(HERE, "score_m1.py"))
m1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m1)

ap = argparse.ArgumentParser()
ap.add_argument("--markers", required=True)
ap.add_argument("--base", required=True)
ap.add_argument("--ens", nargs="+", required=True)
a = ap.parse_args()
load = lambda pre, b: {r["i"]: r for r in map(json.loads, open(f"{pre}_{b}.jsonl"))}
print(f"base {a.base}; ensemble of {len(a.ens)} perturbed runs")
print(f"{'bag':9s} {'id':>3s} {'object':30s} | {'STOP base':>9s} {'STOP ens min..max':>18s} | {'first base':>10s} {'first ens min..max':>20s}")
for b in m1.BAGS:
    mk = m1.markers(f"{a.markers}/markers_{b}.jsonl")
    base = m1.score(mk, load(a.base, b))
    ens = [m1.score(mk, load(p, b)) for p in a.ens if os.path.exists(f"{p}_{b}.jsonl")]
    if not ens:
        continue
    for oid in sorted(base):
        if b == "platform" and 15 < oid < 23:
            continue
        sf = [len(e[oid]["stop"]) for e in ens]
        fs = [m1.first_stop_m(mk, e[oid]["stop"], oid) for e in ens]
        fb = m1.first_stop_m(mk, base[oid]["stop"], oid)
        fmin, fmax = (np.nanmin(fs), np.nanmax(fs)) if not np.all(np.isnan(fs)) else (float("nan"), float("nan"))
        print(f"{b:9s} {oid:>3d} {m1.NAMES.get((b, oid), ''):30s} | {len(base[oid]['stop']):>9d} {min(sf):>8d}..{max(sf):<8d} ({len(ens)} runs) | {fb:>10.1f} {fmin:>9.1f}..{fmax:<9.1f}")
