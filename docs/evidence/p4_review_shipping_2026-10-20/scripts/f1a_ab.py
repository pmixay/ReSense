"""A/B of F1a (lowobj.local_rail_margin 0 vs the shipped 0.01) on the f1a_capped_top scenes: STOP frames on the
box (detection within 0.6 m of it), STOP frames anywhere else, the model error and the corridor clusters."""
from f1a_capped_top import scene, run

rows = []
for raise_ in (0.0, 0.18, 0.20):
    for top in (None, 0.12, 0.13, 0.15, 0.17, 0.20, 0.25, 0.30):
        fr, rh = scene(raise_, 40.0, top)
        line = []
        for margin in (0.0, 0.01):
            det, stops, res, info = run(fr, margin, n=12, trace=True)
            on_box = [d for d in res.detections if abs(d.distance - 40.0) < 0.6 and abs(d.lateral) < 0.4]
            other = [d for d in res.detections if d not in on_box]
            line.append((len(stops), [(round(d.distance, 1), d.kind) for d in on_box], len(other)))
            err = float(det.track.rail_z(40.0)) - rh
        corr = [c for c in info[:-1] if c[2] == ""]
        print(f"rails +{raise_:.2f} (model rail head {err:+.3f} vs true at 40 m) box top {top}: "
              f"F1a off: {line[0][0]} STOP frames / last on box {line[0][1]} / other {line[0][2]}   "
              f"F1a on: {line[1][0]} STOP frames / last on box {line[1][1]} / other {line[1][2]}   corridor clusters {corr}")
