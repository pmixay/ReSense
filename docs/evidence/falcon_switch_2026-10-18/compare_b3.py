#!/usr/bin/env python3
"""B3 / B8: does a switch of lidar inside one detector behave exactly like a fresh start?

    compare_b3.py <run dir> <out.json>

For ``p2f`` (Pandar then Falcon) and ``f2p`` (Falcon then Pandar) every frame record is compared
with the same frame of the bag run alone (``pandar`` / ``falcon``), all fields but the wall-clock
timing ones. Also reports the runner's resets at the switch, the first frames after it (decision,
health messages, mount state) and per-sensor timing (decode / detect / total ms, p50 / p95 / max)
from the stand-alone runs.
"""
import json
import sys
from pathlib import Path

import numpy as np

TIMING = {"decode_ms", "detect_ms", "total_ms", "i", "msgs"}


def load(p):
    return [json.loads(x) for x in Path(p).read_text().splitlines()]


def same(a, b):
    """Records equal on everything but timing; health messages compared without latency lines."""
    ka = {k: v for k, v in a.items() if k not in TIMING}
    kb = {k: v for k, v in b.items() if k not in TIMING}
    ma = [m for m in a.get("msgs", []) if "latency" not in m]
    mb = [m for m in b.get("msgs", []) if "latency" not in m]
    return ka == kb and ma == mb, sorted(k for k in set(ka) | set(kb) if ka.get(k) != kb.get(k))


def timing(rows):
    out = {}
    for k in ("decode_ms", "detect_ms", "total_ms"):
        v = np.array([r[k] for r in rows[1:]], dtype=float)  # frame 0 pays first-call costs
        out[k] = {"p50": round(float(np.percentile(v, 50)), 1), "p95": round(float(np.percentile(v, 95)), 1),
                  "max": round(float(v.max()), 1)}
    out["frames"] = len(rows)
    out["points_median"] = int(np.median([r["n_points"] for r in rows]))
    out["over_100ms_total"] = int(sum(r["total_ms"] > 100 for r in rows[1:]))
    return out


def decisions(rows):
    c = {}
    for r in rows:
        c[r["decision"]] = c.get(r["decision"], 0) + 1
    return c


def main():
    d, out_path = Path(sys.argv[1]), sys.argv[2]
    alone = {"pandar": load(d / "pandar.jsonl"), "falcon": load(d / "falcon.jsonl")}
    res = {"alone": {k: {"decisions": decisions(v), "timing": timing(v)} for k, v in alone.items()}}
    for name, order in (("p2f", ("pandar", "falcon")), ("f2p", ("falcon", "pandar"))):
        rows = load(d / f"{name}.jsonl")
        meta = json.loads((d / f"{name}.meta.json").read_text())
        first = alone[order[0]]
        second = alone[order[1]]
        n0 = len(first)
        diff1 = [(i, same(rows[i], first[i])[1]) for i in range(n0) if not same(rows[i], first[i])[0]]
        diff2 = [(i, same(rows[n0 + i], second[i])[1]) for i in range(len(second))
                 if not same(rows[n0 + i], second[i])[0]]
        after = [{"i": r["i"], "decision": r["decision"], "mount": r.get("mount"), "frame_id": r["frame_id"],
                  "msgs": r["msgs"][:2]} for r in rows[n0:n0 + 3]]
        res[name] = {"order": order, "frames": len(rows), "resets": meta["resets"],
                     "first_part_differs": len(diff1), "second_part_differs": len(diff2),
                     "differences": (diff1 + diff2)[:10], "first_frames_after_switch": after,
                     "decisions": decisions(rows)}
    json.dump(res, open(out_path, "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
