"""F1a fix acceptance (P4, 20.10): summary of f1a_fix_trace.py's records against the two gate runs.

1. The trace's verdicts: every checked cluster's recomputed rule of the tree equals the detector's (``match``); how many
   clusters the old rule (A) and the new one (D) reject; flips (A, not D) by cause and by lateral (on a rail:
   |lateral| 0.6-1.0 m; centre: < 0.4 m; other); clusters the new rule rejects and the old one does not (must be 0);
   for flips, how far the new top is above the old reference (top_new - ref_orig).
2. Every frame whose decision (STOP, advisory) differs between the two gate runs: the run's detection / warning ids,
   and for each id of the candidate run its lineage from the trace (``.tracks.ndjson``): matched hits up to that
   frame, how many were clusters the old rule rejects (flipped), how many were checked clusters both rules accept,
   how many were other clusters (not checked: corridor or not low), and the frames of the flipped hits.

    python -I f1a_fix_summary.py <trace dir> <gate work old> <gate work new>
"""
import collections
import glob
import json
import os
import sys

TR, OLD, NEW = sys.argv[1:4]


def where(lat):
    a = abs(lat)
    return "rail" if 0.6 <= a <= 1.0 else "centre" if a < 0.4 else "other"


print("== 1. the trace's verdicts")
tot = collections.Counter()
for p in sorted(glob.glob(os.path.join(TR, "*.fix.ndjson"))):
    rows = [json.loads(line) for line in open(p)]
    c = collections.Counter()
    gaps = collections.defaultdict(list)
    for r in rows:
        c["checked"] += 1
        c["match"] += r["match"]
        c["A"] += r["A"]
        c["D"] += r["D"]
        c["D_not_A"] += r["D"] and not r["A"]
        if r["cause"]:
            c[f"flip.{r['cause']}.{where(r['lat'])}"] += 1
            c["flip"] += 1
            gaps[where(r["lat"])].append(r["top_new"] - r["ref_orig"])
    tot.update(c)
    name = os.path.basename(p).replace(".fix.ndjson", "")
    print(f"{name:22s} checked {c['checked']:5d} match {c['match']:5d}  A {c['A']:4d}  D {c['D']:4d}  "
          f"D-not-A {c['D_not_A']}  flips {c['flip']:4d}: " +
          ", ".join(f"{k[5:]} {v}" for k, v in sorted(c.items()) if k.startswith("flip.")))
    for w, g in sorted(gaps.items()):
        g = sorted(g)
        print(f"{'':22s}   {w}: top_new - ref_orig min {g[0]:.3f} median {g[len(g) // 2]:.3f} max {g[-1]:.3f} m")
print(f"{'total':22s} checked {tot['checked']:5d} match {tot['match']:5d}  A {tot['A']:4d}  D {tot['D']:4d}  "
      f"D-not-A {tot['D_not_A']}  flips {tot['flip']:4d}: " +
      ", ".join(f"{k[5:]} {v}" for k, v in sorted(tot.items()) if k.startswith("flip.")))

print("\n== 2. decision changes and the lineage of the candidate's tracks")
for p in sorted(glob.glob(os.path.join(NEW, "*.jsonl"))):
    name = os.path.basename(p)[:-6]
    tp = os.path.join(TR, name + ".tracks.ndjson")
    a = [json.loads(line) for line in open(os.path.join(OLD, name + ".jsonl"))]
    b = [json.loads(line) for line in open(p)]
    ch = [i for i, (x, y) in enumerate(zip(a, b)) if (x["obstacle"], x["warning"]) != (y["obstacle"], y["warning"])]
    if not ch:
        continue
    tracks = [json.loads(line) for line in open(tp)] if os.path.exists(tp) else None
    print(f"-- {name}")
    for i in ch:
        x, y = a[i], b[i]
        print(f"row {i:5d} {y['frame_id']}: S{int(x['obstacle'])}W{int(x['warning'])} -> S{int(y['obstacle'])}W{int(y['warning'])}"
              f"  old ids S{[d['id'] for d in x['detections']]} W{[d['id'] for d in x['warnings']]}"
              f"  new ids S{[d['id'] for d in y['detections']]} W{[d['id'] for d in y['warnings']]}")
        if tracks is None:
            print("    (no trace of this piece)")
            continue
        assert tracks[i]["stem"] == y["frame_id"], (tracks[i]["stem"], y["frame_id"])
        for d in y["detections"] + y["warnings"]:
            hits = [(j, t) for j in range(i + 1) for t in tracks[j]["tracks"] if t[0] == d["id"]]
            flipped = [j for j, t in hits if t[7] and t[7][3]]
            kept = [j for j, t in hits if t[7] and not t[7][1]]
            other = [j for j, t in hits if not t[7]]
            still = [j for j, t in hits if t[7] and t[7][1] and not t[7][3]]
            print(f"    id {d['id']:4d} {d['zone']:7s} {d['distance']:6.1f} m lat {d['lateral']:+.2f} kind {d.get('kind') or '-':6s}"
                  f" hits {len(hits):3d}: flipped {len(flipped)} {flipped[:12]}, both accept {len(kept)}, "
                  f"not checked {len(other)}{'' if not still else f', weak continuation {len(still)}'}"
                  f"; first hit row {hits[0][0] if hits else None}")
