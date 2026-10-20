"""F1a finding check: a plain low cluster's top is capped below the envelope floor (0.12 m above the MODEL's
rail-head plane), so where the plane runs low (rails read high) F1a demotes a genuine in-gauge object whose
upper part the corridor stage drops as track hardware.

Scene: numpy ray-cast tunnel (raycast.py); the rail heads stand ``raise_`` above their usual height over
X in [x_a, x_b] (the model's plane, fitted to the bed and the near rails, stays at the old level there:
the rails read ``raise_`` high, as on the ride's frames 2666-2676 where the plane was ~0.1 m low).
A 0.30 x 0.30 m box stands on the bed on the axis at ``x_obj``; its top is ``top_true`` above the TRUE rail
heads there. The same frame is processed n times (standing train), F1a off (margin 0) vs on (0.01).
"""
import numpy as np
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
import raycast as rc


def scene(raise_, x_obj, top_true, x_a=32.0, x_b=70.0, seed=0):
    rr = lambda x: np.where((x >= x_a) & (x <= x_b), raise_, 0.0)
    rh = rc.FLOOR + 0.18 + raise_                       # true rail head z at the object
    boxes = [] if top_true is None else [(x_obj, x_obj + 0.3, rc.AY - 0.15, rc.AY + 0.15, rc.FLOOR, rh + top_true)]
    return rc.frame(rail_raise=rr, boxes=boxes, seed=seed), rh


def run(fr, margin, n=10, trace=False):
    cfg = DetectorConfig()
    cfg.lowobj.local_rail_margin = margin
    det = Detector(cfg)
    stops, info = [], []
    for k in range(n):
        res = det.process(Frame(xyz=fr.xyz, intensity=fr.intensity, stamp=0.1 * k))
        if res.obstacle:
            stops.append(k)
        if trace and k == n - 1:
            info = [(round(c.distance, 2), round(c.lateral, 2), c.kind, c.zone, c.reason, round(float(c.height_max), 3))
                    for c in res.candidates if c.distance > 20]
            info.append(("weak_low", [(round(c.distance, 2), round(c.lateral, 2), round(float(c.height_max), 3))
                                      for c in det._low_height]))
    return det, stops, res, info


if __name__ == "__main__":
    for raise_, top_true in [(0.0, 0.20), (0.13, 0.20), (0.13, None), (0.12, 0.15), (0.11, 0.20)]:
        fr, rh = scene(raise_, 40.0, top_true)
        for margin in (0.0, 0.01):
            det, stops, res, info = run(fr, margin, trace=True)
            dets = [(round(d.distance, 2), round(d.lateral, 2), d.kind) for d in res.detections]
            print(f"rails +{raise_:.2f}, box top {top_true} above true rail head, margin {margin}: "
                  f"STOP frames {stops} dets {dets}")
            print("    model rail_z(40) - true rail head:", round(float(det.track.rail_z(40.0)) - rh, 3))
            print("    candidates >20 m:", info)
