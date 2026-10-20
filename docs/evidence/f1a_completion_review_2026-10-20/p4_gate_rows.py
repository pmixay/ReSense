#!/usr/bin/env python3
"""Reviewer script (own): use P4's archived per-frame gate output of the B1-repair tree (99dab01;
docs/evidence/f1a_acceptance_2026-10-20/out/gatework_f1a.tar.xz) as an independent per-frame witness of the
REFERENCE side of the 9 removed STOP frames.

  1. count the ride's per-frame obstacle (STOP) frames in the 8 pieces: the B1-repair tree should show 111;
  2. print rows 1259..1267 of new_data_1, 80 of new_data_4, 623/624 of new_data_7 (the author's removed frames):
     obstacle flag and detection distances;
  3. positive control: the same extraction applied to rows that are NOT in the author's list must not show
     the removed-frame pattern (consecutive obstacle rows at those distances), and the total STOP rows of the piece
     must equal the sum of piece counts.

    python p4_gate_rows.py <work_f1a dir>
"""
import json
import sys
from pathlib import Path

W = Path(sys.argv[1])
REMOVED = [("new_data_1", 1259, 42.1), ("new_data_1", 1260, 38.9), ("new_data_1", 1261, 36.9), ("new_data_1", 1265, 35.8),
           ("new_data_1", 1266, 24.3), ("new_data_1", 1267, 23.6), ("new_data_4", 80, 21.8), ("new_data_7", 623, 47.6),
           ("new_data_7", 624, 45.9)]
rows = {}
tot = 0
for i in range(8):
    r = [json.loads(l) for l in (W / f"new_data_{i}.jsonl").read_text().splitlines() if l.strip()]
    rows[f"new_data_{i}"] = r
    n = sum(bool(x["obstacle"]) for x in r)
    tot += n
    print(f"new_data_{i}: rows {len(r)} obstacle rows {n}")
print("ride obstacle (STOP) rows over 8 pieces:", tot, "(reference gate JSON says alarm_frames 111)")
print("keys of a row:", sorted(rows["new_data_1"][0]))
ok = 0
for piece, row, dist in REMOVED:
    x = rows[piece][row]
    d = [round(q.get("distance", -1), 1) for q in x.get("detections", [])]
    hit = bool(x["obstacle"]) and any(abs(v - dist) < 0.15 for v in d)
    ok += hit
    print(f"{piece} row {row}: obstacle={bool(x['obstacle'])} detections {d}  author reference distance {dist} "
          f"-> {'MATCH' if hit else 'no match'}")
print(f"{ok} of {len(REMOVED)} removed frames are obstacle rows at the author's reference distance in P4's B1-tree gate")
# positive control: neighbouring rows outside the list
ctrl = [("new_data_1", 1262), ("new_data_1", 1263), ("new_data_1", 1264), ("new_data_4", 79), ("new_data_4", 81),
        ("new_data_7", 622), ("new_data_7", 625)]
print("neighbouring rows not in the author's list (obstacle flag):",
      {f"{p}:{r}": bool(rows[p][r]["obstacle"]) for p, r in ctrl})
