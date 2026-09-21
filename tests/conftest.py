"""Shared fixtures and the skip guard.

The synthetic ray-cast tunnel (``resense.synthetic``) needs Open3D. Tests that use it carry the
``synthetic`` marker (added automatically to every test that requests the ``tunnel`` or
``synth_npy_dir`` fixture) and are *skipped* on a machine without Open3D, with a reason that
``pytest -rs`` prints. The pure-numpy tests always run.

In CI the environment variable ``RESENSE_REQUIRE_SYNTHETIC=1`` turns every skip into a
failure and makes the session exit non-zero if anything was skipped, so a green run can never
hide an empty suite (docs/CAPTAIN.md section 4 item 2).
"""
from __future__ import annotations

import os

import numpy as np
import pytest

REQUIRE_SYNTHETIC = os.environ.get("RESENSE_REQUIRE_SYNTHETIC", "").strip().lower() not in ("", "0", "false", "no")

_SYNTHETIC_FIXTURES = ("tunnel", "synth_npy_dir")


def open3d_missing_reason():
    """None if Open3D imports, otherwise a one-line reason for the skip."""
    try:
        import open3d  # noqa: F401
    except Exception as e:  # ImportError, or a broken wheel raising OSError
        return f"open3d not importable ({type(e).__name__}: {e})"
    return None


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "synthetic: needs Open3D for the synthetic ray-cast tunnel; skipped without it, "
        "failed when RESENSE_REQUIRE_SYNTHETIC=1",
    )


def pytest_collection_modifyitems(config, items):
    for item in items:
        if any(f in item.fixturenames for f in _SYNTHETIC_FIXTURES):
            item.add_marker(pytest.mark.synthetic)


def pytest_runtest_setup(item):
    if "synthetic" in item.keywords:
        reason = open3d_missing_reason()
        if reason is not None:
            if REQUIRE_SYNTHETIC:
                pytest.fail(f"RESENSE_REQUIRE_SYNTHETIC is set but {reason}", pytrace=False)
            pytest.skip(reason)


_skipped = []


def pytest_runtest_logreport(report):
    if report.skipped:
        _skipped.append(report.nodeid)


def pytest_sessionfinish(session, exitstatus):
    if REQUIRE_SYNTHETIC and _skipped and session.exitstatus == 0:
        session.exitstatus = 1


def pytest_terminal_summary(terminalreporter):
    if REQUIRE_SYNTHETIC and _skipped:
        terminalreporter.write_sep("=", f"RESENSE_REQUIRE_SYNTHETIC=1: {len(_skipped)} skipped test(s) fail the run", red=True)
        for n in _skipped:
            terminalreporter.write_line(f"  skipped: {n}")


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def tunnel():
    """(frame, labels, ground-truth TrackModel) of the clear synthetic tunnel, seed 1."""
    from resense.synthetic import synthetic_tunnel_frame
    frame, labels, gt = synthetic_tunnel_frame(rng=np.random.default_rng(1))
    return frame, labels, gt


@pytest.fixture(scope="session")
def synth_npy_dir(tunnel, tmp_path_factory):
    """Two cached ``*.npy`` frames (sensor frame, compact dtype) of the clear synthetic tunnel,
    named like ``scripts/cache_frames.py`` writes them: ``synthetic_0000.npy``, ``synthetic_0001.npy``."""
    from resense.config import SensorConfig
    from resense.frame import axis_matrix
    from resense.pointcloud import COMPACT_DTYPE
    frame, _, _ = tunnel
    d = tmp_path_factory.mktemp("synth_npy")
    R = axis_matrix(SensorConfig())            # p_vehicle = R @ p_sensor  =>  rows: p_sensor = p_vehicle @ R
    xyz_s = frame.xyz @ R
    for k in range(2):
        arr = np.zeros(frame.n, COMPACT_DTYPE)
        arr["x"], arr["y"], arr["z"] = xyz_s.T
        arr["intensity"] = frame.intensity
        np.save(d / f"synthetic_{k:04d}.npy", arr)
    return d
