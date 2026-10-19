"""Print episodes/STOP/GO/degraded per recording and level from dust_battery summary.json files."""
import json, sys
from pathlib import Path
rows = {}
for root in sys.argv[1:]:
    for s in Path(root).rglob("summary.json"):
        for bag, rec in json.loads(s.read_text())["recordings"].items():
            rows[bag] = rec["levels"]
for bag, lv in sorted(rows.items()):
    out = []
    for name in ("clean", "low", "medium", "high"):
        m = lv.get(name)
        if not m: continue
        objs = " ".join(f"{k[:6]}:{len(o['stop_frames'])}/{o['visible_inside_frames']}@{o['first_stop_m']}" for k, o in m.get("objects", {}).items())
        out.append(f"{name}: ep {m.get('stop_episodes',0)} STOP {m.get('STOP',0)} GO {m.get('GO',0)} deg {m.get('degraded_frames',0)} {objs}")
    print(bag); print("   " + "\n   ".join(out))
