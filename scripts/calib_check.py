#!/usr/bin/env python3
"""Mount auto-calibration on real frames (EXPERIMENTS.md section 6).

A run of cached frames is re-mounted by known rotations (the cloud rotated as a sensor mounted
that way would see it) and a fresh detector runs over it. The residual is the angle between the
correction found for the re-mounted cloud and the one found on the recording as it is - the
rigs are tilted themselves, which is not an error - split into tilt (roll + pitch) and yaw
(below ``calibration.min_yaw_deg`` the yaw is left to the per-frame track model by design).

    python scripts/calib_check.py --npy /data/cache/roundT_doubleT --start 100 --limit 25
"""
from __future__ import annotations

import argparse
import glob
import os
import time

import numpy as np


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--npy", required=True, help="directory of cached frames (scripts/cache_frames.py)")
    ap.add_argument("--start", type=int, default=100)
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--config", default="configs/default.yaml")
    a = ap.parse_args()
    from resense.calibration import rot_x, rot_y, rot_z
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import Frame
    from resense.io import _natural_key, load_npy_frame
    files = sorted(glob.glob(os.path.join(a.npy, "*.npy")), key=_natural_key)[a.start:a.start + a.limit]
    cfg = DetectorConfig.from_yaml(a.config)
    frames = [load_npy_frame(f, cfg.sensor) for f in files]
    cases = {
        "as recorded": np.eye(3),
        "roll +3": rot_x(np.radians(3)),
        "pitch -4": rot_y(np.radians(-4)),
        "roll -2 pitch 3 yaw 2": rot_z(np.radians(2)) @ rot_y(np.radians(3)) @ rot_x(np.radians(-2)),
        "upside down": rot_x(np.pi),
        "forward = +x (90 deg)": rot_z(np.pi / 2),
        "backwards": rot_z(np.pi),
        "on its side (spin axis horizontal)": rot_x(np.pi / 2),
    }
    R0 = None
    for name, M in cases.items():
        det = Detector(cfg)
        t = time.perf_counter()
        res = None
        for fr in frames:
            res = det.process(Frame(xyz=(fr.xyz @ M.T).astype(np.float32), intensity=fr.intensity, ring=fr.ring,
                                    stamp=fr.stamp, meta=fr.meta))
        if R0 is None:
            R0 = det.mount_rotation.copy()           # the rig's own correction
        err = det.mount_rotation @ M @ R0.T          # identity when the re-mounted cloud gets the same correction
        ang = np.degrees(np.arccos(np.clip((np.trace(err) - 1) / 2, -1, 1)))
        tilt = np.degrees(np.arccos(np.clip((err @ np.array([0, 0, 1.0]))[2], -1, 1)))
        fwd = err @ np.array([1.0, 0, 0])
        yaw = np.degrees(np.arctan2(fwd[1], fwd[0]))
        m = res.mount
        print(f"{name:36s} {m['status']:9s} residual {ang:5.2f} deg (tilt {tilt:4.2f}, yaw {yaw:+5.2f})  "
              f"roll {m['roll_deg']:+.2f} pitch {m['pitch_deg']:+.2f} yaw {m['yaw_deg']:+.2f}  orientation: {m['orientation']}  "
              f"| obstacle {res.obstacle}  {time.perf_counter() - t:.1f} s")


if __name__ == "__main__":
    main()
