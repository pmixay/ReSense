#!/usr/bin/env python3
"""Two same-topic/frame/stamp bags with different explicit sensor coordinates."""

import argparse
import json
from pathlib import Path
import sys

import numpy as np
from rosbags.typesys import Stores, get_typestore

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts import make_smoke_bag as smoke  # noqa: E402
from resense.config import SensorConfig  # noqa: E402
from resense.frame import axis_matrix  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    ts = get_typestore(Stores.ROS2_HUMBLE)
    frames = list(smoke.build_frames(15, 25, 40.0, 100))
    rotation = axis_matrix(SensorConfig()).astype(np.float32)
    smoke.FRAME_ID = "same_lidar"
    manifest = {}
    for profile in ("pandar128", "falcon_ros"):

        def messages():
            for index, (xyz, intensity, ring) in enumerate(frames):
                points = xyz if profile == "pandar128" else xyz @ rotation.T
                msg = smoke.make_message(
                    ts,
                    points,
                    intensity,
                    ring,
                    100_000_000_000 + index * 100_000_000,
                    100.0 + index * 0.1,
                    np.random.default_rng(100 + index),
                )
                if profile == "falcon_ros":
                    parsed = ts.deserialize_cdr(msg, smoke.MSGTYPE)
                    parsed.fields = [
                        field for field in parsed.fields if field.name != "ring"
                    ]
                    msg = ts.serialize_cdr(parsed, smoke.MSGTYPE)
                yield msg

        path = args.out / profile
        manifest[profile] = smoke.write_bag(
            str(path), messages(), 1_700_000_000_000_000_000, 100_000_000
        )
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(
        f"{args.out}: 40 frames each, identical topic/frame/stamps, person40m; Pandar→Falcon axes/ring differ"
    )


if __name__ == "__main__":
    main()
