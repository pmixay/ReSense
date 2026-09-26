#!/usr/bin/env python3
"""Ground truth for the organizers' synthetic-obstacle recording ``cloud_with_fake_obj``.

    python scripts/label_fake_objects.py /data/cloud_with_fake_obj --out labels/cloud_with_fake_obj.json

The organizers built this bag by ray-casting ten obstacles into a real recording. Each
PointCloud2 message is the organized real scan (128 x 2400 points, no-return points kept as
zeros, the returns an object hides removed) followed by the object points, all with
intensity 1. So the object points of every frame are exactly the points after the last zero
point of the message; nothing is guessed from the detector's output.

The object points of one frame are split into objects at gaps of more than ``--gap`` m in X
and linked across frames into tracks (they stand still in the tunnel and approach by the
train's own displacement, 1.4-20 m/s; docs/EXPERIMENTS.md §9). The tracks are
numbered in the order they pass the sensor. That order is the organizers' list of 24.09
(``OBJECTS``), each obstacle ~100 m behind the one before it: the script stops if it does not
find exactly ten tracks.

Positions follow ``docs/DATASET.md`` "Label format". ``distance`` is the nearest object point
in the detector's (mount-calibrated) vehicle frame. ``lateral`` is the object's centre from the
track axis of the shipped detector in that frame, as for ``labels/doubleT_obstacle.json``:
the detector reports its detections against that same axis. ``in_gauge`` is the organizers'
intent (inside / outside the envelope), not the measured position, except that it is false
on rows that are not ``plausible`` (far away the organizers' path leaves the tunnel), so that
``resense eval`` does not count those as misses. ``gauge_margin``, ``h_above_rail``,
``lateral_sensor`` and ``n_in_envelope`` record the measured position. Only frames in which an object has at
least one point inside the sensor's range filter carry a row for it, and a frame with no
object points is labelled empty (``[]``).
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import frame_from_compact, sensor_to_vehicle  # noqa: E402
from resense.gauge import corridor_coordinates  # noqa: E402
from resense.pointcloud import pointcloud2_to_structured, structured_to_compact  # noqa: E402

# The organizers' description (24.09), in the order the obstacles pass the train. size: [L, W, H] m
OBJECTS = [
    ("big_center", "box", [2.0, 2.0, 2.0], True, "посередине габарита крупный, 2х2 метра"),
    ("small_center", "box", [0.3, 0.3, 0.3], True, "посередине габарита мелкий 0.3х0.3 м"),
    ("small_on_rail", "box", [0.3, 0.3, 0.3], True, "мелкий 0.3х0.3 м стоит на рельсах"),
    ("small_edge_inside", "box", [0.3, 0.3, 0.3], True, "0.3х0.3 м скраю габарита"),
    ("small_outside_near", "box", [0.3, 0.3, 0.3], False, "0.3х0.3 м за пределами габарита, но близко"),
    ("big_edge_inside", "box", [2.0, 2.0, 2.0], True, "2х2 метра скраю в пределах габарита"),
    ("big_outside", "box", [2.0, 2.0, 2.0], False, "2х2 за пределами габарита"),
    # "сверху габарита": at the top of the envelope. Its bottom is 2.4-2.9 m above the rail head in
    # both the sensor's and the track's frame, inside the 3.0 m envelope, so it must alarm (P4, 24.09)
    ("big_above", "box", [2.0, 2.0, 2.0], True, "2х2 сверху габарита"),
    ("long_low_on_rails", "plank", [0.5, 2.0, 0.2], True, "длинный низкий предмет лежит на рельсах (2х0.2)"),
    ("thin_hanging", "cable", [0.05, 0.05, 1.5], True, "узкий длинный свисает с потолка (ширина 0.05 м)"),
]


def split_objects(msg_struct: np.ndarray) -> np.ndarray:
    """The appended object block of one message: every point after the last no-return zero."""
    x = np.asarray(msg_struct["x"]).ravel()
    y = np.asarray(msg_struct["y"]).ravel()
    z = np.asarray(msg_struct["z"]).ravel()
    zero = (x == 0) & (y == 0) & (z == 0)
    start = int(np.flatnonzero(zero)[-1]) + 1 if zero.any() else x.size
    return np.column_stack([x[start:], y[start:], z[start:]]).astype(np.float64)


def group_frame(xyz: np.ndarray, gap: float):
    """Index arrays of the objects of one frame (split at gaps along X)."""
    if not len(xyz):
        return []
    order = np.argsort(xyz[:, 0])
    cuts = np.flatnonzero(np.diff(xyz[order, 0]) > gap) + 1
    return np.split(order, cuts)


def link_tracks(groups_per_frame, max_gap_frames: int = 40):
    """groups_per_frame: {frame: [(x_min, indices), ...]} -> list of tracks [(frame, group_no), ...]."""
    tracks = []      # each: list of (frame, group_no, x_min)
    for k in sorted(groups_per_frame):
        groups = groups_per_frame[k]
        cands = []
        for ti, t in enumerate(tracks):
            kl, _, xl = t[-1]
            if k - kl > max_gap_frames:
                continue
            if len(t) >= 2:
                ka, _, xa = t[-min(len(t), 6)]
                v = (xa - xl) / max(kl - ka, 1)
            else:
                v = 1.8
            xp = xl - v * (k - kl)
            for gi, (x0, _) in enumerate(groups):
                err = abs(x0 - xp)
                if err < max(6.0, 0.08 * x0):
                    cands.append((err, ti, gi))
        t_used, g_used = set(), set()
        for err, ti, gi in sorted(cands):
            if ti in t_used or gi in g_used:
                continue
            tracks[ti].append((k, gi, groups[gi][0]))
            t_used.add(ti)
            g_used.add(gi)
        for gi, (x0, _) in enumerate(groups):
            if gi not in g_used:
                tracks.append([(k, gi, x0)])
    return tracks


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("bag", help="the unpacked bag directory cloud_with_fake_obj/")
    p.add_argument("--out", default="labels/cloud_with_fake_obj.json")
    p.add_argument("--config", default=None, help="detector config for the axis and mount (default: shipped)")
    p.add_argument("--gap", type=float, default=8.0, help="m along X that separates two objects of one frame")
    p.add_argument("--min-track", type=int, default=5, help="frames a track needs to count as an object")
    a = p.parse_args()

    from rosbags.rosbag2 import Reader
    from rosbags.typesys import Stores, get_typestore

    cfg = DetectorConfig.from_yaml(a.config) if a.config else DetectorConfig()
    det = Detector(cfg)
    ts = get_typestore(Stores.ROS2_HUMBLE)
    per_frame = {}          # frame -> list of dicts (points in the corrected vehicle frame + corridor coords)
    groups_per_frame = {}
    n_frames = 0
    topic = frame_id = None
    t0 = None
    with Reader(Path(a.bag)) as reader:
        conns = [c for c in reader.connections if c.msgtype == "sensor_msgs/msg/PointCloud2"]
        topic = conns[0].topic
        for k, (conn, t, raw) in enumerate(reader.messages(connections=conns)):
            msg = ts.deserialize_cdr(raw, conn.msgtype)
            frame_id = msg.header.frame_id
            st = pointcloud2_to_structured(msg)
            obj_s = split_objects(st)
            frame = frame_from_compact(structured_to_compact(st), cfg.sensor, stamp=t / 1e9, frame_id=frame_id)
            t0 = t / 1e9 if t0 is None else t0
            det.process(frame)
            n_frames += 1
            if not len(obj_s):
                continue
            r2 = (obj_s * obj_s).sum(axis=1)
            obj_s = obj_s[(r2 >= cfg.sensor.min_range ** 2) & (r2 <= cfg.sensor.max_range ** 2)]
            xyz = det.calib.apply(sensor_to_vehicle(obj_s.astype(np.float32), cfg.sensor)).astype(np.float64)
            dy, h = corridor_coordinates(xyz, det.track)
            groups = [(float(xyz[g, 0].min()), g) for g in group_frame(xyz, a.gap)]
            groups_per_frame[k] = groups
            per_frame[k] = (xyz, dy, h)
            if k % 200 == 0:
                print(f"frame {k}: {len(groups)} object(s)", flush=True)

    tracks = [t for t in link_tracks(groups_per_frame) if len(t) >= a.min_track]
    tracks.sort(key=lambda t: t[-1][0])          # the order in which they pass the sensor
    if len(tracks) != len(OBJECTS):
        raise SystemExit(f"found {len(tracks)} object tracks, expected {len(OBJECTS)}: check --gap / the bag")

    half_w = max(abs(float(v[0])) for v in cfg.gauge.profile)
    top = max(float(v[1]) for v in cfg.gauge.profile)
    gt = {}
    summary = {}
    for (label, kind, size, in_gauge, text), track in zip(OBJECTS, tracks):
        frames = []
        for k, gi, _ in track:
            xyz, dy, h = per_frame[k]
            g = groups_per_frame[k][gi][1]
            X, d, hh = xyz[g, 0], dy[g], h[g]
            inside = (np.abs(d) <= half_w) & (hh <= top) & (hh >= -0.6)
            row = {"kind": kind, "name": label, "label": label, "size": size,
                   "distance": round(float(X.min()), 2),
                   "lateral": round(float(0.5 * (d.min() + d.max())), 2),
                   "lateral_sensor": round(float(0.5 * (xyz[g, 1].min() + xyz[g, 1].max())), 2),
                   "yaw_deg": 0.0, "reflectivity": 1.0, "in_gauge": in_gauge,
                   "n_points": int(g.size),
                   "n_in_envelope": int(inside.sum()),
                   "plausible": bool(abs(0.5 * (d.min() + d.max())) < 3.5 and -1.0 < hh.min() < 5.0),
                   "gauge_margin": round(float(half_w - np.abs(d).min()) if (d.min() > 0 or d.max() < 0) else half_w, 2),
                   "h_above_rail": [round(float(hh.min()), 2), round(float(hh.max()), 2)],
                   "bbox": [[round(float(v), 2) for v in xyz[g].min(axis=0)],
                            [round(float(v), 2) for v in xyz[g].max(axis=0)]]}
            if not row["plausible"]:
                row["in_gauge"] = False      # inside the rock: `resense eval` must not count a miss
            gt.setdefault(f"{k:05d}", []).append(row)
            frames.append((k, row))
        near = [r for _, r in frames if r["distance"] < 40.0] or [r for _, r in frames]
        plaus = [r for _, r in frames if r["plausible"]]
        summary[label] = {
            "description": text, "in_gauge": in_gauge, "size_m": size,
            "frames": [frames[0][0], frames[-1][0]], "visible_frames": len(frames),
            "first_visible_m": frames[0][1]["distance"],
            "plausible_frames": len(plaus),
            "first_plausible_m": plaus[0]["distance"] if plaus else None,
            "frames_in_envelope": sum(1 for r in plaus if r["n_in_envelope"] > 0),
            "lateral_near_m": round(float(np.median([r["lateral"] for r in near])), 2),
            "gauge_margin_near_m": round(float(np.median([r["gauge_margin"] for r in near])), 2),
            "h_above_rail_near_m": [round(float(np.median([r["h_above_rail"][0] for r in near])), 2),
                                    round(float(np.median([r["h_above_rail"][1] for r in near])), 2)],
        }
    for k in range(n_frames):
        gt.setdefault(f"{k:05d}", [])
    meta = {
        "bag": os.path.basename(os.path.normpath(a.bag)), "topic": topic, "frame_id": frame_id,
        "source": "scripts/label_fake_objects.py: the organizers' appended object points of every "
                  "message (after the last no-return zero, intensity 1), linked into ten tracks in "
                  "the organizers' order of 24.09",
        "coords": "vehicle (mount-calibrated by the shipped detector)", "every": 1, "frames": n_frames,
        "axis": "per-frame estimate_track axis of the shipped detector; lateral is measured from it, + left",
        "gauge_half_width_m": half_w,
        "keys": {"gauge_margin": "half-width minus the smallest |dy| of the object's points (+ inside); "
                                 "the full half-width when the object straddles the axis",
                 "h_above_rail": "[min, max] height of the object's points above the detector's rail head",
                 "lateral_sensor": "object centre from the sensor's X axis (Y = 0), the frame the organizers "
                                   "placed the objects in; the rails of this recording run at -0.24 deg to it",
                 "in_gauge": "the organizers' intent (inside / outside the envelope), not the measurement; "
                             "false on rows that are not plausible, so that `resense eval` does not count them as misses",
                 "n_in_envelope": "object points inside the strict envelope in the track frame (|dy| <= half-width, "
                                  "-0.6 m <= h <= top)",
                 "plausible": "the object lies in the tunnel cross-section (|lateral| < 3.5 m, -1 m < lowest "
                              "point < 5 m above the rail head); far away the organizers' path leaves the tunnel "
                              "and some single points lie tens of metres inside the rock"},
        "objects": summary,
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:      # one frame per line keeps the diff readable
        fh.write('{\n "_meta": ' + json.dumps(meta, ensure_ascii=False, indent=1).replace("\n", "\n ") + ",\n")
        fh.write(",\n".join(f' "{k}": {json.dumps(gt[k], ensure_ascii=False, separators=(",", ":"))}'
                             for k in sorted(gt)))
        fh.write("\n}\n")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"wrote {a.out}: {n_frames} frames, {sum(len(v) for v in gt.values())} object rows")


if __name__ == "__main__":
    main()
