#!/usr/bin/env python3
"""Per-row comparison of two replay jsonl files on every field except wall-clock timing.

    rowdiff.py a.jsonl b.jsonl [--ignore far,far_state,far_measure] [--show 5]
Prints the number of rows, the number of differing rows, and per field the count of differences."""
import argparse
import json
from collections import Counter

TIMING = {"decode_ms", "detect_ms", "total_ms"}


def norm(r, ignore):
    r = {k: v for k, v in r.items() if k not in TIMING and k not in ignore}
    # the latency health message is wall-clock dependent
    if "msgs" in r:
        r["msgs"] = [m for m in r["msgs"] if "latency" not in m]
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--ignore", default="far,far_state,far_measure")
    ap.add_argument("--show", type=int, default=5)
    a = ap.parse_args()
    ig = set(a.ignore.split(",")) if a.ignore else set()
    A = [json.loads(line) for line in open(a.a)]
    B = [json.loads(line) for line in open(a.b)]
    fields, diff, shown = Counter(), [], 0
    for ra, rb in zip(A, B):
        na, nb = norm(ra, ig), norm(rb, ig)
        if na != nb:
            diff.append(ra["i"])
            for k in set(na) | set(nb):
                if na.get(k) != nb.get(k):
                    fields[k] += 1
            if shown < a.show:
                shown += 1
                print("row", ra["i"], {k: (na.get(k), nb.get(k)) for k in set(na) | set(nb) if na.get(k) != nb.get(k) and k not in ("dets", "warns", "track_detail")})
    print(json.dumps({"rows_a": len(A), "rows_b": len(B), "differing_rows": len(diff), "fields": dict(fields),
                      "first_diff": diff[:10]}))


if __name__ == "__main__":
    main()
