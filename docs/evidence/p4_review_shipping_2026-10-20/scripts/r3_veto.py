"""R3 vs the ego-motion veto (tracking.ego_veto_*): a thin vertical target CARRIED ALONG at a constant distance
(it does not approach while the train moves at ``v`` m/s, odometry given) and, as a positive control, a static
cable the train approaches. 10 Hz. Reports STOP frames with R3 on (shipped) and off, and the veto's verdict.
Distance chosen in 25-40 m: beyond ego_veto_min_distance (25 m) and inside the accumulation's min_range
(40 m), so the cluster is current-frame only (R3 eligible) with the speed given."""
import sys
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.synthetic import effective_thickness
import raycast as rc

RH = rc.FLOOR + 0.18


def run(v, d0, carried, r3, n=15, kind="tall"):
    cfg = DetectorConfig()
    if not r3:
        cfg.tracking.cable_confirm_time_s = 0.0
    det = Detector(cfg)
    rows = []
    for k in range(n):
        x = d0 if carried else d0 - v * 0.1 * k
        w = effective_thickness(0.03, x)
        y = rc.AY
        if kind == "tall":
            box = (x, x + w, y - w / 2, y + w / 2, RH + 0.2, rc.AZ + rc.R + 0.5)
        else:                       # hanging from the vault, lowest point 2.7 m above the rail head
            box = (x, x + w, y - w / 2, y + w / 2, RH + 2.7, rc.AZ + rc.R + 0.5)
        fr = rc.frame(boxes=[box], seed=k)
        res = det.process(Frame(xyz=fr.xyz, intensity=fr.intensity, stamp=0.1 * k), ego_speed=v)
        tr = [t for t in det.tracker.tracks if t.last is not None and abs(t.last.distance - x) < 1.5]
        veto = [det.tracker._carried_along(t) for t in tr]
        on = [d for d in res.detections if abs(d.distance - x) < 1.0]
        warn = [(d.reason) for d in res.warnings if abs(d.distance - x) < 1.0]
        rows.append((k, round(x, 1), "STOP" if on else "-", warn, [(t.hits, t.cable_kind, t.cable_hits) for t in tr], veto))
    return rows


if __name__ == "__main__":
    v = float(sys.argv[1]) if len(sys.argv) > 1 else 15.0
    for kind, d0 in (("tall", 30.0), ("hanging", 30.0)):
        for carried in (True, False):
            for r3 in (True, False):
                rows = run(v, d0 if carried else d0 + 10, carried, r3, kind=kind)
                stops = [r[0] for r in rows if r[2] == "STOP"]
                print(f"{kind} {'carried along' if carried else 'static (approached)'}, R3 {'on' if r3 else 'off'}: STOP frames {stops}")
                if carried:
                    print("    ", rows[:7])
