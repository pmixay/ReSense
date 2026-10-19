#!/usr/bin/env python3
"""Markdown tables of the injection matrix (PROTOCOL §3, amendment A1) for the report.

    make_tables.py <name>=<summary.json> [...] > tables.md

Static: STOP fraction over the 15 s (median of 3 seeds) and seconds to the first STOP (median);
"held" = STOP fraction after the first STOP. Approach: first STOP distance (median, range) and the
held fraction after it. E3: the largest static range with first STOP <= 3 s and held >= 0.9 in all
three seeds.
"""
import json
import sys
from collections import defaultdict

import numpy as np

ORDER = ["person_front", "person_back", "cube10", "cube20", "cube50", "box2_10", "box2_20", "box2_50", "outside"]
RANGES = (150, 200, 250, 300, 350)


def load(path):
    rows = defaultdict(list)
    for c in json.load(open(path))["cases"]:
        rows[(c["target"], c["mode"], c.get("range"))].append(c)
    return rows


def med(v):
    v = [x for x in v if x is not None]
    return None if not v else float(np.median(v))


def held(c):
    return c.get("held_fraction_after_first_stop") or 0.0


def static_cell(cs):
    f = med([c["stop_fraction"] for c in cs])
    t = med([c["seconds_to_first_stop"] for c in cs])
    n_stop = sum(c["seconds_to_first_stop"] is not None for c in cs)
    if not n_stop:
        return "—"
    return f"{f:.2f} / {t:.1f} s" + ("" if n_stop == len(cs) else f" ({n_stop}/{len(cs)})")


def e3(rows, target):
    ok = [D for D in RANGES if all(c["seconds_to_first_stop"] is not None and c["seconds_to_first_stop"] <= 3.0
                                   and held(c) >= 0.9 for c in rows[(target, "static", D)])]
    return max(ok) if ok else None


def main():
    runs = [a.split("=", 1) for a in sys.argv[1:]]
    data = {n: load(p) for n, p in runs}
    print("### Static targets: STOP fraction of 15 s / seconds to first STOP (median of 3 seeds)\n")
    print("| target | run | " + " | ".join(f"{D} m" for D in RANGES) + " | E3 stable to |")
    print("|---|---|" + "---|" * (len(RANGES) + 1))
    for t in ORDER:
        for n, rows in data.items():
            print(f"| {t} | {n} | " + " | ".join(static_cell(rows[(t, 'static', D)]) for D in RANGES)
                  + f" | {e3(rows, t) or '—'} |")
    print("\n### Approach from 400 m at 10 m/s: first output / first STOP distance, held fraction after first STOP\n")
    print("| target | run | first output m | first STOP m (min–max) | held after first STOP |")
    print("|---|---|---|---|---|")
    for t in ORDER:
        for n, rows in data.items():
            cs = rows[(t, "approach", None)]
            fs = [c["first_stop_x"] for c in cs if c["first_stop_x"] is not None]
            fo = med([c["first_output_x"] for c in cs])
            print(f"| {t} | {n} | {fo if fo is not None else '—'} | "
                  + (f"{med(fs):.0f} ({min(fs):.0f}–{max(fs):.0f})" if fs else "—")
                  + f" | {med([held(c) for c in cs]) if fs else '—'} |")
    print("\n### Returns per frame on the target (median of seeds, same in every run)\n")
    first = next(iter(data.values()))
    print("| target | " + " | ".join(f"{D} m" for D in RANGES) + " |")
    print("|---|" + "---|" * len(RANGES))
    for t in ORDER:
        print(f"| {t} | " + " | ".join(f"{med([c['returns_per_frame'] for c in first[(t, 'static', D)]]):.1f}" for D in RANGES) + " |")


if __name__ == "__main__":
    main()
