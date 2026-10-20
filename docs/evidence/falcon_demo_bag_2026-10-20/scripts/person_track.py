#!/usr/bin/env python3
"""The walking person's distance by frame, from the whole-recording record, and a classifier for STOP frames.

    person_track.py --record l16.jsonl.xz [--out person_track.json]

The record lists, per frame, the detections (``dets``) and warnings (``warns``) of the node. The person is the
object at 110-150 m on the track (lateral -1.6 to 0.4 m; negative = right of the centre line) that approaches
at walking speed. Before frame ``MERGE_FRAME`` (303.3 s) a straight line d(frame) is fitted to those objects
between frames 2900 and 3025 (the person is the only mover there) and refitted on the objects within 1.5 m
of the line between frames 2800 and 3030; the static structures lie elsewhere (105.6 m and 115.1 m at lateral
+1.0 to +1.4, 152-154 m at lateral -0.1 to -1.1). At ``MERGE_FRAME`` the person reaches the 115 m structure
(detection 115.08 m, lateral -0.22, 32 points); from there the record's own object of 15+ points nearest to
the previous frame's distance (within 3 m, the merge moves the centre by 2.6 m) is followed.

``classify`` labels a STOP frame ``person`` if one of its detections is within ``TOL`` m of the person's
expected distance, else ``other``. This is an attribution aid for reading the cold-start replays, not a
ground truth: there is none.
"""
from __future__ import annotations

import argparse
import json
import lzma

import numpy as np

TOL = 3.5               # m: a detection this close to the person's expected distance is the person
MERGE_FRAME = 3033      # the person reaches the 115 m structure (record: detection 115.08 m, lateral -0.22)


def load(path: str) -> list[dict]:
    with (lzma.open(path, "rt") if path.endswith(".xz") else open(path)) as fh:
        return [json.loads(line) for line in fh]


def fit(rows: list[dict]) -> tuple[float, float, int]:
    pts = np.array([(r["i"], o["d"]) for r in rows[2600:3040] for o in r["dets"] + r["warns"]
                    if -1.6 < o["lat"] < 0.0 and 110 < o["d"] < 150])
    m = (pts[:, 0] >= 2900) & (pts[:, 0] <= 3025) & (pts[:, 1] > 116)
    a = np.polyfit(pts[m, 0], pts[m, 1], 1)
    for _ in range(5):
        res = pts[:, 1] - np.polyval(a, pts[:, 0])
        m = (abs(res) < 1.5) & (pts[:, 0] >= 2800) & (pts[:, 0] <= 3030)
        a = np.polyfit(pts[m, 0], pts[m, 1], 1)
    return float(a[1]), float(a[0]), int(m.sum())


def follow(rows: list[dict], a0: float, a1: float, last: int = 3400) -> dict[int, float]:
    """Expected distance of the person per frame: the line before MERGE_FRAME, then the followed record object."""
    out = {f: a0 + a1 * f for f in range(2600, MERGE_FRAME)}
    d = out[MERGE_FRAME - 1]
    for f in range(MERGE_FRAME, last + 1):
        near = [o["d"] for o in rows[f]["dets"] + rows[f]["warns"]
                if -1.6 < o["lat"] < 0.4 and o["n"] >= 15 and abs(o["d"] - d) < 3.0]
        if near:
            d = min(near, key=lambda v: abs(v - d))
        else:
            d += a1                      # no object this frame: keep walking at the fitted speed
        out[f] = d
    return out


def classify(row: dict, frame: int, track: dict[int, float]) -> str:
    """'person' | 'other' for a STOP row (its detections against the person's expected distance)"""
    e = track[frame]
    return "person" if any(abs(d["d"] - e) <= TOL for d in row["dets"]) else "other"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--record", required=True)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    rows = load(a.record)
    a0, a1, n = fit(rows)
    track = follow(rows, a0, a1)
    first = next(f for f in range(2600, 3040) if any(
        abs(o["d"] - track[f]) < 1.5 and -1.6 < o["lat"] < 0.0 for o in rows[f]["dets"] + rows[f]["warns"]))
    stops = [r["i"] for r in rows if r["decision"] == "STOP" and 2600 <= r["i"] <= 3400]
    other = [f for f in stops if classify(rows[f], f, track) == "other"]
    out = {"d0": a0, "d_per_frame": a1, "speed_m_per_s": round(-a1 * 10, 3), "points_in_fit": n,
           "first_frame_with_object_on_the_line": first, "distance_at_frame_2972": round(track[2972], 2),
           "distance_at_3033": round(track[3033], 2), "distance_at_3200": round(track[3200], 2),
           "tolerance_m": TOL, "record_stop_frames_2600_3400": len(stops),
           "record_stop_frames_2600_3400_not_on_person": other}
    print(json.dumps(out, indent=1))
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
