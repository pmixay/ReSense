"""Field-by-field comparison of judge_runner records, one line per (bag, run): which fields differ in which frames.

Every field except the timing ones (decode_ms, detect_ms, total_ms) is compared; the health ``msgs`` after dropping the
wall-clock "latency ..." messages, and ``level`` only when it is not explained by those messages alone (the rule of
compare_runs.py). Prints 'IDENT' or ``field[first frames](count)``. With --verbose also the values of the first
--show differing frames.

    python field_diff.py <a prefix> <b prefix> [--bags platform,switch,tunnels] [--verbose] [--show 5]
(prefix + "_<bag>.jsonl")
"""
import argparse
import json

TIM = {"decode_ms", "detect_ms", "total_ms"}
ap = argparse.ArgumentParser()
ap.add_argument("a")
ap.add_argument("b")
ap.add_argument("--bags", default="platform,switch,tunnels")
ap.add_argument("--verbose", action="store_true")
ap.add_argument("--show", type=int, default=5)
args = ap.parse_args()


def nl(m):
    return [x for x in m if not x.startswith("latency")]


def diff(a, b):
    out = {}
    for x, y in zip(a, b):
        for k in set(x) | set(y):
            if k in TIM:
                continue
            if k == "msgs":
                same = nl(x[k]) == nl(y[k])
            elif k == "level":
                same = x[k] == y[k] or (not nl(x["msgs"]) and not nl(y["msgs"]))
            else:
                same = x.get(k) == y.get(k)
            if not same:
                out.setdefault(k, []).append(x["i"])
    return out


for bag in args.bags.split(","):
    a = [json.loads(line) for line in open(f"{args.a}_{bag}.jsonl")]
    b = [json.loads(line) for line in open(f"{args.b}_{bag}.jsonl")]
    assert len(a) == len(b), (bag, len(a), len(b))
    d = diff(a, b)
    print(f"{bag:9s} {len(a)} frames: " + ("IDENT" if not d else "; ".join(f"{k}{v[:6]}({len(v)})" for k, v in d.items())))
    if args.verbose:
        shown = sorted({i for v in d.values() for i in v})[:args.show]
        for i in shown:
            for k, v in d.items():
                if i in v:
                    print(f"    frame {i} {k}: a={a[i].get(k)!r}  b={b[i].get(k)!r}")
