"""Frame counts of an offline run (`resense run --out` JSONL): STOP / CAUTION / GO frames and STOP
episodes (runs of STOP frames, a one-frame gap merged) with their distance range.

    python score_bag.py <run.jsonl> ...
"""
import json
import sys


def score(path: str) -> dict:
    rows = [json.loads(line) for line in open(path)]
    stop = [r["obstacle"] for r in rows]
    caution = [(not r["obstacle"]) and r["warning"] for r in rows]
    episodes = []
    i, n = 0, len(rows)
    while i < n:
        if not stop[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and (stop[j + 1] or (j + 2 < n and stop[j + 2])):
            j += 1
        ds = [r["nearest_distance"] for r in rows[i:j + 1] if r["nearest_distance"] is not None]
        episodes.append((i, j, round(min(ds), 1), round(max(ds), 1)))
        i = j + 1
    return dict(frames=n, stop_frames=sum(stop), caution_frames=sum(caution),
                go_frames=n - sum(stop) - sum(caution), stop_episodes=episodes)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(p.split("/")[-1], json.dumps(score(p)))
