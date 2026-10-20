#!/usr/bin/env python3
"""Reviewer script: tie the 9 STOP frames removed on the ride to P4's archived reference trace and to the
candidate's snapshot replay.

The archive (trace_fix_records.tar.xz) is the read-only trace of the B1-repair tree (= the reference f56ad5e), one
line per frame in <piece>.tracks.ndjson (line i = the piece's row i), with every matched track (id, hits, age,
reported, zone, kind, centroid, [cluster k, A, D, cause]).  The (piece, row) pairs and the distances below are copied
from the author's changed-frames.txt; they are used only as a key, and the check is that the archived trace shows
a reported gauge track at the same distance (an independent confirmation that the row <-> snapshot mapping is right).
"""
import json
import sys
from pathlib import Path

snap = Path(sys.argv[1])
rep = Path(sys.argv[2])            # snap_pad_wt_cand.json
ref = Path(sys.argv[3])            # snap_pad_wt_ref.json
REMOVED = [("new_data_1", 1259, 42.1), ("new_data_1", 1260, 38.9), ("new_data_1", 1261, 36.9),
           ("new_data_1", 1265, 35.8), ("new_data_1", 1266, 24.3), ("new_data_1", 1267, 23.6),
           ("new_data_4", 80, 21.8), ("new_data_7", 623, 47.6), ("new_data_7", 624, 45.9)]
cand = {(r["stem"], r["k"]): r for r in json.load(open(rep))["rows"]}
refrows = {(r["stem"], r["k"]): r for r in json.load(open(ref))["rows"]}
out = []
for piece, row, dist in REMOVED:
    tracks = [json.loads(l) for l in (snap / f"{piece}.tracks.ndjson").read_text().splitlines()]
    t = tracks[row]
    print(f"{piece} row {row} stem {t['stem']}  author distance {dist}")
    for tr in t["tracks"]:
        tid, hits, age, reported, zone, kind, cen, tag = tr
        mark = ""
        if tag is not None:
            k, A, D, cause = tag
            c = cand.get((t["stem"], k))
            mark = f" lineage cluster k={k} A={A} D={D} cause={cause}"
            if c is not None:
                mark += (f" | candidate replay: rejected={c['rejected']} surface={c['surface']} top_new={c['top_new']}"
                         f" top_old={c['top_old']} ref_orig={c['ref_orig']} ref_ind={c['ref_ind']} lat={c['lat']}")
        print(f"   track {tid} hits {hits} age {age} reported {reported} zone {zone} kind '{kind}' centroid {cen}{mark}")
        if reported and zone == "gauge":
            out.append(dict(piece=piece, row=row, stem=t["stem"], author_distance=dist, track=tid,
                            centroid_x=cen[0], dist_match=abs(cen[0] - dist) < 2.5, tag=tag))
print(json.dumps(out, indent=1))
