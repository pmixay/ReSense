#!/usr/bin/env python3
"""Per-frame comparison of two record sets (gate work directories of per-recording ``*.jsonl``, or two single
``.jsonl`` files): rows aligned by position (same count, same stamp; fails closed), every key compared recursively
except timing keys and machine-speed latency health messages. Reports differing rows per file and per top-level
key; with ``--skip K`` (repeatable) key K is left out at every depth and reported separately as lowered / raised
(numeric) counts. ``--inject`` is the positive control: one row of the second set is altered (n_points + 1, or a
detection distance + 0.1 m) and must come back as exactly one extra differing row.

    rows_diff.py A B [--skip clear_distance] [--inject] [--show 5]
"""
import argparse, glob, json, lzma, os, sys

TIMING = {"timing_ms", "latency_ms", "latency_p95_ms", "wall_ms", "total_ms", "t_ms", "cpu_ms", "proc_ms", "ms",
          "timing", "elapsed_ms", "decode_ms", "detect_ms"}


def opn(p):
    return lzma.open(p, "rt") if p.endswith(".xz") else open(p)


def load(p):
    return [json.loads(l) for l in opn(p) if l.strip()]


def strip(o, skip, out):
    if isinstance(o, dict):
        r = {}
        for k, v in o.items():
            if k in TIMING:
                continue
            if k in skip:
                out.setdefault(k, []).append(v)
                continue
            if k == "messages" and isinstance(v, list):
                v = [m for m in v if "latency" not in str(m)]
            r[k] = strip(v, skip, out)
        return r
    if isinstance(o, list):
        return [strip(v, skip, out) for v in o]
    return o


def pairs(a, b):
    if os.path.isdir(a):
        for fa in sorted(glob.glob(os.path.join(a, "*.jsonl")) + glob.glob(os.path.join(a, "*.jsonl.xz"))):
            fb = os.path.join(b, os.path.basename(fa))
            if not os.path.exists(fb):
                sys.exit(f"missing in B: {fb}")
            yield os.path.basename(fa), fa, fb
        na = len(glob.glob(os.path.join(a, "*.jsonl*"))); nb = len(glob.glob(os.path.join(b, "*.jsonl*")))
        if na != nb:
            sys.exit(f"file count differs {na} {nb}")
    else:
        yield os.path.basename(a), a, b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("a"); ap.add_argument("b")
    ap.add_argument("--skip", action="append", default=[])
    ap.add_argument("--inject", action="store_true")
    ap.add_argument("--show", type=int, default=3)
    x = ap.parse_args()
    skip = set(x.skip)
    tot = dif = 0; keys = {}; lowered = raised = 0; injected = False
    for name, fa, fb in pairs(x.a, x.b):
        ra, rb = load(fa), load(fb)
        if len(ra) != len(rb):
            sys.exit(f"{name}: row count {len(ra)} vs {len(rb)}")
        if x.inject and not injected and ra:
            r = rb[len(rb) // 2]
            if "n_points" in r:
                r["n_points"] += 1
            elif r.get("dets"):
                r["dets"][0]["d"] += 0.1
            else:
                r["__injected__"] = 1
            injected = True
        d = 0; shown = 0
        for i, (p, q) in enumerate(zip(ra, rb)):
            sp, sq = p.get("stamp", i), q.get("stamp", i)
            if sp != sq:
                sys.exit(f"{name} row {i}: stamp {sp} vs {sq}")
            tot += 1
            oa, ob = {}, {}
            a, b = strip(p, skip, oa), strip(q, skip, ob)
            for k in skip:
                for u, v in zip(oa.get(k, []), ob.get(k, [])):
                    if isinstance(u, (int, float)) and isinstance(v, (int, float)):
                        lowered += v < u; raised += v > u
            if a != b:
                d += 1
                ks = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
                for k in ks:
                    keys[k] = keys.get(k, 0) + 1
                if shown < x.show:
                    print(f"  {name} row {i}: differs in {ks}")
                    shown += 1
        dif += d
        print(f"{name}: {len(ra)} rows, {d} differ")
    print(f"TOTAL {tot} rows, {dif} differ; by key {keys}")
    if skip:
        print(f"skipped keys {sorted(skip)}: lowered {lowered}, raised {raised} (numeric leaf values)")


if __name__ == "__main__":
    main()
