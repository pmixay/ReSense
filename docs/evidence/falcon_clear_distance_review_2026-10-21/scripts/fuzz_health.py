"""Independent property fuzz of HealthMonitor.update with the lane's switches (own code).
For random inputs: run the monitor with all switches off (= v1.2.0 behaviour) and with each switch combination;
every field of the returned dict other than clear_distance must be equal; clear_distance may only be lowered;
with a confirmed obstacle/candidate the reported clear never exceeds the 0.01 m-rounded obstacle distance.
Positive control: a monitor subclass that perturbs `level` / raises clear must be caught by the same checker."""
import itertools, json, sys
import numpy as np
from resense.config import GaugeConfig, HealthConfig
from resense.health import HealthMonitor
from resense.track import TrackModel
rng = np.random.default_rng(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
N = int(sys.argv[2]) if len(sys.argv) > 2 else 4000
def cfg(lm, lb, rd):
    c = HealthConfig(); c.clear_lost_model, c.clear_lost_bed, c.clear_round_down = lm, lb, rd; return c
def track(score):
    return TrackModel(floor_coef=np.array([0., 0., -1.77]), floor_range=(4., 100.), center=0., yaw=0., curvature=0.,
                      rail_score=score, rail_offset=0.0)
def cloud():
    n = int(rng.integers(30000, 60000)); x = rng.uniform(3, rng.uniform(20, 200), n)
    return np.stack([x, x * np.tan(np.radians(rng.uniform(-35, 35, n))), rng.uniform(-1.8, 2, n)], 1).astype(np.float32)
combos = list(itertools.product([False, True], repeat=3))
class Bad(HealthMonitor):
    mode = None
    def update(self, *a, **k):
        o = super().update(*a, **k)
        if Bad.mode == "level": o["level"] = "warn" if o["level"] == "ok" else "ok"
        if Bad.mode == "raise": o["clear_distance"] = o["clear_distance"] + 0.1
        return o
def run(mon_cls, seq_params, c):
    m = mon_cls(c); outs = []
    for (xyz, sc, od, cd, bc) in seq_params:
        outs.append(m.update(xyz, {}, track(sc), GaugeConfig(), 150.0, 0.05, None, obstacle_distance=od,
                             candidate_distance=cd, bed_conflict=bc))
    return outs
def check(mon_cls):
    bad = {"other_field": 0, "raised": 0, "above_obstacle": 0, "n": 0, "round_down_diff_gt_0.1": 0}
    for _ in range(N // 40):
        seq = []
        for _ in range(40):
            od = None if rng.random() < .4 else float(rng.choice([rng.uniform(3, 200), round(rng.uniform(3, 200), 2) - 1e-9, round(rng.uniform(3, 200), 1)]))
            cd = None if rng.random() < .6 else float(rng.uniform(3, 200))
            seq.append((cloud(), float(rng.choice([0.0, 0.3])), od, cd, bool(rng.random() < .2)))
        base = run(HealthMonitor, seq, cfg(False, False, False))
        for lm, lb, rd in combos[1:]:
            outs = run(mon_cls, seq, cfg(lm, lb, rd))
            for b, o, p in zip(base, outs, seq):
                bad["n"] += 1
                if {k: v for k, v in b.items() if k != "clear_distance"} != {k: v for k, v in o.items() if k != "clear_distance"}: bad["other_field"] += 1
                if o["clear_distance"] > b["clear_distance"] + 1e-12: bad["raised"] += 1
                if rd and not lm and not (lb and p[4]) and b["clear_distance"] - o["clear_distance"] > 0.1 + 1e-9: bad["round_down_diff_gt_0.1"] += 1
                if p[2] is not None and o["clear_distance"] > round(p[2], 2) + 1e-9 and rd: bad["above_obstacle"] += 1
    return bad
print("real  :", json.dumps(check(HealthMonitor)))
for mode in ("level", "raise"):
    Bad.mode = mode; print("poscon", mode, ":", json.dumps(check(Bad)))
