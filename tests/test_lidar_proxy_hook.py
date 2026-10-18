"""The external N2 stress hook is explicit, inherited and cannot fake a clean gate."""

import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

from resense.detector import Detector
from resense.frame import Frame

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "docs/evidence/n2_falcon_2026-10-18/proxy_hook"


def environment(directory):
    env = dict(os.environ)
    env.update(PYTHONPATH=str(HOOK), RESENSE_N2_PROXY="1", RESENSE_N2_SOURCE=str(ROOT),
               RESENSE_N2_HELPER=str(ROOT / "scripts/lidar_input_variants.py"),
               RESENSE_N2_PROXY_RECEIPTS=str(directory),
               OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    return env


def test_hook_receives_injected_points_and_drops_ring_without_changing_input(tmp_path, monkeypatch):
    for key, value in environment(tmp_path).items():
        if key.startswith("RESENSE_N2_"):
            monkeypatch.setenv(key, value)
    monkeypatch.setattr(sys, "path", list(sys.path))
    seen = []
    monkeypatch.setattr(Detector, "process", lambda self, frame: seen.append(frame) or frame)
    spec = importlib.util.spec_from_file_location("test_proxy_hook", HOOK / "proxy_input_hook.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.install()
    # The last point is an injected positive in the same angular cell as the
    # background; it must replace that farther return after injection.
    xyz = np.array([[20., 0, 0], [-10., 0, 0], [10., 0, 0]], np.float32)
    frame = Frame(xyz, np.array([1., 2., 3.], np.float32), np.arange(3, dtype=np.uint16),
                  stamp=12., frame_id="original", meta={"n_raw": 9, "n_near": 2})
    result = Detector.process(None, frame)
    np.testing.assert_array_equal(result.xyz, [[10., 0, 0]])
    assert result.ring is None and result.intensity.tolist() == [3.]
    assert result.meta == frame.meta and result.stamp == frame.stamp
    assert frame.ring is not None and frame.xyz.shape == (3, 3)
    row = json.loads(next(tmp_path.glob("frames_*.jsonl")).read_text())
    assert row["before_points"] == 3 and row["after_points"] == 1
    assert row["__source_frame_index"] == 0 and not row["output_has_ring"]


def test_child_process_inherits_hook_and_bad_source_fails_closed(tmp_path):
    env = environment(tmp_path / "valid")
    code = (
        "from resense.detector import Detector; from resense.config import DetectorConfig; "
        "from resense.frame import Frame; import numpy as np; "
        "assert Detector.process.n2_transformed_input; "
        "Detector(DetectorConfig()).process(Frame(np.zeros((0,3),np.float32),np.zeros(0,np.float32)))"
    )
    result = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert len(list((tmp_path / "valid").glob("activated_*.json"))) == 1
    assert len(list((tmp_path / "valid").glob("frames_*.jsonl"))) == 1
    env["RESENSE_N2_SOURCE"] = str(tmp_path / "missing-source")
    result = subprocess.run([sys.executable, "-c", "raise SystemExit(0)"], env=env,
                            capture_output=True, text=True)
    assert result.returncode == 86 and "outside the pinned source" in result.stderr
