#!/usr/bin/env python3
"""Calibrate the injector's POD fall-off beyond 250 m on the real far walker (far_walker_labels.json).

The near calibration (calibrate_person.py: fill, rho_lower, rho_upper with k = 2.35) is refitted
jointly with the POD exponent k on (a) the reviewed main anchors 150-250 m and (b) the far walker's
labelled frames at 245-285 m with label lateral > -0.6 m (clearly inside the count box). Frames are
split even/odd (fit on even, report odd). Observable as in calibrate_person.py (count box). The far
walker frames 285-307 m (lateral -0.5..-1.0 m, at the gauge edge) are reported, not fitted.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from inject import Injector, pod  # noqa: E402
from calibrate_person import count_box, SPLIT  # noqa: E402

EV = HERE.parent
CACHE = Path("/home/user/data/falcon")
cal = json.loads((EV / "person_calibration.json").read_text())
TR = cal["track"]
lab = json.loads((EV / "far_walker_labels.json").read_text())
inj = Injector({"track": TR})


def sample(frame, x, lat):
    d = np.load(CACHE / f"f_{frame:05d}.npz")
    box = (x - 0.25, x + 0.25, lat - 0.25, lat + 0.25, -0.2, 1.55)
    keys, dirs, tf, f, p, hh = inj.cast(d, box, {"rho": 1.0}, occlusion=False)
    lo, up = count_box(d["xyz"].astype(np.float64), x, lat)
    return {"frame": frame, "x": x, "lat": lat, "real_lower": lo, "real_upper": up, "tf": tf, "f": f, "h": hh}


rows = []
for r in cal["rows"]:
    if r["episode"].startswith("main") and 150 <= r["x"] < 250:
        rows.append(dict(sample(r["frame"], r["x"], r["lat"]), src="anchor"))
path = {f: (x, l) for f, x, l in lab["episodes"]["far_walker"]["path"]}
for f in sorted(path)[::3]:
    x, l = path[f]
    if 245 <= x < 310:
        rows.append(dict(sample(f, x, l), src="walker"))


def expected(r, fill, rl, ru, k):
    pr = fill * pod(r["tf"], np.where(r["h"] < SPLIT, rl, ru) * r["f"], k)
    return float(pr.sum())


def table(sel, fill, rl, ru, k, width=10):
    out = {}
    for src in ("anchor", "walker"):
        for lo in range(150, 310, width):
            b = [r for r in sel if r["src"] == src and lo <= r["x"] < lo + width]
            if b:
                out[f"{src} {lo}-{lo + width}"] = {"n": len(b), "real": round(np.mean([r["real_lower"] + r["real_upper"] for r in b]), 2),
                                                 "model": round(np.mean([expected(r, fill, rl, ru, k) for r in b]), 2),
                                                 "lat_median": round(float(np.median([r["lat"] for r in b])), 2)}
    return out


fit_rows = [r for r in rows if r["src"] == "anchor" or (r["x"] < 285 and r["lat"] > -0.6)]
even = fit_rows[::2]
odd = fit_rows[1::2]
fill = cal["fill"]
best = None
for k in (1.0, 1.5, 2.0, 2.35, 3.0, 4.0, 6.0):
    for rl in (0.02, 0.03, 0.05, 0.08):
        for ru in (0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.7, 1.0):
            t = table(even, fill, rl, ru, k)
            err = sum(np.log((v["model"] + 0.5) / (v["real"] + 0.5)) ** 2 for v in t.values())
            if best is None or err < best[0]:
                best = (err, k, rl, ru)
_, k, rl, ru = best
res = {"fit": {"k": k, "rho_lower": rl, "rho_upper": ru, "fill": fill, "error": best[0]},
       "previous_model": {"k": 2.35, "rho_lower": cal["rho_lower"], "rho_upper": cal["rho_upper"]},
       "even_fit": table(even, fill, rl, ru, k), "odd_heldout": table(odd, fill, rl, ru, k),
       "walker_edge_285_310_not_fitted": table([r for r in rows if r["src"] == "walker" and (r["x"] >= 285 or r["lat"] <= -0.6)], fill, rl, ru, k),
       "previous_model_on_all": table(rows, fill, cal["rho_lower"], cal["rho_upper"], 2.35)}
(EV / "far_calibration.json").write_text(json.dumps(res, indent=1))
print(json.dumps(res, indent=1))
