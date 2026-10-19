#!/usr/bin/env python3
"""B2 checks and summary of the whole-recording Falcon run.

    check_b2.py <full run .jsonl> <17.10 prefix run .jsonl> <17.10 window run .jsonl> <out.json>

1. The first frames must equal the 17.10 prefix run (same data, same fresh detector), all fields but timing.
2. The 241-329 s part must contain every bag time of the 17.10 window run.
3. Summary by part of the recording (0-98, 98-241, 241-329, 329-444 s): decisions, STOP episodes (frames, nearest
   detection), the distances and laterals of the warnings that keep the node in CAUTION.
"""
import json
import sys
from collections import Counter

TIMING = {"decode_ms", "detect_ms", "total_ms", "msgs"}
PARTS = [("0-98 s (prefix, seen 17.10)", 0, 98.4), ("98-241 s (unseen)", 98.4, 241.2),
         ("241-329 s (window, seen 17.10)", 241.2, 328.6), ("329-444 s (unseen)", 328.6, 1e9)]


def load(p):
    return [json.loads(x) for x in open(p)]


def strip(r):
    return {k: v for k, v in r.items() if k not in TIMING}


def main():
    full, pre, win = load(sys.argv[1]), load(sys.argv[2]), load(sys.argv[3])
    t0 = full[0]["bag_t"]
    same = sum(strip(a) == strip(b) for a, b in zip(full, pre))
    first_diff = next((i for i, (a, b) in enumerate(zip(full, pre)) if strip(a) != strip(b)), None)
    full_t = {round(r["bag_t"], 4) for r in full}
    win_t = [round(r["bag_t"], 4) for r in win]
    out = {"frames": len(full), "duration_s": round(full[-1]["bag_t"] - t0, 1),
           "prefix_equal_frames": same, "prefix_frames": len(pre), "prefix_first_difference": first_diff,
           "window_times_found": sum(t in full_t for t in win_t), "window_frames": len(win),
           "max_gap_s": round(max(b["bag_t"] - a["bag_t"] for a, b in zip(full, full[1:])), 3),
           "resets": [], "parts": {}}
    for name, lo, hi in PARTS:
        rows = [r for r in full if lo <= r["bag_t"] - t0 < hi]
        eps, cur = [], None
        for r in rows:
            if r["decision"] == "STOP":
                if cur and r["i"] - cur["last"] <= 3:
                    cur["last"] = r["i"]
                    cur["frames"] += 1
                else:
                    cur = {"first": r["i"], "last": r["i"], "frames": 1, "t_s": round(r["bag_t"] - t0, 1),
                           "d": [round(d["d"], 1) for d in r["dets"]], "lat": [round(d["lat"], 2) for d in r["dets"]]}
                    eps.append(cur)
        warn = Counter()
        for r in rows:
            for wd in r["warns"]:
                warn[(round(wd["d"] / 5) * 5, round(wd["lat"] * 2) / 2)] += 1
        out["parts"][name] = {"frames": len(rows), "decisions": dict(Counter(r["decision"] for r in rows)),
                              "caution_share": round(sum(r["decision"] == "CAUTION" for r in rows) / max(len(rows), 1), 3),
                              "stop_episodes": eps,
                              "top_warnings_d5m_lat0.5m": [[k[0], k[1], v] for k, v in warn.most_common(6)]}
    json.dump(out, open(sys.argv[4], "w"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
