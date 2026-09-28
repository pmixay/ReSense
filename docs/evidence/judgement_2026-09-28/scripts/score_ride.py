"""The ride (ride_consumer.py output) scored per split: frames, STOP / CAUTION frames and STOP episodes
(runs of STOP frames inside one split, a one-frame gap merged), with their distance ranges, and the
rates per 1 000 frames, per hour at 10 Hz and per km over the recording's 13.0 km.

    python score_ride.py ride.jsonl > ride_summary.json
"""
import json
import sys
from collections import defaultdict

KM = 13.0


def main(path: str) -> None:
    splits = defaultdict(list)
    for line in open(path):
        r = json.loads(line)
        splits[r["split"]].append(r)
    frames = stop = caution = 0
    episodes = []
    for name, rows in splits.items():
        rows.sort(key=lambda r: r["i"])
        s = [r["obstacle"] for r in rows]
        frames += len(rows)
        stop += sum(s)
        caution += sum((not r["obstacle"]) and r["warning"] for r in rows)
        i = 0
        while i < len(s):
            if not s[i]:
                i += 1
                continue
            j = i
            while j + 1 < len(s) and (s[j + 1] or (j + 2 < len(s) and s[j + 2])):
                j += 1
            ds = [r["nearest_distance"] for r in rows[i:j + 1] if r["nearest_distance"] is not None]
            episodes.append({"split": name, "frames": [rows[i]["i"], rows[j]["i"]],
                             "distance_m": [round(min(ds), 1), round(max(ds), 1)]})
            i = j + 1
    hours = frames / 10 / 3600
    print(json.dumps({"splits": len(splits), "frames": frames, "stop_frames": stop, "caution_frames": caution,
                      "stop_episodes": len(episodes),
                      "stop_episodes_per_1000_frames": round(len(episodes) / frames * 1000, 2),
                      "stop_episodes_per_hour": round(len(episodes) / hours, 1),
                      "stop_episodes_per_km": round(len(episodes) / KM, 2),
                      "episodes": episodes}, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
