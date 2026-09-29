"""Fixtures: an isolated data dir + server root per test, the app under TestClient, and small
real rosbag2 bags (synthetic tunnel frames, cached across sessions in pytest's cache dir)."""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[3]
SMOKE_SCRIPT = REPO / "scripts" / "make_smoke_bag.py"
BAG_CACHE_VERSION = "v1"
N_CLEAR, N_OBSTACLE, DECIMATE = 8, 12, 4


def _smoke():
    spec = importlib.util.spec_from_file_location("resense_make_smoke_bag", SMOKE_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def write_bag(path: Path, clouds, topic: str = "/lidar_points", frame_id: str = "hesai_lidar") -> Path:
    """A rosbag2 bag (sqlite3, Humble layout) of (xyz_sensor, intensity, ring) clouds at 10 Hz."""
    from rosbags.typesys import Stores, get_typestore
    mod = _smoke()
    mod.TOPIC, mod.FRAME_ID = topic, frame_id
    ts = get_typestore(Stores.ROS2_HUMBLE)
    rng = np.random.default_rng(0)
    t0, period = 1_700_000_000 * 1_000_000_000, 100_000_000
    msgs = (mod.make_message(ts, np.asarray(xyz, np.float32), np.asarray(inten, np.float32),
                             np.asarray(ring, np.uint16), t0 + i * period, 946_684_800.0 + 0.1 * i, rng)
            for i, (xyz, inten, ring) in enumerate(clouds))
    mod.write_bag(str(path), msgs, t0, period)
    return path


def random_clouds(n_frames: int = 3, n_points: int = 2000, seed: int = 0):
    rng = np.random.default_rng(seed)
    for _ in range(n_frames):
        xyz = rng.uniform([-5, 2, -2], [5, 80, 3], size=(n_points, 3)).astype(np.float32)
        yield xyz, rng.uniform(0, 255, n_points).astype(np.float32), rng.integers(0, 128, n_points).astype(np.uint16)


@pytest.fixture(scope="session")
def synthetic_clouds(request, tmp_path_factory):
    """(xyz_sensor, intensity, ring) of 8 empty-tunnel frames then 12 with a person at 30 m
    (resense.synthetic via scripts/make_smoke_bag.py, every 4th point)."""
    store = getattr(request.config, "cache", None)      # absent with -p no:cacheprovider
    cache = (Path(store.mkdir(f"resense_web_synth_{BAG_CACHE_VERSION}")) if store is not None
             else tmp_path_factory.mktemp("synth"))
    f = cache / "clouds.npz"
    if not f.is_file():
        pytest.importorskip("open3d")
        mod = _smoke()
        arrays = {}
        for i, (xyz, inten, ring) in enumerate(mod.build_frames(N_CLEAR, N_OBSTACLE, 30.0, 7)):
            arrays[f"xyz{i}"] = xyz[::DECIMATE]
            arrays[f"int{i}"] = inten[::DECIMATE]
            arrays[f"ring{i}"] = ring[::DECIMATE]
        np.savez(cache / "clouds_tmp.npz", **arrays)
        (cache / "clouds_tmp.npz").replace(f)
    with np.load(f) as z:
        n = len([k for k in z.files if k.startswith("xyz")])
        return [(z[f"xyz{i}"], z[f"int{i}"], z[f"ring{i}"]) for i in range(n)]


@pytest.fixture(scope="session")
def synthetic_bag(tmp_path_factory, synthetic_clouds) -> Path:
    return write_bag(tmp_path_factory.mktemp("bags") / "synth_tunnel", synthetic_clouds)


@pytest.fixture
def env(tmp_path, monkeypatch):
    """Isolated RESENSE_WEB_DATA / RESENSE_DATA for one test; returns the fresh Settings."""
    from resense_web.settings import get_settings
    data = tmp_path / "webdata"
    server = tmp_path / "server"
    server.mkdir()
    monkeypatch.setenv("RESENSE_WEB_DATA", str(data))
    monkeypatch.setenv("RESENSE_DATA", str(server))
    monkeypatch.setenv("RESENSE_WEB_STATIC", str(tmp_path / "no-frontend-build"))   # hermetic: ignore a real dist
    monkeypatch.delenv("RESENSE_WEB_MAX_UPLOAD_GB", raising=False)
    get_settings.cache_clear()
    yield get_settings()
    get_settings.cache_clear()


def make_client(settings, **kw):
    from fastapi.testclient import TestClient

    from resense_web.app import create_app
    return TestClient(create_app(settings, **kw))


@pytest.fixture
def client(env):
    with make_client(env) as c:
        yield c


def wait_job(client, job_id: str, statuses=("done", "failed", "cancelled"), timeout: float = 90.0) -> dict:
    t_end = time.monotonic() + timeout
    while True:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in statuses:
            return job
        if time.monotonic() > t_end:
            log = client.get(f"/api/jobs/{job_id}/log").text
            raise AssertionError(f"job {job_id} still {job['status']} after {timeout} s; log:\n{log}")
        time.sleep(0.1)


def sleeper_command(seconds: float = 60.0):
    """A stand-in worker that only sleeps (for queue / cancel tests)."""
    def cmd(_job_id: str) -> list[str]:
        return [sys.executable, "-c", f"import time; time.sleep({seconds})"]
    return cmd


def _link_or_copy(src, dst):
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)


def copy_into_server(settings, src: Path, name: str | None = None) -> str:
    """Put a bag / file under the server root (hard links: symlinks out of the root are refused)."""
    dest = settings.server_root / (name or src.name)
    if src.is_dir():
        shutil.copytree(src, dest, copy_function=_link_or_copy)
    else:
        _link_or_copy(src, dest)
    return dest.name
