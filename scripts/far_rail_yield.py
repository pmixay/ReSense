#!/usr/bin/env python3
"""Far rail evidence from single LiDAR ring crossings: how often it exists and where it puts the axis.

    python scripts/far_rail_yield.py --bag /data/for_hackathon/squareT_platform_squareT_switch --every 5
    python scripts/far_rail_yield.py --npy /data/cache/new_data --every 20 --limit 300 --out out/far_rails.json

Our near rail tracker looks at 4-30 m (``track.rails_range``) and needs three returns per 5 cm
profile bin, so it stops at ~30 m. Beyond that a ring crosses each rail head once or twice, but the
two heads of a rail pair still sit one gauge apart on the *same* ring, and pairs found on many
rings must lie on one smooth offset curve that starts at the last near rail. That is the idea of
the ``Tactical-Inventor/LCT-2026.NIIstovye`` repository (``route/_core/far_rails.py``), written here from its description: a vectorised
lateral-cell grid per ring instead of per-ring loops, no numba.

The pairing lives in ``resense/farrails.py``. It is the evidence source our disabled
``track._check_far_rails`` lacks: that check corrects a wall-derived curvature that contradicts the
rails (a station hall's walls look like a gentle curve while the rails stay straight), but its slab
profile never finds a rail pair beyond 30 m (docs/archive/EXPERIMENTS_log_2026-09.md 1f, 1h), so it
never fires. With ``track.rails_far_check_enabled`` and ``track.rails_far_rings`` the detector uses the
ring evidence (opt-in, off by default: configs/experimental_far_rail_rings.yaml).

This script changes no decision; it is the measurement to make before the gate. Per recording it reports

* the frames with a near rail fit (the anchor) and, of those, the frames with at least
  ``--min-stations`` consistent far stations, and how far they reach;
* the far centres against the axis our detector uses (wall curvature included), and the frames in
  which ``_check_far_rails`` would act: both slabs on the same side, further than half a profile
  bin and somewhere more than ``track.rails_yaw_max_dev`` (0.3 m) from our axis.

Run it before the gate (docs/DETECTOR_FREEZE.md): if
the yield is low or the centres disagree with our axis where they should agree, stop there.

Ring identity comes from the elevation angle of a return in the *sensor* frame (the axis-permuted
frame before the mount correction), snapped to the measured ring table: after the mount correction
a tilted mount smears a ring's elevation across its azimuth, and the two heads of one pair (1.6 m
apart, ~2 deg of azimuth at 50 m) would fall in different bins.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from resense.farrails import FarRailParams, far_rails, ring_index, would_correct_axis  # noqa: E402


def measure(frames, cfg, params: FarRailParams) -> dict:
    """Run the detector's calibration and near rail fit on ``frames`` ((index, Frame) pairs) and
    measure the far rail evidence frame by frame."""
    from resense.detector import Detector
    from resense.track import estimate_rails

    det = Detector(cfg)
    n = n_anchor = n_far = n_correct = 0
    reach, n_st, err_all = [], [], []
    for _, frame in frames:
        n += 1
        res = det.process(frame)
        model = res.track
        xyz = det.calib.apply(frame.xyz)
        near = estimate_rails(xyz, model, cfg.track, model.center, prior=model)
        if near.xm is None or near.mids is None or near.n_slabs < 2 or near.score < cfg.track.rails_min_score:
            continue
        n_anchor += 1
        rails = far_rails(xyz, ring_index(frame.xyz, params.ring_tol_deg), model,
                          (float(near.xm[-1]), float(near.mids[-1])), params)
        if rails.n < params.min_stations:
            continue
        n_far += 1
        reach.append(float(rails.x.max()))
        n_st.append(rails.n)
        err = rails.y - model.center_y(rails.x)
        err_all.append(float(np.median(np.abs(err))))
        n_correct += would_correct_axis(rails, model, cfg.track.rails_bin, cfg.track.rails_yaw_max_dev)

    def q(v, pct):
        return round(float(np.percentile(v, pct)), 2) if v else None

    return {"frames": n, "frames_with_near_rails": n_anchor, "frames_with_far_rails": n_far,
            "far_rail_frame_fraction_of_anchored": round(n_far / n_anchor, 3) if n_anchor else None,
            "stations_median": q(n_st, 50), "reach_m_median": q(reach, 50), "reach_m_p90": q(reach, 90),
            "median_abs_axis_error_m_median": q(err_all, 50), "median_abs_axis_error_m_p90": q(err_all, 90),
            "frames_where_check_far_rails_would_act": int(n_correct)}


def iter_cache_frames(directory: str, sensor, every: int = 1, start: int = 0, limit: Optional[int] = None):
    """(index, Frame) of a frame cache, ``*.npy`` and ``*.npy.zst`` alike (scripts/cache_io.py), in
    recording order, with the bag receive stamps when the cache carries them."""
    from resense.frame import frame_from_compact
    from scripts.cache_io import cache_file_stem, cache_files, load_cache_array, load_cache_stamps
    files = cache_files(directory)
    stamps = load_cache_stamps(directory)
    n_out = 0
    for i, f in enumerate(files):
        if i < start or (i - start) % every != 0:
            continue
        stem = cache_file_stem(f)
        yield i, frame_from_compact(load_cache_array(f), sensor, stamp=stamps.get(stem, 0.1 * i),
                                    frame_id=os.path.basename(f))
        n_out += 1
        if limit is not None and n_out >= limit:
            return


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--bag", help="rosbag2 directory")
    src.add_argument("--npy", help="directory of cached *.npy frames (scripts/cache_frames.py)")
    p.add_argument("--topic", default=None)
    p.add_argument("--every", type=int, default=5)
    p.add_argument("--start", type=int, default=0)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--min-stations", type=int, default=FarRailParams.min_stations)
    p.add_argument("--out", default=None, help="write the summary as JSON")
    a = p.parse_args()
    from resense.config import DetectorConfig
    from resense.io import iter_bag_frames
    cfg = DetectorConfig()
    frames = (iter_bag_frames(a.bag, cfg.sensor, topic=a.topic, every=a.every, start=a.start, limit=a.limit)
              if a.bag else iter_cache_frames(a.npy, cfg.sensor, every=a.every, start=a.start, limit=a.limit))
    res = measure(frames, cfg, FarRailParams(min_stations=a.min_stations))
    res["input"] = os.path.abspath(a.bag or a.npy)
    print(json.dumps(res, indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
