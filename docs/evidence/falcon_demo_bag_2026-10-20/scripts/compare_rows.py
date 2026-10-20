#!/usr/bin/env python3
"""Row-by-row identity of two per-frame replay records, ignoring only wall-clock timing.

    compare_rows.py A.jsonl B.jsonl [--offset-b N]

Rows are paired by position (row k of A with row k + N of B). Compared: every field except the timings
(``decode_ms``, ``detect_ms``, ``total_ms``), the row number ``i`` and the added ``frame``. The health ``level``,
``dlevel`` and ``msgs`` are compared as they are (the latency budget cannot trigger in these replays: no row of
either file carries a latency message; this is checked and printed).
"""
from __future__ import annotations

import argparse
import json

IGNORED = {"decode_ms", "detect_ms", "total_ms", "i", "frame"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("a")
    ap.add_argument("b")
    ap.add_argument("--offset-b", type=int, default=0)
    args = ap.parse_args()
    ra = [json.loads(line) for line in open(args.a)]
    rb = [json.loads(line) for line in open(args.b)][args.offset_b:]
    n = min(len(ra), len(rb))
    differ = [k for k in range(n) if {x: y for x, y in ra[k].items() if x not in IGNORED}
              != {x: y for x, y in rb[k].items() if x not in IGNORED}]
    latency = sum(any("latency" in m for m in r["msgs"]) for r in ra[:n] + rb[:n])
    print(json.dumps({"rows_a": len(ra), "rows_b_from_offset": len(rb), "compared": n, "rows_different": len(differ),
                      "first_different_rows": differ[:10], "rows_with_a_latency_message": latency}))
    return 0 if not differ and len(ra) == len(rb) else 1


if __name__ == "__main__":
    raise SystemExit(main())
