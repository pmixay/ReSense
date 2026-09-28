"""Per-frame trace of one transplant case: the candidate cluster near the pasted person, its zone and
demotion reason, and the trusted axis range, to see why a case does not STOP.

    python transplant_debug.py doubleT_platform 60 60      # <target bag> <window start> <range m>
"""
import sys

import numpy as np

import transplant as T
from resense.detector import Detector
from resense.frame import Frame


def main(bag: str, start: int, rng_m: float) -> None:
    tpl = T.person_templates()
    base = T.frames(bag, start - 60, 90)
    det0 = Detector(T.cfg)
    models = []
    for f in base:
        r = det0.process(f)
        models.append((r.track, det0.mount_rotation.copy()))
    det = Detector(T.cfg)
    rs = np.random.default_rng(0)
    for j, f in enumerate(base):
        if j >= 60:
            rel, inten, _ = tpl[(j - 60) % len(tpl)]
            keep = rs.random(len(rel)) < min(1.0, (55.5 / rng_m) ** 2)
            rel, inten = rel[keep], inten[keep]
            tm, R = models[j]
            proc = np.c_[rng_m + rel[:, 0], tm.center_y(rng_m) + rel[:, 1], tm.rail_z(rng_m) + rel[:, 2]]
            raw = (proc @ R).astype(np.float32)
            ring = None if f.ring is None else np.concatenate([f.ring, np.zeros(len(raw), f.ring.dtype)])
            f = Frame(xyz=np.vstack([f.xyz, raw]),
                      intensity=np.concatenate([f.intensity, inten.astype(f.intensity.dtype)]),
                      ring=ring, stamp=f.stamp, frame_id=f.frame_id, meta=f.meta)
        res = det.process(f)
        if j < 58:
            continue
        near = [c for c in res.candidates if abs(c.distance - rng_m) < 5]
        desc = "; ".join(f"d={c.distance:.1f} lat={c.lateral:+.2f} n={c.n} h={c.height_min:.2f}-{c.height_max:.2f} "
                         f"zone={c.zone} reason={c.reason}" for c in near)
        dec = "STOP" if res.obstacle else ("CAUT" if res.warning else "GO  ")
        print(j - 60, dec, f"axis_valid={res.track.axis_valid:.0f}", desc)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), float(sys.argv[3]))
