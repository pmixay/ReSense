"""Fail immediately on an installed/cross-checkout core or absent native/Open3D."""
import hashlib
import importlib
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy
import open3d
import resense
from resense import _native

root = Path("/work/target")
assert Path(resense.__file__).resolve() == root / "resense/__init__.py", resense.__file__
assert _native.enabled(), _native.status()
modules = {}
for name in ("config", "detector", "track", "tracking", "health", "clustering", "sensor", "_native"):
    mod = importlib.import_module("resense." + name)
    assert Path(mod.__file__).resolve().is_relative_to(root)
    modules[mod.__name__] = {"path": mod.__file__,
                            "sha256": hashlib.sha256(Path(mod.__file__).read_bytes()).hexdigest()}
binaries = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*.so")}
assert binaries
print(json.dumps({"python": sys.version, "executable": sys.executable,
                  "platform": platform.platform(), "numpy": numpy.__version__,
                  "open3d": open3d.__version__, "open3d_path": open3d.__file__,
                  "native": _native.status(), "binaries": binaries,
                  "modules": modules, "sys_path": sys.path,
                  "compiler": subprocess.check_output(["g++", "--version"], text=True)}, indent=2))
