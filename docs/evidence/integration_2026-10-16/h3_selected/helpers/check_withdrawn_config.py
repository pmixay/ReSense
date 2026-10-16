#!/usr/bin/env python3
"""Read the actual measured checkout's shipping routes without changing inputs."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import yaml

COMMIT = "c9aea87cb5322092070158cd8987115ee44833c9"
RUN = "candidate-c9aea87cb532-20261016T101302Z-8a9ae4d1"
REPO = Path("/evalworkspace") / RUN
sys.path[:0] = [str(REPO), str(REPO / "scripts")]
import resense
from resense import _native
from resense.config import DetectorConfig


def config(path):
    value = yaml.safe_load(path.read_text())
    return value.get("resense", value)


head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
assert head == COMMIT
canonical = REPO / "configs/default.yaml"
ros = REPO / "ros2_ws/src/resense_ros/config/detector.yaml"
measured = Path("/evidence") / RUN / "gate_work/config.yaml"
routes = {"class_default": DetectorConfig().cluster.column_free_max_top,
          "canonical_yaml": config(canonical)["cluster"]["column_free_max_top"],
          "ros_yaml": config(ros)["cluster"]["column_free_max_top"],
          "measured_gate_yaml": config(measured)["cluster"]["column_free_max_top"],
          "resolved_measured_config": DetectorConfig.from_dict(config(measured)).cluster.column_free_max_top}
values = config(canonical)
report = dict(measured_commit=head, version=resense.__version__, resense_file=resense.__file__,
    column_free_max_top_routes=routes, shipping_H1_disabled=all(v == 0.0 for v in routes.values()),
    canonical_ros_bytes_identical=canonical.read_bytes() == ros.read_bytes(),
    canonical_config_sha256=hashlib.sha256(canonical.read_bytes()).hexdigest(),
    structure_cut={k: v for k, v in values["cluster"].items() if k.startswith("structure_cut_")},
    wall_drift={k: v for k, v in values["track"].items() if k.startswith("axis_wall_drift")},
    inactive_experimental_knobs={k: v for k, v in values["cluster"].items() if k.startswith("column_free_") and k != "column_free_max_top"},
    native_enabled=_native.enabled(), native_status=_native.status())
assert report["shipping_H1_disabled"] and report["canonical_ros_bytes_identical"] and report["native_enabled"]
print(json.dumps(report, indent=2))
