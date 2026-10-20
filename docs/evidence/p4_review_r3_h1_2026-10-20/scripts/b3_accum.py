"""B3 (P4 shipping review, reviewer only): R3's tall-cable shortcut on accumulated clusters. A thin vertical
target (3 cm cable, the review's r3_veto geometry) approached at 10 m/s from 80 m, 10 Hz, speed given to the
detector vs unknown, R3 on (shipped YAML) vs off (tracking.cable_confirm_time_s=0). Per frame the matched
track's last cluster: current-frame points == all points (R3-eligible) or accumulated, and cable_kind.
Read-only: state is read after Detector.process returns.

    cd docs/evidence/p4_review_shipping_2026-10-20/scripts
    PYTHONPATH=<tree>:. python b3_accum.py <tree>/configs/default.yaml
"""
import sys

import raycast as rc
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.synthetic import effective_thickness

RH = rc.FLOOR + 0.18


def run(yaml, r3, speed_known, v=10.0, d0=80.0, n=62):
    cfg = DetectorConfig.from_yaml(yaml)
    if not r3:
        cfg.tracking.cable_confirm_time_s = 0.0
    det = Detector(cfg)
    first, rows = None, []
    for k in range(n):
        x = d0 - v * 0.1 * k
        w = effective_thickness(0.03, x)
        box = (x, x + w, rc.AY - w / 2, rc.AY + w / 2, RH + 0.2, rc.AZ + rc.R + 0.5)
        fr = rc.frame(boxes=[box], seed=k)
        res = det.process(Frame(xyz=fr.xyz, intensity=fr.intensity, stamp=0.1 * k),
                          ego_speed=v if speed_known else None)
        on = any(abs(d.distance - x) < 1.0 for d in res.detections)
        if on and first is None:
            first = round(x, 1)
        tr = [t for t in det.tracker.tracks if t.last is not None and t.misses == 0 and abs(t.last.distance - x) < 1.5]
        info = [(t.hits, t.cable_kind, t.cable_hits, int(t.last.n_raw), len(t.last.points_idx)) for t in tr]
        rows.append((k, round(x, 1), on, info))
    return first, rows


if __name__ == "__main__":
    y = sys.argv[1]
    for speed_known in (False, True):
        for r3 in (True, False):
            first, rows = run(y, r3, speed_known)
            acc = sum(1 for r in rows for i in r[3] if i[3] != i[4])
            cab = sum(1 for r in rows for i in r[3] if i[1])
            print(f"speed {'given' if speed_known else 'unknown'} R3 {'on' if r3 else 'off'}: first STOP {first} m, "
                  f"STOP frames {sum(r[2] for r in rows)}, track-frames accumulated {acc}, with cable_kind {cab}")
            if r3:
                for r in rows[:12]:
                    print("    frame", r[0], "x", r[1], "STOP" if r[2] else "-", "(hits, kind, cable_hits, n_raw, n_pts)", r[3])
