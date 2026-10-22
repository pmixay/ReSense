"""Smoke tests for the scripts that nothing else referred to (docs/evidence/hygiene_2026-10-22).

``scripts/README.md`` indexes them. Here: every one of them starts (``--help`` prints a usage
line, run from outside the repository as ``docs/EXPERIMENT_*`` run them), the index names each,
and the reusable tools that take small inputs are run on one: ``cache_to_bag.py`` (round trip of a
tiny cache through a ROS 2 bag, plain and zstandard cache) and ``consistency_check.py``.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
INDEX = SCRIPTS / "README.md"

# The files the sweep of 22.10 found without a reference from a test, CI, Dockerfile, script or live doc.
UNREFERENCED = [
    "bench_health_histogram.py", "cache_to_bag.py", "check_synth_labels.py", "compare_history_stress.py",
    "consistency_check.py", "dust_battery.py", "lying_person_eval.py", "ml_second_opinion.py",
    "mount_survey.py", "orientation_battery.py", "p2_draft_deck.py", "p4_data_intake.py",
    "p4_linux_intake.py", "render_false_targets.py", "robustness_check.py", "run_offline.sh",
    "speed_setf.py", "speed_static_check.py", "speed_timing.py", "start_offsets.py", "startup_census.py",
    "summarize_oracle_accumulation.py", "summarize_synthetic_sensitivity.py", "track_opinion_pipeline.py",
]
PYTHON_TOOLS = [n for n in UNREFERENCED if n.endswith(".py")]


def _clean_env():
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    return env


def _run(args, cwd, timeout=120):
    return subprocess.run([sys.executable, *map(str, args)], cwd=cwd, env=_clean_env(),
                          capture_output=True, text=True, timeout=timeout)


def _usage_ok(script: Path, cwd) -> bool:
    r = _run([script, "--help"], cwd)
    return r.returncode == 0 and r.stdout.lstrip().startswith("usage:")


def test_the_index_names_every_unreferenced_script_and_each_exists():
    text = INDEX.read_text(encoding="utf-8")
    for name in UNREFERENCED:
        assert (SCRIPTS / name).is_file(), name
        assert f"`{name}`" in text, f"scripts/README.md does not index {name}"


@pytest.mark.parametrize("name", PYTHON_TOOLS)
def test_script_starts_and_prints_usage_outside_the_repository(name, tmp_path):
    if name == "p2_draft_deck.py":
        pytest.importorskip("pptx", reason="p2_draft_deck.py builds a .pptx (the 'presentation' extra)")
    r = _run([SCRIPTS / name, "--help"], tmp_path)
    assert r.returncode == 0, r.stderr[-800:]
    assert r.stdout.lstrip().startswith("usage:"), r.stdout[:200]


def test_the_usage_check_fails_on_a_broken_script_and_on_a_script_that_does_not_stop(tmp_path):
    """Positive control of the check above: it must be able to say no."""
    broken = tmp_path / "broken.py"
    broken.write_text("import module_that_does_not_exist\n", encoding="utf-8")
    assert not _usage_ok(broken, tmp_path)
    silent = tmp_path / "silent.py"
    silent.write_text("print('ran without argparse')\n", encoding="utf-8")
    assert not _usage_ok(silent, tmp_path)
    good = tmp_path / "good.py"
    good.write_text("import argparse\nargparse.ArgumentParser().parse_args()\n", encoding="utf-8")
    assert _usage_ok(good, tmp_path)


def test_run_offline_passes_its_arguments_to_the_cli(tmp_path):
    fake = tmp_path / "bin"
    fake.mkdir()
    log = tmp_path / "args.txt"
    (fake / "resense").write_text(f'#!/bin/sh\necho "$@" > {log}\n', encoding="utf-8")
    (fake / "resense").chmod(0o755)
    env = _clean_env()
    env["PATH"] = f"{fake}{os.pathsep}{env['PATH']}"
    r = subprocess.run(["bash", str(SCRIPTS / "run_offline.sh"), "/bags/x", str(tmp_path / "o.jsonl"), "/r"],
                       env=env, capture_output=True, text=True, timeout=20)
    assert r.returncode == 0, r.stderr
    assert log.read_text().split() == ["run", "--bag", "/bags/x", "--out", str(tmp_path / "o.jsonl"), "--render", "/r"]


# --- cache_to_bag.py: a tiny cache through a bag and back ------------------------------------------------

N_FRAMES, N_POINTS = 3, 40


def _write_cache(directory: Path, zstd: bool):
    from resense.pointcloud import COMPACT16_DTYPE
    directory.mkdir(parents=True)
    rng = np.random.default_rng(5)
    stamps, expected = {}, []
    for k in range(N_FRAMES):
        arr = np.zeros(N_POINTS, COMPACT16_DTYPE)
        arr["x"] = rng.integers(500, 9000, N_POINTS)
        arr["y"] = rng.integers(-300, 300, N_POINTS)
        arr["z"] = rng.integers(-150, 150, N_POINTS)
        arr["intensity"] = rng.integers(1, 255, N_POINTS)
        arr["ring"] = rng.integers(0, 120, N_POINTS)
        expected.append(arr)
        stem = directory / f"demo_{k:04d}"
        if zstd:
            import io
            import zstandard
            buf = io.BytesIO()
            np.save(buf, arr)
            Path(str(stem) + ".npy.zst").write_bytes(zstandard.ZstdCompressor().compress(buf.getvalue()))
        else:
            np.save(str(stem) + ".npy", arr)
        stamps[f"{k:04d}"] = 100.0 + 0.1 * k
    (directory / "demo_stamps.json").write_text(
        json.dumps({"bag": "demo", "frame_id": "hesai_lidar", "frames": N_FRAMES, "stamps": stamps}), encoding="utf-8")
    return expected


@pytest.mark.parametrize("zstd", [False, True], ids=["npy", "npy.zst"])
def test_cache_to_bag_round_trips_a_tiny_cache(zstd, tmp_path):
    pytest.importorskip("rosbags")
    if zstd:
        pytest.importorskip("zstandard")
    from rosbags.rosbag2 import Reader
    from rosbags.typesys import Stores, get_typestore
    expected = _write_cache(tmp_path / "cache", zstd)
    out = tmp_path / "bag"
    r = _run([SCRIPTS / "cache_to_bag.py", tmp_path / "cache", out, "--topic", "/lidar"], tmp_path)
    assert r.returncode == 0, r.stderr[-800:]
    assert f"{N_FRAMES} frames of demo" in r.stdout
    ts = get_typestore(Stores.ROS2_HUMBLE)
    with Reader(out) as reader:
        messages = list(reader.messages())
        assert [c.topic for c in reader.connections] == ["/lidar"]
    assert [m[1] for m in messages] == [round((100.0 + 0.1 * k) * 1e9) for k in range(N_FRAMES)]
    for (_, _, raw), arr in zip(messages, expected):
        msg = ts.deserialize_cdr(raw, "sensor_msgs/msg/PointCloud2")
        assert msg.header.frame_id == "hesai_lidar" and msg.point_step == 26
        pts = np.frombuffer(bytes(msg.data), dtype=np.dtype({
            "names": ["x", "y", "z", "intensity", "ring", "timestamp"],
            "formats": ["<f4", "<f4", "<f4", "<f4", "<u2", "<f8"], "offsets": [0, 4, 8, 12, 16, 18], "itemsize": 26}))
        assert pts.size == N_POINTS + N_POINTS // 10                     # the empty dual-return slots
        filled = ~((pts["x"] == 0) & (pts["y"] == 0) & (pts["z"] == 0))
        assert int(filled.sum()) == N_POINTS
        np.testing.assert_allclose(pts["x"][filled], arr["x"] * 0.01, atol=1e-5)
        np.testing.assert_allclose(pts["z"][filled], arr["z"] * 0.01, atol=1e-5)
        np.testing.assert_array_equal(pts["intensity"][filled], arr["intensity"])
        np.testing.assert_array_equal(pts["ring"][filled], arr["ring"] & 0x7F)


# --- consistency_check.py ------------------------------------------------------------------------------------

def _run_dir(directory: Path, ids_by_subset: dict):
    directory.mkdir()
    names = ["doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
             "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch", "doubleT_obstacle",
             "new_data_1", "new_data_2"]
    for name in names:
        rows = []
        for frame in range(4):
            ids = ids_by_subset.get(name, []) if frame in (1, 2) else []
            rows.append({"frame": frame, "obstacle": bool(ids),
                         "detections": [{"id": i, "distance": 20.0, "lateral": 0.0} for i in ids]})
        (directory / f"{name}.jsonl").write_text("\n".join(map(json.dumps, rows)) + "\n", encoding="utf-8")


def test_consistency_check_counts_alarm_events_per_subset(tmp_path):
    _run_dir(tmp_path / "base", {"roundT_doubleT": [7], "new_data_1": [3, 4], "doubleT_platform": [9]})
    _run_dir(tmp_path / "cand", {"roundT_doubleT": [], "new_data_1": [3], "doubleT_platform": [9]})
    out = tmp_path / "c.json"
    r = _run([SCRIPTS / "consistency_check.py", tmp_path / "base", tmp_path / "cand", "--json", out], tmp_path)
    assert r.returncode == 0, r.stderr[-800:]
    rows = {row["subset"]: row for row in json.loads(out.read_text())["rows"]}
    assert (rows["roundT_doubleT"]["events_base"], rows["roundT_doubleT"]["events_cand"]) == (1, 0)
    assert (rows["ride part 1"]["events_base"], rows["ride part 1"]["events_cand"]) == (2, 1)
    assert (rows["doubleT_platform"]["events_base"], rows["doubleT_platform"]["events_cand"]) == (1, 1)
    assert rows["ride part 1"]["alarm_frames_base"] == 2                   # frames 1 and 2 carry the alarm
    assert "subsets with fewer events: 2, more: 0" in r.stdout
