"""GET /api/system, GET /api/health."""
from __future__ import annotations

import importlib.util
import os
import shutil
import time

from fastapi import APIRouter, Depends

import resense_web
from resense_web.api.deps import Context, get_ctx

router = APIRouter()


def _importable(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _native_enabled() -> bool:
    try:
        from resense import _native
        return bool(_native.enabled())
    except Exception:
        return False


@router.get("/health")
def health() -> dict:
    return {"ok": True}


@router.get("/system")
def system(ctx: Context = Depends(get_ctx)) -> dict:
    import resense
    s = ctx.settings
    cpu = os.cpu_count() or 1
    try:
        load = float(os.getloadavg()[0])
    except OSError:
        load = 0.0
    try:
        free = shutil.disk_usage(s.data_dir).free
    except OSError:
        free = 0
    db = ctx.db
    return {
        "version": resense_web.__version__,
        "detector_version": resense.__version__,
        "uptime_s": round(time.time() - ctx.started, 1),
        "cpu_count": cpu,
        "load_1m": round(load, 2),
        "cpu_cores_busy": round(min(float(cpu), load), 2),
        "disk_free_bytes": int(free),
        "data_dir": str(s.data_dir),
        "server_root": str(s.server_root),
        "server_root_exists": s.server_root.is_dir(),
        "features": {"rosbags": _importable("rosbags"), "open3d": _importable("open3d"),
                     "native_kernels": _native_enabled(), "clouds": True},
        "counts": {
            "recordings": int(db.scalar("SELECT COUNT(*) FROM recordings") or 0),
            "runs": int(db.scalar("SELECT COUNT(*) FROM runs") or 0),
            "jobs_queued": int(db.scalar("SELECT COUNT(*) FROM jobs WHERE status = 'queued'") or 0),
            "jobs_running": int(db.scalar("SELECT COUNT(*) FROM jobs WHERE status = 'running'") or 0),
        },
    }
