#!/usr/bin/env python3
"""Read the final measured checkout's four version declarations and shipping config."""
import ast
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

import yaml

COMMIT = "52115654417a660669b8dddfce447692c1d782cc"
RUN = "candidate-52115654417a-20261016T110150Z-d9084fe4"
REPO = Path("/evalworkspace") / RUN
sys.path[:0] = [str(REPO), str(REPO / "scripts")]
import resense
from resense import _native
from resense.config import DetectorConfig

head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
assert head == COMMIT
pyproject = (REPO / "pyproject.toml").read_text()
project_version = re.search(r'^version = "([^"]+)"$', pyproject, re.M).group(1)
setup = ast.parse((REPO / "ros2_ws/src/resense_ros/setup.py").read_text())
setup_versions = [kw.value.value for node in ast.walk(setup) if isinstance(node, ast.Call)
                  for kw in node.keywords if kw.arg == "version" and isinstance(kw.value, ast.Constant)]
assert len(setup_versions) == 1
versions = {"resense/__init__.py": resense.__version__, "pyproject.toml": project_version,
            "ros2_ws/src/resense_ros/setup.py": setup_versions[0],
            "ros2_ws/src/resense_ros/package.xml": ET.parse(REPO / "ros2_ws/src/resense_ros/package.xml").getroot().findtext("version")}
canonical = REPO / "configs/default.yaml"
ros = REPO / "ros2_ws/src/resense_ros/config/detector.yaml"
config = yaml.safe_load(canonical.read_text())["resense"]
measured = yaml.safe_load((Path("/evidence") / RUN / "gate_work/config.yaml").read_text())["resense"]
routes = dict(class_default=DetectorConfig().cluster.column_free_max_top,
              canonical_yaml=config["cluster"]["column_free_max_top"],
              ros_yaml=yaml.safe_load(ros.read_text())["resense"]["cluster"]["column_free_max_top"],
              measured_yaml=measured["cluster"]["column_free_max_top"],
              resolved_measured=DetectorConfig.from_dict(measured).cluster.column_free_max_top)
assert all(value == "1.1.0" for value in versions.values())
assert all(value == 0.0 for value in routes.values())
assert canonical.read_bytes() == ros.read_bytes() and _native.enabled()
print(json.dumps(dict(measured_commit=head, versions=versions, all_versions_1_1_0=True,
    resense_file=resense.__file__, column_free_max_top_routes=routes,
    config_sync=True, canonical_config_sha256=hashlib.sha256(canonical.read_bytes()).hexdigest(),
    native_enabled=_native.enabled(), native_status=_native.status()), indent=2))
