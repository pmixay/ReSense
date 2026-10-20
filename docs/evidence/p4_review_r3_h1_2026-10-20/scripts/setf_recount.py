"""Independent recount of two set F raw files (gate work ``setF_straight.json``, R3 off -> on), without the
comparator or the evaluator's summary: per sequence, hits lost / added row by row (rows matched by frame id),
whether visibility (n > 0) and placement (d, gt distance) agree, and sustained range (held90) recomputed here by
sorted-distance integer counts (visible rows, share of hits among the rows at distance <= D at least 90 %, at
least 5 rows; the largest such D). Compared with the file's own ``summary`` medians and per-kind counts.

    python setf_recount.py <off setF_straight.json> <on setF_straight.json>
"""
import json
import statistics
import sys

off, on = (json.load(open(p)) for p in sys.argv[1:3])
assert len(off["sequences"]) == len(on["sequences"])


def held90(rows):
    vis = sorted((r["d"], bool(r["hit"])) for r in rows if r["n"] > 0)
    best, n, h, i = None, 0, 0, 0
    while i < len(vis):
        j = i
        while j < len(vis) and vis[j][0] == vis[i][0]:
            j += 1
        n, h = j, sum(x[1] for x in vis[:j])
        if n >= 5 and h * 10 >= 9 * n:
            best = vis[i][0]
        i = j
    return best


kinds = {}
for a, b in zip(off["sequences"], on["sequences"]):
    ident = ("kind", "d0", "refl", "file0", "placement_mode")
    assert all(a[k] == b[k] for k in ident), (a["kind"], b["kind"])
    ra, rb = a["rows"], b["rows"]
    assert [r["frame"] for r in ra] == [r["frame"] for r in rb]
    d = kinds.setdefault(a["kind"], {"lost": 0, "added": 0, "same_vis": True, "same_d": True, "same_fp": True,
                                     "off": [], "on": [], "add_rows": []})
    for x, y in zip(ra, rb):
        d["lost"] += bool(x["hit"]) and not y["hit"]
        d["added"] += (not x["hit"]) and bool(y["hit"])
        if not x["hit"] and y["hit"]:
            d["add_rows"].append((x["frame"], x["d"], x["n"]))
        d["same_vis"] &= (x["n"] > 0) == (y["n"] > 0)
        d["same_d"] &= x["d"] == y["d"] and x["gt"]["distance"] == y["gt"]["distance"]
        d["same_fp"] &= len(x["fp_dets"]) == len(y["fp_dets"]) or len(y["fp_dets"]) <= len(x["fp_dets"])
    d["off"].append(held90(ra))
    d["on"].append(held90(rb))
med = lambda v: round(statistics.median(v), 1) if v else None  # noqa: E731
for k, d in kinds.items():
    so, sn = [v for v in d["off"] if v is not None], [v for v in d["on"] if v is not None]
    print(f"{k:8s} hits lost {d['lost']} added {d['added']} | visibility same {d['same_vis']} distances same {d['same_d']} "
          f"| held90 off {len(so)}/6 median {med(so)} -> on {len(sn)}/6 median {med(sn)}")
    print("          off", [None if v is None else round(v, 1) for v in d["off"]],
          "on", [None if v is None else round(v, 1) for v in d["on"]])
    if d["added"]:
        print("          added rows (frame, d, n_returns):", d["add_rows"])
    s_off, s_on = off["summary"]["per_kind"][k], on["summary"]["per_kind"][k]
    print(f"          file's own summary: sustained_median {s_off['sustained_median']} -> {s_on['sustained_median']}; "
          f"sustained list {s_off['sustained_m']} -> {s_on['sustained_m']}")
