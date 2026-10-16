#!/usr/bin/env python3
"""Build real local wheels and verify the backend in a fresh, non-editable venv.

Needs pip, setuptools and wheel in the builder; dependency downloads need the
internet (or a configured pip cache/index). Build copies keep source trees clean.
The verification interpreter runs outside the checkout with -I and no ROS.
"""
from __future__ import annotations

import argparse
from email.parser import Parser
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import venv
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SMOKE = r'''
import importlib.abc
import importlib.metadata as metadata
import importlib.util
import json
from pathlib import Path
import sys

assert importlib.util.find_spec("ros2_ws") is None, sys.path
for name in ("rclpy", "launch", "launch_ros"):
    assert importlib.util.find_spec(name) is None, name

class NoNodeOrROS(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in ("rclpy", "launch", "launch_ros") or fullname == "resense_ros.detector_node":
            raise ModuleNotFoundError("ROS/node import forbidden by wheel check", name=fullname)

sys.meta_path.insert(0, NoNodeOrROS())
import resense
import resense_ros.decision_policy as policy
import resense_web.decision as backend
from resense_web.app import create_app
assert create_app().title
assert backend.decision_of is policy.decision
assert backend.decision_of({"obstacle": True, "health": {"level": "error"}}) == "STOP"
assert backend.decision_of({"warning": True}) == "CAUTION"
assert backend.decision_of({"health": {"level": "warn", "decision_level": "ok"}}) == "GO"
assert backend.decision_of({"health": {"level": "error"}}) == "FAULT"
assert policy.decision({"warning": True, "warnings": [{"reason": "column"}]}, "v2") == "GO"
assert "resense_ros.detector_node" not in sys.modules
assert not any(name.split(".")[0] in ("rclpy", "launch", "launch_ros") for name in sys.modules)
origins = {name: str(Path(module.__file__).resolve()) for name, module in
           (("resense", resense), ("resense_ros.decision_policy", policy), ("resense_web.decision", backend))}
assert all(Path(path).is_relative_to(Path(sys.prefix)) for path in origins.values()), origins
print(json.dumps({"python": sys.version, "origins": origins, "ros_available": False,
                  "versions": {name: metadata.version(name) for name in ("resense", "resense-ros", "resense-web")}}))
'''


def run(args, cwd, env):
    subprocess.run([str(arg) for arg in args], cwd=cwd, env=env, check=True)


def verify(root, work):
    env = {key: value for key, value in os.environ.items() if key not in ("PYTHONPATH", "PYTHONHOME")}
    env.update(OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", NUMEXPR_NUM_THREADS="1")
    ignore = shutil.ignore_patterns("__pycache__", "*.egg-info", "build", "dist", "*.so", "*.pyd")
    detector = work / "detector"
    detector.mkdir()
    for name in ("pyproject.toml", "setup.py", "README.md"):
        shutil.copyfile(root / name, detector / name)
    for name in ("resense", "native"):
        shutil.copytree(root / name, detector / name, ignore=ignore)
    ros = work / "ros-package"
    shutil.copytree(root / "ros2_ws/src/resense_ros", ros, ignore=ignore)
    backend = work / "backend"
    shutil.copytree(root / "webapp/backend", backend, ignore=ignore)
    wheels = work / "wheels"
    wheels.mkdir()
    run([sys.executable, "-m", "pip", "wheel", "--quiet", "--no-deps", "--no-build-isolation",
         "--wheel-dir", wheels, detector, ros, backend], work, env)
    backend_wheel = next(wheels.glob("resense_web-*.whl"))
    detector_wheel = next(wheels.glob("resense-*.whl"))
    with zipfile.ZipFile(backend_wheel) as wheel:
        meta = Parser().parsestr(wheel.read(next(name for name in wheel.namelist() if name.endswith("/METADATA"))).decode())
    requirements = meta.get_all("Requires-Dist", [])
    assert any(re.match(r"resense[-_]ros\b", requirement, re.I) for requirement in requirements), requirements
    target = work / "venv"
    venv.EnvBuilder(with_pip=True).create(target)
    python = target / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    # Do not supply the ROS wheel explicitly: the backend dependency must resolve it.
    run([python, "-m", "pip", "install", "--quiet", "--only-binary=:all:",
         "--find-links", wheels, detector_wheel, backend_wheel], work, env)
    run([python, "-m", "pip", "check"], work, env)
    env.update(RESENSE_WEB_DATA=str(work / "web-data"), RESENSE_DATA=str(work))
    result = subprocess.run([str(python), "-I", "-c", SMOKE], cwd=work, env=env,
                            check=True, capture_output=True, text=True)
    run([python, "-I", "-m", "resense_web", "--help"], work, env)
    return {"schema": "resense.webapp_wheel_check.v1", "status": "pass",
            "backend_requirements": requirements, "isolated_import": json.loads(result.stdout),
            "wheels": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(wheels.glob("*.whl"))}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="optional JSON evidence (the parent directory must exist)")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="resense-web-wheels-") as directory:
        result = verify(ROOT, Path(directory))
    text = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
