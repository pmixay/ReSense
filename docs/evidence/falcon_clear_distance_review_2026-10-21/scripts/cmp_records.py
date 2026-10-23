"""Independent comparator of two judge-record jsonl.xz files (own code, not the author's compare_falcon.py).
usage: cmp_records.py A B [--inject FIELD]   A = reference, B = candidate.
Skips timing fields. Reports rows differing per field, rows where clear rose/fell, and (with --inject) a
positive control: one row of B gets FIELD perturbed, the comparator must report exactly that row."""
import json, lzma, sys, copy
TIMING = {"decode_ms", "detect_ms", "total_ms"}
def load(p): return [json.loads(l) for l in lzma.open(p, "rt")]
def cmp(A, B):
    assert len(A) == len(B), (len(A), len(B))
    diff, up, down = {}, [], []
    for a, b in zip(A, B):
        assert a["i"] == b["i"]
        for k in set(a) | set(b):
            if k in TIMING: continue
            if a.get(k) != b.get(k):
                if k == "clear":
                    (up if b["clear"] > a["clear"] else down).append(a["i"])
                else:
                    diff.setdefault(k, []).append(a["i"])
    return diff, up, down
if __name__ == "__main__":
    A, B = load(sys.argv[1]), load(sys.argv[2])
    if "--inject" in sys.argv:
        f = sys.argv[sys.argv.index("--inject") + 1]; B = copy.deepcopy(B)
        r = B[2000]
        r[f] = (not r[f]) if isinstance(r[f], bool) else ([] if r[f] else [{"x": 1}]) if isinstance(r[f], list) else (str(r[f]) + "X")
    d, up, down = cmp(A, B)
    print(json.dumps({"rows": len(A), "other_fields_differ": {k: len(v) for k, v in d.items()},
                      "first_rows": {k: v[:3] for k, v in d.items()}, "clear_raised": len(up), "clear_lowered": len(down)}))
