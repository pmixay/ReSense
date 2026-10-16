"""Load an observer checkout's pure policy, independently of detector / ROS overlays.

This is an import helper, not another implementation of the decision rule. Never
replace resense_ros modules: an already imported node must keep its class identity.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.util
from pathlib import Path
import sys


def load_policy(root):
    path = (Path(root) / "ros2_ws/src/resense_ros/resense_ros/decision_policy.py").resolve()
    if not path.is_file():
        # Installed-only consumers require the declared resense-ros distribution.
        return importlib.import_module("resense_ros.decision_policy")
    for name in ("resense_ros.decision_policy", "ros2_ws.src.resense_ros.resense_ros.decision_policy"):
        module = sys.modules.get(name)
        filename = getattr(module, "__file__", None)
        if filename and Path(filename).resolve() == path:
            return module
        if module is None:
            try:
                spec = importlib.util.find_spec(name)
            except (ModuleNotFoundError, ValueError):
                continue
            if spec is not None and spec.origin and Path(spec.origin).resolve() == path:
                # Use the normal module identity when it resolves to this exact
                # file; never execute an older overlay / detector copy instead.
                return importlib.import_module(name)
    name = "_resense_source_policy_" + hashlib.sha256(str(path).encode()).hexdigest()
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module  # dataclasses resolve annotations through sys.modules
        try:
            spec.loader.exec_module(module)
        except BaseException:
            del sys.modules[name]
            raise
    return sys.modules[name]
