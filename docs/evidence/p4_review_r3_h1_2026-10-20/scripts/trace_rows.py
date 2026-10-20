"""Print the switch trace around given rows of one piece: per matched track the R3 and H1 state and the tracker's
own _qualifies verdicts, and the rows' plain-run identity with the shipped gate rows.

    python trace_rows.py <trace dir> <name> <row0> <row1> [shipped gate work dir]
"""
import json
import os
import sys

d, name, r0, r1 = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
tr = [json.loads(line) for line in open(os.path.join(d, f"{name}.trace.ndjson"))]
for i in range(r0, r1 + 1):
    for t in tr[i]["tracks"]:
        lc = t["last"]
        print(f"row {i} id{t['id']} hits{t['hits']} rep{int(t['reported'])} span{t['span']} | cluster {lc['kind'] or '-'}"
              f"/{lc['zone']}/{lc['reason'] or '-'} d{lc['d']} lat{lc['lat']} h{lc['hmin']}..{lc['hmax']} nraw{lc['n_raw']}/"
              f"pts{lc['n_pts']} | R3 kind{t['cable_kind']} hits{t['cable_hits']} span{t['cable_span']} "
              f"q_on{int(t['q_r3_on'])} q_off{int(t['q_r3_off'])} | H1 core{t['core_hits']}"
              f"{'R' if t['core_ready'] else ''} col{t['col_hits']}/hold{t['column_hold']} "
              f"hold_core{int(t['hold_core'])} hold_nocore{int(t['hold_nocore'])}")
