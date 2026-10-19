"""Associate detector outputs with a known target path (raw ROS frame, track reference lateral).

A detection or warning belongs to the target when its centre, mapped back to the raw frame
(``c @ mount_rotation`` with the explicit falcon_ros axes), lies within ALONG m along and LAT m
laterally (track reference) of the target's path position at that frame."""
import json

import numpy as np

ALONG, LAT = 2.5, 1.0


def load(path):
    return [json.loads(line) for line in open(path)]


def target_at(path, i):
    P = np.asarray(path, dtype=np.float64)
    if i < P[0, 0] or i > P[-1, 0]:
        return None
    return float(np.interp(i, P[:, 0], P[:, 1])), float(np.interp(i, P[:, 0], P[:, 2]))


def raw_center(det, row):
    return np.asarray(det["c"]) @ np.asarray(row["mount_rotation"])


def associate(rows, path, track, frames):
    """Per frame in ``frames``: (target along, stop?, warn?, reported distance, reported lateral)."""
    by = {r["i"]: r for r in rows}
    out = []
    for i in frames:
        t = target_at(path, i)
        r = by.get(i)
        if t is None or r is None:
            continue
        x, lat = t
        hit = {"dets": None, "warns": None}
        for field in ("dets", "warns"):
            for d in r[field]:
                c = raw_center(d, r)
                lr = c[1] - (track["a"] + track["b"] * c[0])
                if abs(c[0] - x) < ALONG and abs(lr - lat) < LAT:
                    hit[field] = d
                    break
        out.append({"i": i, "x": x, "stop": hit["dets"] is not None, "warn": hit["warns"] is not None,
                    "decision": r["decision"],
                    "d": (hit["dets"] or hit["warns"] or {}).get("d"), "lat": (hit["dets"] or hit["warns"] or {}).get("lat"),
                    "other_stop": r["decision"] == "STOP" and hit["dets"] is None})
    return out


def summary(assoc, bands):
    s = {"frames": len(assoc)}
    first_any = next((a for a in assoc if a["stop"] or a["warn"]), None)
    first_stop = next((a for a in assoc if a["stop"]), None)
    s["first_output_x"] = None if first_any is None else round(first_any["x"], 1)
    s["first_stop_x"] = None if first_stop is None else round(first_stop["x"], 1)
    s["first_stop_frame"] = None if first_stop is None else first_stop["i"]
    if first_stop is not None:
        after = [a for a in assoc if a["i"] >= first_stop["i"]]
        s["held_fraction_after_first_stop"] = round(sum(a["stop"] for a in after) / len(after), 3)
    s["bands"] = {}
    for hi, lo in bands:
        b = [a for a in assoc if lo <= a["x"] < hi]
        if b:
            lats = [a["lat"] for a in b if a["lat"] is not None]
            s["bands"][f"{hi}-{lo}"] = {"frames": len(b), "stop": round(sum(a["stop"] for a in b) / len(b), 3),
                                        "output": round(sum(a["stop"] or a["warn"] for a in b) / len(b), 3),
                                        "reported_lat_median": round(float(np.median(lats)), 2) if lats else None}
    s["other_stop_frames"] = sum(a["other_stop"] for a in assoc)
    return s
