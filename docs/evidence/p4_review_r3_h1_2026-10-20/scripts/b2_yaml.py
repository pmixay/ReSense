"""B2 (P4 shipping review) on the final source with the shipped YAML configuration instead of the class
defaults: the review's r3_veto.run, unchanged, with DetectorConfig() replaced by DetectorConfig.from_yaml.
Prints, per case, the STOP frames and (carried cases) each frame's track hits / cable kind / cable hits and
the ego veto's verdict, plus the static approached control.

    cd docs/evidence/p4_review_shipping_2026-10-20/scripts
    PYTHONPATH=<tree>:. python b2_yaml.py <tree>/configs/default.yaml
"""
import sys

import r3_veto
from resense.config import DetectorConfig

YAML = sys.argv[1]
r3_veto.DetectorConfig = lambda: DetectorConfig.from_yaml(YAML)
c = DetectorConfig.from_yaml(YAML)
d = DetectorConfig()
keys = [("tracking", k) for k in ("cable_confirm_time_s", "hanging_confirm_time_s", "hanging_confirm_hits",
                                  "confirm_hits", "confirm_time_s", "ego_veto_min_speed", "ego_veto_min_distance")]
print("yaml vs class defaults:", [(f"{s}.{k}", getattr(getattr(c, s), k), getattr(getattr(d, s), k)) for s, k in keys])
for d0 in (37.0, 30.0):
    for kind in ("tall", "hanging"):
        for r3 in (True, False):
            rows = r3_veto.run(15.0, d0, True, r3, n=18, kind=kind)
            print(f"carried {d0} m {kind} R3 {'on' if r3 else 'off'}: STOP {[r[0] for r in rows if r[2] == 'STOP']}")
            if d0 == 37.0:
                for r in rows[:6]:
                    print("    frame", r[0], "x", r[1], r[2], "warn", r[3], "(hits, cable_kind, cable_hits)", r[4], "veto", r[5])
    for kind in ("tall", "hanging"):
        for r3 in (True, False):
            rows = r3_veto.run(15.0, d0 + 10, False, r3, n=15, kind=kind)
            print(f"control approached from {d0 + 10} m {kind} R3 {'on' if r3 else 'off'}: STOP "
                  f"{[(r[0], r[1]) for r in rows if r[2] == 'STOP'][:3]}... n={sum(r[2] == 'STOP' for r in rows)}")
