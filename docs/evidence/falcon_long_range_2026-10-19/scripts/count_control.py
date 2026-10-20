#!/usr/bin/env python3
"""Positive control 1 (return counts): the person-like target (person_model.json) injected at
each reviewed anchor's position on an empty frame (200..1150, before the person appears) through
the full injector (scene occlusion, Bernoulli returns, range noise); points counted in the same
count box as calibrate_person.py; compared with the real person's points per band. 3 seeds."""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from inject import Injector  # noqa: E402
from calibrate_person import BANDS, count_box  # noqa: E402

CACHE = Path("/home/user/data/falcon")
cal = json.loads((HERE.parent / "person_calibration.json").read_text())
TR = cal["track"]
PERSON = json.loads((HERE.parent / "person_model.json").read_text())
rows = [r for r in cal["rows"] if r["episode"].startswith("main")]
out = []
for seed in range(3):
    for k, r in enumerate(rows):
        f = 200 + (k * 37 + seed * 11) % 950
        tgt = {key: PERSON[key] for key in ("size", "bottom", "fill", "rho", "intensity")}
        tgt.update({"from": f, "to": f + 1, "dist": r["x"], "lat": r["lat"]})
        d = np.load(CACHE / f"f_{f:05d}.npz")
        xyz, _, info = Injector({"track": TR, "seed": 1000 * seed + k, "targets": [tgt]}).apply(f, d)
        lo, up = count_box(xyz.astype(np.float64), r["x"], r["lat"])
        blo, bup = count_box(d["xyz"].astype(np.float64), r["x"], r["lat"])
        out.append({"seed": seed, "x": r["x"], "frame": f, "lower": lo, "upper": up, "bg": blo + bup,
                    "real_lower": r["real_lower"], "real_upper": r["real_upper"], "info": info[0]})
res = {}
for lo_, hi in BANDS:
    sel = [o for o in out if lo_ <= o["x"] < hi]
    real = [o for o in sel if o["seed"] == 0]
    tot = [o["lower"] + o["upper"] for o in sel]
    rtot = [o["real_lower"] + o["real_upper"] for o in real]
    res[f"{lo_}-{hi}"] = {
        "anchors": len(real), "injections": len(sel),
        "lower": [round(np.mean([o["lower"] for o in sel]), 2), round(np.mean([o["real_lower"] for o in real]), 2)],
        "upper": [round(np.mean([o["upper"] for o in sel]), 2), round(np.mean([o["real_upper"] for o in real]), 2)],
        "total_mean": [round(np.mean(tot), 2), round(np.mean(rtot), 2)],
        "total_p10_p50_p90_injected": np.percentile(tot, [10, 50, 90]).tolist(),
        "total_p10_p50_p90_real": np.percentile(rtot, [10, 50, 90]).tolist(),
        "background_points_in_count_box": round(np.mean([o["bg"] for o in sel]), 2)}
(HERE.parent / "count_control.json").write_text(json.dumps({"columns": "[injected, real] per frame", "bands": res, "rows": out}, indent=1))
for k, v in res.items():
    print(k, v)
