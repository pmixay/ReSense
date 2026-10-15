"""Runtime settings from the environment (webapp/API.md, «Environment») and the data dir layout.

    <data_dir>/resense_web.sqlite     recordings, jobs, runs, presets
    <data_dir>/uploads/<id>/          staging areas of unfinished uploads (resumable: files/ and parts/)
    <data_dir>/recordings/<id>/       uploaded / demo recordings, uploaded labels
    <data_dir>/jobs/<id>/             spec.json, progress.json, result.json, worker.log of a job
    <data_dir>/runs/<id>/             results.jsonl (+ .idx), clouds.bin, clouds.json, series.json,
                                      summary.json, worker.log
    <data_dir>/cache/                 generated downloads (demo bag zips)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
BACKEND_DIR = PACKAGE_DIR.parent
WEBAPP_DIR = BACKEND_DIR.parent


def _repo_root() -> Path:
    """The ReSense checkout (configs/, labels/): where the editable ``resense`` package lives."""
    try:
        import resense
        root = Path(resense.__file__).resolve().parents[1]
        if (root / "configs" / "default.yaml").is_file():
            return root
    except ImportError:
        pass
    return WEBAPP_DIR.parent


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name, "").strip()
    return Path(raw).expanduser().resolve() if raw else default.resolve()


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    try:
        return float(raw) if raw else default
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


# Behind a reverse proxy the backend must keep an idle connection open longer than the proxy does:
# whoever closes first must be the proxy, or it may send a request on a connection uvicorn is just
# closing and answer 502 (a POST is never retried). uvicorn's own default is 5 s; Caddy keeps idle
# upstream connections 2 min, Traefik 90 s, nginx 60 s.
KEEP_ALIVE_S = 130


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    server_root: Path
    max_upload_bytes: int
    host: str
    port: int
    repo_root: Path
    frontend_dist: Path
    upload_ttl_s: float = 72 * 3600.0     # an unfinished upload is kept this long after its last write
    keep_alive_s: int = KEEP_ALIVE_S      # an idle HTTP connection is closed after this long

    @property
    def db_path(self) -> Path:
        return self.data_dir / "resense_web.sqlite"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def recordings_dir(self) -> Path:
        return self.data_dir / "recordings"

    @property
    def jobs_dir(self) -> Path:
        return self.data_dir / "jobs"

    @property
    def runs_dir(self) -> Path:
        return self.data_dir / "runs"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def default_config(self) -> Path:
        return self.repo_root / "configs" / "default.yaml"

    def ensure_dirs(self) -> None:
        for d in (self.data_dir, self.uploads_dir, self.recordings_dir, self.jobs_dir, self.runs_dir,
                  self.cache_dir):
            d.mkdir(parents=True, exist_ok=True)
        ignore = self.data_dir / ".gitignore"
        if not ignore.exists():
            try:
                ignore.write_text("*\n", encoding="utf-8")
            except OSError:
                pass


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Settings of this process (cached; tests call ``get_settings.cache_clear()``)."""
    repo = _repo_root()
    gb = _env_float("RESENSE_WEB_MAX_UPLOAD_GB", 100.0)
    return Settings(
        data_dir=_env_path("RESENSE_WEB_DATA", WEBAPP_DIR / "data"),
        server_root=_env_path("RESENSE_DATA", Path("/data")),
        max_upload_bytes=max(1, int(gb * 1024 ** 3)),
        host=os.environ.get("RESENSE_WEB_HOST", "").strip() or "0.0.0.0",
        port=_env_int("RESENSE_WEB_PORT", 8080),
        repo_root=repo,
        frontend_dist=_env_path("RESENSE_WEB_STATIC", WEBAPP_DIR / "frontend" / "dist"),
        upload_ttl_s=max(0.1, _env_float("RESENSE_WEB_UPLOAD_TTL_H", 72.0)) * 3600.0,
        keep_alive_s=max(1, _env_int("RESENSE_WEB_KEEPALIVE_S", KEEP_ALIVE_S)),
    )
