"""Rejection control for the F1a repair: boxes whose top is at or just above the TRUE rail heads (rail-height
clutter, which F1a exists to weaken), level and raised rails, F1a off vs on, on the checkout first on PYTHONPATH."""
import resense
from f1a_capped_top import run, scene

print(resense.__file__)
for raise_ in (0.0, 0.18):
    for top in (-0.02, 0.0, 0.02, 0.05, 0.08, 0.10):
        fr, rh = scene(raise_, 40.0, top)
        out = []
        for margin in (0.0, 0.01):
            det, stops, res, info = run(fr, margin, n=12, trace=True)
            on_box = [(round(d.distance, 1), d.kind) for d in res.detections if abs(d.distance - 40.0) < 0.6 and abs(d.lateral) < 0.4]
            out.append(f"{len(stops)} STOP {on_box}")
        print(f"rails +{raise_:.2f} top {top:+.2f}: F1a off {out[0]} | F1a on {out[1]}")
