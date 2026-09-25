#!/usr/bin/env python3
"""Replay the frames a ROS run processed through the node's detector path, offline.

A ``/resense/status`` capture (``scripts/dry_run.sh``: ``status.jsonl``, or the ``.gz`` of the
evidence) holds the header stamp of every frame the node processed; the catch-up at the start
skips some. This script feeds the same frames with the same stamps to a fresh ``Detector`` (the
node's parameter file, ``auto_calibrate`` on, no ego speed) and prints its alarm frames next to
the node's:

    python scripts/replay_node_frames.py <status.jsonl[.gz]> --bag <bags>/roundT_doubleT
    python scripts/replay_node_frames.py <status> --cache /data/cache/roundT_doubleT [--dither-mm 5 --seeds 0-9]
    python scripts/replay_node_frames.py <status> --cache ... --every-frame --set tracking.column_hold=0

``--bag`` (the original recording): frames matched by header stamp, decoded as the node does
(``pointcloud2_to_arrays``) - the node's input exactly. ``--cache`` (``scripts/cache_frames.py
--int16 --stamps``): the cache keeps only receive times, so the header clock is fitted as
``h0 + period * index`` on the frames whose point count matches the node's ``n_points`` exactly;
the coordinates carry the cache's 1 cm step, and ``--dither-mm`` adds uniform noise of that size
to see how much an alarm depends on it (EXPERIMENTS.md section 3a). ``--every-frame``: every
frame of the recording on the header clock instead of the node's sequence.
"""
from __future__ import annotations

import argparse
import glob
import os
import sys

import numpy as np
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, HERE)

from check_dry_run import load as load_status  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.detector import Detector  # noqa: E402
from resense.frame import Frame, axis_matrix, frame_from_compact  # noqa: E402
from resense.io import npy_frame_index  # noqa: E402
from resense.pointcloud import COMPACT_DTYPE, compact_to_xyz, expand_compact16, pointcloud2_to_arrays  # noqa: E402


def node_config(path, sets) -> DetectorConfig:
    raw = yaml.safe_load(open(path, encoding="utf-8")) or {}
    d = raw.get("resense", raw)
    for s in sets:
        key, val = s.split("=", 1)
        sec, k = key.split(".", 1)
        d.setdefault(sec, {})[k] = yaml.safe_load(val)
    cfg = DetectorConfig.from_dict(d)
    cfg.calibration.enabled = True                      # the node's auto_calibrate default
    return cfg


def fit_header_clock(stamps, n_points, cache_n, period=0.1):
    """(h0, period): header stamp = h0 + period * cache index, fitted on the processed frames
    whose point count matches exactly one cache frame (outliers beyond 30 ms dropped)."""
    idx, h = [], []
    for s, n in zip(stamps, n_points):
        m = np.flatnonzero(cache_n == n)
        if m.size == 1:
            idx.append(m[0])
            h.append(s)
    idx, h = np.asarray(idx, float), np.asarray(h, float)
    if idx.size < 3:
        raise SystemExit("replay_node_frames: too few frames match the cache by point count")
    ok = np.abs((h - period * idx) - np.median(h - period * idx)) < 0.03
    A = np.vstack([idx[ok], np.ones(int(ok.sum()))]).T
    (p, h0), *_ = np.linalg.lstsq(A, h[ok] - h[ok][0], rcond=None)
    return h0 + h[ok][0], p


def cache_frames(cache, cfg, seq_stamps, n_points, every, dither_mm, seed):
    files = {npy_frame_index(f): f for f in glob.glob(os.path.join(cache, "*.npy"))}
    order = sorted(files)
    counts = np.array([frame_from_compact(np.load(files[i]), cfg.sensor).n for i in order])
    h0, p = fit_header_clock(seq_stamps, n_points, counts)
    seq = ([(i, h0 + p * i) for i in order] if every
           else [(int(round((s - h0) / p)), s) for s in seq_stamps])
    rng = np.random.default_rng(seed) if dither_mm > 0 else None
    for i, stamp in seq:
        arr = np.load(files[i])
        if rng is not None:
            arr = expand_compact16(arr)
            xyz = compact_to_xyz(arr) + rng.uniform(-dither_mm, dither_mm, (arr.size, 3)).astype(np.float32) * 1e-3
            out = np.zeros(arr.size, dtype=COMPACT_DTYPE)
            out["x"], out["y"], out["z"] = xyz.T
            out["intensity"], out["ring"] = arr["intensity"], arr["ring"]
            arr = out
        yield i, frame_from_compact(arr, cfg.sensor, stamp=stamp)


def bag_frames(bag, cfg, topic, seq_stamps, every):
    from rosbags.rosbag2 import Reader
    from rosbags.typesys import Stores, get_typestore
    ts = get_typestore(Stores.ROS2_HUMBLE)
    R_vs = axis_matrix(cfg.sensor).astype(np.float32)
    want = {round(s, 6) for s in seq_stamps}
    with Reader(bag) as reader:
        conns = [c for c in reader.connections if c.msgtype == "sensor_msgs/msg/PointCloud2"
                 and (topic is None or c.topic == topic)]
        for i, (conn, _, raw) in enumerate(reader.messages(connections=conns)):
            msg = ts.deserialize_cdr(raw, conn.msgtype)
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            if not every and round(stamp, 6) not in want:
                continue
            xyz, inten, ring, n_raw, n_near = pointcloud2_to_arrays(msg, cfg.sensor.min_range, cfg.sensor.max_range)
            yield i, Frame(xyz=xyz @ R_vs.T, intensity=inten, ring=ring, stamp=stamp,
                           frame_id=msg.header.frame_id, meta={"n_raw": n_raw, "n_near": n_near})


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("status", help="the node's /resense/status capture (status.jsonl or .jsonl.gz)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--bag", help="the original recording (float coordinates, frames matched by header stamp)")
    src.add_argument("--cache", help="its frame cache (int16, header clock fitted)")
    ap.add_argument("--recording", type=int, default=1, help="which recording of the capture (node.recording)")
    ap.add_argument("--config", default=os.path.join(os.path.dirname(HERE), "configs", "default.yaml"))
    ap.add_argument("--set", action="append", default=[], help="section.key=value override (YAML value)")
    ap.add_argument("--every-frame", action="store_true", help="every frame of the recording, not the node's")
    ap.add_argument("--dither-mm", type=float, default=0.0, help="--cache: uniform noise on the coordinates")
    ap.add_argument("--seeds", default="0", help="--dither-mm: seeds, e.g. 0-9 or 1,3")
    a = ap.parse_args(argv)
    node = [f for f in load_status(a.status)[0] if f["node"].get("recording") == a.recording]
    if not node:
        raise SystemExit(f"replay_node_frames: no frame of recording {a.recording} in {a.status}")
    stamps = [f["stamp"] for f in node]
    print(f"node: {len(node)} frames, alarm frames {len([f for f in node if f['obstacle']])}: "
          + ", ".join(f"+{f['stamp'] - stamps[0]:.1f} s {f['nearest_distance']} m" for f in node if f["obstacle"]))
    lo, _, hi = a.seeds.partition("-")
    seeds = list(range(int(lo), int(hi) + 1)) if hi else [int(s) for s in a.seeds.split(",")]
    for seed in (seeds if a.cache and a.dither_mm > 0 else [None]):
        cfg = node_config(a.config, a.set)
        det = Detector(cfg)
        frames = (cache_frames(a.cache, cfg, stamps, [f["n_points"] for f in node], a.every_frame, a.dither_mm, seed)
                  if a.cache else bag_frames(a.bag, cfg, node[0]["node"].get("input_topic"), stamps, a.every_frame))
        rows = [(i, det.process(fr, ego_speed=None).to_dict()) for i, fr in frames]
        al = [(i, r["nearest_distance"]) for i, r in rows if r["obstacle"]]
        tag = "" if seed is None else f" seed {seed}"
        print(f"replay{tag}: {len(rows)} frames, alarm frames {len(al)}: "
              + ", ".join(f"#{i} {d} m" for i, d in al), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
