#!/usr/bin/env python3
"""Reviewer script: print the archived reference trace (tracks.ndjson) rows around a piece/row, only the tracks that
are reported or gauge-low, to follow the STOP track that the candidate removes.

    python track_lineage.py <trace_fix dir> <piece> <row_from> <row_to>
"""
import json
import sys
from pathlib import Path

snap, piece, a, b = Path(sys.argv[1]), sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
tracks = [json.loads(l) for l in (snap / f"{piece}.tracks.ndjson").read_text().splitlines()]
fix = {}
for l in (snap / f"{piece}.fix.ndjson").read_text().splitlines():
    r = json.loads(l)
    fix[(r["stem"], r["k"])] = r
for i in range(a, b + 1):
    t = tracks[i]
    items = []
    for tid, hits, age, rep, zone, kind, cen, tag in t["tracks"]:
        if (rep and zone == "gauge") or (kind == "low" and zone == "gauge"):
            extra = ""
            if tag:
                k = tag[0]
                r = fix.get((t["stem"], k))
                extra = f" cl{k}[A={tag[1]} D={tag[2]} lat={r['lat'] if r else '?'} d={r['d'] if r else '?'}]"
            items.append(f"T{tid}(h{hits}{' REP' if rep else ''} {kind or 'corr'} x={cen[0]:.1f}{extra})")
    print(f"row {i} {t['stem']}: " + "; ".join(items))
