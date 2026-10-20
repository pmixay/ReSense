"""Set F: 30 sequences / 3,060 rows, candidate vs reference, with a planted flip and a wrong-sequence control.

    python setf_rows.py <setF_straight.json candidate> <setF_straight.json reference>
"""
import collections
import copy
import json
import sys

c, r = (json.load(open(p)) for p in sys.argv[1:3])


def cmp(c, r):
    rows = diff = lost = added = 0
    hits = [0, 0]
    fields = collections.Counter()
    for a, b in zip(c["sequences"], r["sequences"]):
        assert (a["kind"], a["d0"], a["lateral"], a["file0"]) == (b["kind"], b["d0"], b["lateral"], b["file0"])
        assert len(a["rows"]) == len(b["rows"])
        for x, y in zip(a["rows"], b["rows"]):
            rows += 1
            if x != y:
                diff += 1
                fields.update(k for k in set(x) | set(y) if x.get(k) != y.get(k))
            hits[0] += bool(x["hit"])
            hits[1] += bool(y["hit"])
            lost += bool(y["hit"]) and not x["hit"]
            added += bool(x["hit"]) and not y["hit"]
    return dict(rows=rows, differing=diff, fields=dict(fields), hits_candidate=hits[0], hits_reference=hits[1], lost=lost, added=added)


print("kinds", dict(collections.Counter(s["kind"] for s in c["sequences"])), "sequences", len(c["sequences"]))
print("candidate vs reference:", cmp(c, r))
c2 = copy.deepcopy(c)
c2["sequences"][3]["rows"][50]["hit"] = not c2["sequences"][3]["rows"][50]["hit"]
print("planted hit flip:", cmp(c2, r))
c3 = copy.deepcopy(c)
c3["sequences"][0]["rows"] = c3["sequences"][1]["rows"][: len(c3["sequences"][0]["rows"])]
print("wrong-sequence control rows differing:", cmp(c3, r)["differing"])
print("summary per_kind equal:", c["summary"]["per_kind"] == r["summary"]["per_kind"])
