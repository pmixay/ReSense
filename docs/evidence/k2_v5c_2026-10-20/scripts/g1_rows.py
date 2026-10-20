"""G-1 of the v5c registration from regression_gate.py JSONs: gate verdict and failing rows, ride STOP episodes,
the five empty recordings' and squareT_platform's STOP episodes, set O small_center; one line per JSON.

    python -I g1_rows.py <gate.json> ...
"""
import json
import sys

for p in sys.argv[1:]:
    d = json.load(open(p))
    g = d["gate"]
    so = d["set_O"]["objects"].get("small_center", {})
    print(f"{p}\n  commit {d['code'].get('commit', '?')[:10]}  passed {g['passed']}  worse_gated {len(g['worse_gated'])}  "
          f"missing_gated {len(g['missing_gated'])}  better {len(g['better'])}")
    for r in g["worse_gated"] + g["missing_gated"]:
        print("    worse/missing:", r)
    print(f"  ride STOP episodes {d['ride']['stop_episodes']}  alarm events {d['ride']['alarm_events']}  "
          f"alarm frames {d['ride']['alarm_frames']}")
    print(f"  five empty STOP episodes {d['five_empty']['stop_episodes']}  squareT_platform STOP episodes "
          f"{d['recordings']['squareT_platform_squareT_switch']['stop_episodes']}")
    print(f"  set O small_center: STOP frames {so.get('stop_frames')}  first STOP {so.get('first_stop_m')} m  "
          f"held from {so.get('held_from_m')} m")
