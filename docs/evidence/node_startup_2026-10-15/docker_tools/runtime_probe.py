#!/usr/bin/env python3
"""In-image stdlib provenance / cgroup high-water probe; no Docker socket."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


def memory():
    for name in ("memory.peak", "memory/memory.max_usage_in_bytes"):
        path = Path("/sys/fs/cgroup") / name
        if path.exists():
            return {"bytes": int(path.read_text().strip()), "source": str(path)}
    raise RuntimeError("No cgroup v2 memory.peak or v1 memory.max_usage_in_bytes")


def provenance():
    import resense
    import resense._native as native

    paths = ["ros2_ws/src/resense_ros/resense_ros/detector_node.py",
             "ros2_ws/src/resense_ros/launch/detector.launch.py",
             "ros2_ws/src/resense_ros/resense_ros/decision_policy.py",
             "ros2_ws/src/resense_ros/setup.py"]
    return {
        "python": sys.version, "platform": platform.platform(), "nproc": os.cpu_count(),
        "lscpu": subprocess.check_output(["lscpu"], text=True),
        "meminfo": Path("/proc/meminfo").read_text(),
        "resense_version": resense.__version__, "resense_path": resense.__file__,
        "native": native.status(),
        "source_sha256_lf": {
            p: hashlib.sha256((Path("/opt/resense") / p).read_text().encode()).hexdigest()
            for p in paths
        },
        "thread_env": {k: os.environ.get(k) for k in (
            "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
            "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")},
    }


if __name__ == "__main__":
    print(json.dumps(memory() if sys.argv[1] == "memory" else provenance(), allow_nan=False))
