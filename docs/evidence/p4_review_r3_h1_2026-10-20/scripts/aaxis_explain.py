"""A-axis (H1 author claim, final source): (1) the traced run's rows equal the plain run's (instrumentation does not
change results); (2) per frame of the injected 2.8 m body, the hooks' record of the track that holds it: the last
cluster's zone / reason / height, whether find_clusters marked it collision_core, column hits in the history and
the hold, core hits / ready, and the tracker's own verdict.

    python aaxis_explain.py <A-axis-default.json> <A-axis-default-traced.json> <hooks.ndjson> [k0 k1]
"""
import json
import sys

plain, traced = (json.load(open(p)) for p in sys.argv[1:3])
hooks = [json.loads(line) for line in open(sys.argv[3])]
k0, k1 = (int(v) for v in sys.argv[4:6]) if len(sys.argv) > 5 else (280, 336)
print("traced == plain (summary and every row):", plain == traced)
# hooks are recorded per Detector.process call; range_test runs its baseline from a file, so call i = frame k
assert len(hooks) == len(plain["rows"]), (len(hooks), len(plain["rows"]))
for r, h in zip(plain["rows"], hooks):
    k = r["k"]
    if not (k0 <= k <= k1) or r["X"] is None or r.get("Y") is None:
        continue
    X = r["X"]
    near = [t for t in h["tracks"] if abs(t["d"] - X) <= max(2.0, 0.03 * X) + 0.15 and abs(t["lat"]) < 1.2]
    cl = [c for c in h["clusters"] if abs(c["d"] - X) <= 1.0 and abs(c["lat"]) < 1.2]
    print(f"k {k} X {X:6.2f} {r['decision']:7s} hit {int(r['hit'])} | clusters "
          + "; ".join(f"{c['zone']}/{c['reason'] or '-'} h{c['h']} core{int(c['core'])} ng{c['n_gauge']}" for c in cl)
          + " | tracks "
          + "; ".join(f"id{t['id']} hits{t['hits']} rep{int(t['reported'])} col{t['col_hits']}/{len(t['column_hist'])}"
                      f" hold{t['column_hold']} core{t['core_hits']}{'R' if t['core_ready'] else ''} q{int(t['q_run'])}"
                      for t in near))
