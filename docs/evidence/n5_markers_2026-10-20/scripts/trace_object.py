"""Frame-by-frame trace of one marked object in two runs: the marker box (near face, lateral extent, sensor frame) and,
per run, the decision, the clear distance, the monitored range, and the detections and warnings within max(3 m, 3 %)
of the box's near face (distance, lateral from the run's own track axis, vehicle lateral c[1]).

    python trace_object.py <markers.jsonl> <runA.jsonl> <runB.jsonl> <marker_id> [max_near_m]
"""
import json
import sys

mk_path, a_path, b_path, oid = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
max_near = float(sys.argv[5]) if len(sys.argv) > 5 else 250.0
runs = [[json.loads(line) for line in open(p)] for p in (a_path, b_path)]
for line in open(mk_path):
    r = json.loads(line)
    for m in r["markers"]:
        if m["id"] != oid or m["type"] != "LINE_LIST" or m["action"] != 0 or not m["n_points"]:
            continue
        lo, hi = m["pts_min"], m["pts_max"]
        near = -hi[1]
        if not 2.5 <= near <= max_near:
            continue
        out = [f"{r['i']:4d} near {near:6.1f} lat {lo[0]:+.2f}..{hi[0]:+.2f}"]
        for tag, run in zip("AB", runs):
            q = run[r["i"]]
            win = max(3.0, 0.03 * near)
            dets = [(d["d"], d["lat"], d["c"][1]) for d in q["dets"] if abs(d["d"] - near) <= win]
            warns = [(w["d"], w["lat"]) for w in q["warns"] if abs(w["d"] - near) <= win]
            out.append(f"{tag} {q['decision']:<7} clear {q['clear']:6.1f} mon {q['monitored']:6.1f} det {dets} warn {warns}")
        print(" | ".join(out))
