#!/usr/bin/env python3
"""Calibrate the person-like target on the reviewed real person (raw points only).

Per reviewed main-approach anchor: a 0.5 x 0.5 m box from -0.2 to 1.55 m above the rail-head
reference at the anchor's along/lateral position. The injector's beam model (``Injector.cast``,
scene occlusion off: on these frames the person's own returns are the nearest) gives every raster
ray's beam fraction on the face. Observable: points in the count box (|along - x| < 0.6,
|lateral - lat| < 0.5, height -0.4 .. 1.9 m; split lower/upper at 0.8 m), the same definition the
injection control uses. Fit (grid): fill, rho_lower, rho_upper by the squared log-ratio of
expected/real per band and half, on EVEN anchors (60..250 m); report the ODD anchors as held out.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from inject import Injector, pod  # noqa: E402

REPO = Path(os.environ.get("RESENSE_REPO", HERE.parents[3]))
CACHE = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/user/data/falcon")
TR = json.loads((HERE.parent / "track_reference.json").read_text())["track"]
atlas = json.loads((REPO / "docs/evidence/n2_falcon_2026-10-18/raw_person_review/atlas_proposals.json").read_text())
BANDS = [(0, 30), (30, 60), (60, 100), (100, 150), (150, 200), (200, 240), (240, 250)]
SPLIT = 0.8


def count_box(p, x, lat):
    la = p[:, 1] - (TR["a"] + TR["b"] * p[:, 0])
    h = p[:, 2] - (TR["z0"] + TR["c"] * p[:, 0])
    m = (np.abs(p[:, 0] - x) < 0.6) & (np.abs(la - lat) < 0.5) & (h > -0.4) & (h < 1.9)
    return int((m & (h < SPLIT)).sum()), int((m & (h >= SPLIT)).sum())


def main():
    inj = Injector({"track": TR})
    rows = []
    for k, a in enumerate(atlas["anchors"]):
        c = np.array(a["discovery_center"])
        d = np.load(CACHE / f"f_{a['frame']:05d}.npz")
        lat0 = float(c[1] - (TR["a"] + TR["b"] * c[0]))
        # the face at the body's front: the anchor centre is the body-core centre
        box = (c[0] - 0.25, c[0] + 0.25, lat0 - 0.25, lat0 + 0.25, -0.2, 1.55)
        keys, dirs, tf, f, p, hh = inj.cast(d, box, {"rho": 1.0}, occlusion=False)
        lo, up = count_box(d["xyz"].astype(np.float64), c[0], lat0)
        rows.append({"frame": a["frame"], "episode": a["episode"], "x": float(c[0]), "lat": lat0,
                     "real_lower": lo, "real_upper": up, "tf": tf.tolist(), "f": f.tolist(), "h": hh.tolist(),
                     "rays_inside": int((f > 0.5).sum()), "rays_any": int((f > 0.01).sum())})
    main_rows = [r for r in rows if r["episode"].startswith("main")]

    def expected(r, fill, rl, ru):
        tf, f, h = np.array(r["tf"]), np.array(r["f"]), np.array(r["h"])
        pr = fill * pod(tf, np.where(h < SPLIT, rl, ru) * f)
        return float(pr[h < SPLIT].sum()), float(pr[h >= SPLIT].sum())

    def band_table(sel, fill, rl, ru):
        out = {}
        for lo, hi in BANDS:
            b = [r for r in sel if lo <= r["x"] < hi]
            if not b:
                continue
            e = np.array([expected(r, fill, rl, ru) for r in b])
            out[f"{lo}-{hi}"] = {"anchors": len(b),
                                 "real_lower": round(np.mean([r["real_lower"] for r in b]), 2),
                                 "model_lower": round(float(e[:, 0].mean()), 2),
                                 "real_upper": round(np.mean([r["real_upper"] for r in b]), 2),
                                 "model_upper": round(float(e[:, 1].mean()), 2),
                                 "rays_inside_per_frame": round(np.mean([r["rays_inside"] for r in b]), 2)}
        return out

    even = [r for i, r in enumerate(main_rows) if i % 2 == 0]
    odd = [r for i, r in enumerate(main_rows) if i % 2 == 1]
    best = None
    for fill in np.arange(0.5, 1.21, 0.02):
        for rl in [0.01, 0.015, 0.02, 0.025, 0.03, 0.035, 0.04, 0.05, 0.06, 0.08, 0.1, 0.13, 0.16, 0.2, 0.3, 0.5]:
            for ru in [0.03, 0.04, 0.05, 0.06, 0.08, 0.1, 0.13, 0.16, 0.2, 0.3, 0.5, 1.0]:
                t = band_table([r for r in even if r["x"] >= 60], fill, rl, ru)
                err = sum(np.log((v["model_" + n] + 0.5) / (v["real_" + n] + 0.5)) ** 2
                          for v in t.values() for n in ("lower", "upper"))
                if best is None or err < best[0]:
                    best = (err, float(fill), rl, ru)
    _, fill, rl, ru = best
    res = {"track": TR, "fit_on": "even main anchors, 60-250 m", "fill": round(fill, 3), "rho_lower": rl, "rho_upper": ru,
           "fit_error": best[0], "sigma_deg": 0.025,
           "even_fit": band_table(even, fill, rl, ru), "odd_heldout": band_table(odd, fill, rl, ru),
           "early_uncertain_episode": band_table([r for r in rows if r["episode"].startswith("early")], fill, rl, ru),
           "upper_rho_sensitivity_odd_240_250": {str(v): band_table([r for r in odd if r["x"] >= 200], fill, rl, v)
                                                  for v in (0.05, 0.08, 0.1, 0.2, 1.0)},
           "rows": [{k: v for k, v in r.items() if k not in ("tf", "f", "h")} for r in rows]}
    (HERE.parent / "person_calibration.json").write_text(json.dumps(res, indent=1))
    print(json.dumps({k: v for k, v in res.items() if k not in ("rows", "track")}, indent=1))


if __name__ == "__main__":
    main()
