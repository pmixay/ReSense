#!/usr/bin/env python3
"""Wrapper around the repo's scripts/stream_falcon.py (unchanged): one pass over the Falcon recording,
two detectors fed from it.

  primary   = NodeReplica() as the repo's own B2 run (default launch: Pandar axes -y/+x/+z + auto_calibrate)
  secondary = NodeReplica(overrides = falcon_ros profile axes +x/+y/+z), written to <out>_ros.jsonl

Extras (do not touch detector state): per-frame uncropped range histograms of the raw returns (10 m bins to
600 m), the full mount dict, and a few raw frames dumped as npz for independent geometry checks.

Usage: same CLI as stream_falcon.py (src, --out, --limit ...) plus env FALCON_DUMP=comma list of frame numbers.
"""
import json
import os
import sys

REPO = os.environ["RESENSE_REPO"]
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, os.path.join(REPO, "ros2_ws/src/resense_ros"))

import numpy as np  # noqa: E402

import stream_falcon  # noqa: E402  (inserts the judge scripts path)
import judge_runner  # noqa: E402
from resense_ros import fastcloud  # noqa: E402

DUMP = {int(v) for v in os.environ.get("FALCON_DUMP", "").split(",") if v}
OUT = None
BINS = np.arange(0, 610, 10.0)


_Orig = judge_runner.NodeReplica


class DualReplica(_Orig):
    def __init__(self):
        super().__init__()
        self.second = _Orig(overrides={"sensor.forward": "+x", "sensor.left": "+y", "sensor.up": "+z"})
        self.f2 = open(OUT + "_ros.jsonl", "w")
        self.fx = open(OUT + "_extra.jsonl", "w")

    def process_raw(self, raw, topic, idx, transform=None):
        out = super().process_raw(raw, topic, idx, transform)
        msg, stamp, res, dec_ms, det_ms = out
        # extras on the primary
        extra = {"i": idx, "mount_full": res.mount, "axis_valid": getattr(res.track, "axis_valid", None)}
        m2 = self.second.process_raw(raw, topic, idx, transform)
        r2 = judge_runner.record(idx, m2[1], m2[1], m2[2], m2[3], m2[4], m2[0].header.frame_id, topic)
        r2["mount_full"] = m2[2].mount
        r2["axis_valid"] = getattr(m2[2].track, "axis_valid", None)
        self.f2.write(json.dumps(r2, default=float) + "\n")
        # uncropped raw range stats (sensor frame = ROS FLU for this recording)
        xyz, inten, _, n_raw, _ = fastcloud.decode(fastcloud.packed(msg), 0.0, 700.0)
        rr = np.linalg.norm(xyz, axis=1)
        h, _ = np.histogram(rr, bins=BINS)
        extra["range_hist10"] = h.tolist()
        extra["n_raw"] = int(n_raw)
        extra["n_gt250"] = int((rr > 250).sum())
        extra["n_gt300"] = int((rr > 300).sum())
        extra["rmax"] = float(rr.max()) if len(rr) else None
        self.fx.write(json.dumps(extra, default=float) + "\n")
        if idx in DUMP:
            np.savez_compressed(f"{OUT}_f{idx:05d}.npz", xyz=xyz.astype(np.float32), inten=inten.astype(np.uint8),
                                mount=np.asarray(self.detector.mount_rotation), R_vs=self.R_vs)
        return out


judge_runner.NodeReplica = DualReplica

if __name__ == "__main__":
    i = sys.argv.index("--out")
    OUT = sys.argv[i + 1]
    raise SystemExit(stream_falcon.main())
