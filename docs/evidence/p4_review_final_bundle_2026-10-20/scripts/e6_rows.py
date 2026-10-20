"""E6 (standing 5 cm cable, the judge's range probe) re-counted from the raw rows of R3's range runs.

    python e6_rows.py <range-a-candidate.json> <range-a-reference.json>

visible = rows with returns on the object (n_obj > 0) and X > 3 m; matched = visible rows whose ``hit`` is set (the probe's
own STOP-on-the-object test); first STOP = X of the first matched row in file order; held from ("held90" of the judge's
definition) = the largest X for which, counting the visible rows from the nearest one outward, at least 90 % are matched.
"""
import json
import sys

a, b = (json.load(open(p)) for p in sys.argv[1:3])


def recount(d):
    rows = d["rows"]
    vis = [r for r in rows if r["X"] is not None and r["X"] > 3.0 and r["n_obj"] > 0]
    first = next((r["X"] for r in vis if r["hit"]), None)
    held, n_hit = None, 0
    for n, r in enumerate(sorted(vis, key=lambda r: r["X"]), 1):
        n_hit += bool(r["hit"])
        if n_hit >= 0.9 * n:
            held = r["X"]
    return dict(rows=len(rows), visible=len(vis), matched=sum(bool(r["hit"]) for r in vis), first_stop=first, held_from=held)


ra, rb = recount(a), recount(b)
s = a["summary"]
print("candidate recount:", ra, "| published summary:", dict(visible=s["visible_frames"], matched=s["stop_frames"], first_stop=s["first_stop_X"], held_from=s["held_from_X"]))
strip = lambda r: {k: v for k, v in r.items() if k not in ("timing_ms",)}
print("rows differing between candidate and reference:", sum(json.dumps(strip(x), sort_keys=True) != json.dumps(strip(y), sort_keys=True) for x, y in zip(a["rows"], b["rows"])), "of", len(a["rows"]))
print("reference recount:", rb)
