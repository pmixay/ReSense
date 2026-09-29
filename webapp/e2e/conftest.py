"""Shared fixtures of the browser end-to-end suite of the web prototype (webapp/e2e, see README.md).

* ``dist`` (session): the production build of the frontend the whole suite runs against —
  ``WEBAPP_DIST`` when set; else ``webapp/frontend/dist`` when it is newer than every frontend
  source; else a fresh ``vite build`` into a temporary folder (the checkout's ``dist/`` is never
  overwritten, a server may be serving it).
* ``backend`` (module): one ``python -m resense_web`` per test module on a free port, serving that
  build and the API on the same origin (``RESENSE_WEB_STATIC``), with its own fresh data dir
  (``RESENSE_WEB_DATA``) and an empty server folder (``RESENSE_DATA``). Every module starts on an
  empty stand (its first test checks the empty states) and seeds what it needs through
  ``backend.api``; the tests of a module run in order and build on each other. The data dir is
  removed when the module ends (demo bags are ~33 MB per second) unless ``WEBAPP_E2E_KEEP=1``;
  the server log (``backend.log``) stays in pytest's temp dir.
* ``browser`` (session): headless Chromium, WebGL through SwiftShader for the 3D views
  (``PW_CHROMIUM`` overrides the executable).
* ``app`` (test): a fresh browser context and page at 1600×1000 on the backend, plus the console
  errors the page logged (``app.errors``; filter provoked ones with ``e2e_helpers.real_errors``).

Run: ``python -m pytest -q webapp/e2e`` with an interpreter that has the backend package, pytest,
playwright and websockets; Node and ``webapp/frontend/node_modules`` only when a build is needed.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from e2e_helpers import free_port

REPO = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO / "webapp" / "backend"
FRONTEND_DIR = REPO / "webapp" / "frontend"
PYTHON = os.environ.get("RESENSE_PYTHON", sys.executable)
CHROMIUM_CANDIDATES = ("/opt/pw-browsers/chromium-1194/chrome-linux/chrome", "/opt/pw-browsers/chromium")
CHROMIUM_ARGS = ["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
ACTIVE = ("queued", "running")
# what a build depends on: a dist/ older than any of these is stale
BUILD_INPUTS = ("src", "public", "index.html", "vite.config.ts", "package.json", "package-lock.json", "tsconfig.json")


def _wait_http(url: str, proc: subprocess.Popen, log: Path, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"{proc.args!r} exited with {proc.returncode}:\n{log.read_text(errors='replace')[-3000:]}")
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    return
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.2)
    raise RuntimeError(f"{url} did not answer in {timeout:.0f} s:\n{log.read_text(errors='replace')[-3000:]}")


def _stop(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)


class ApiError(Exception):
    def __init__(self, status: int, detail):
        super().__init__(f"{status}: {detail}")
        self.status = status
        self.detail = detail


class Api:
    """Tiny JSON client of the backend (webapp/API.md) for seeding and checking state."""

    def __init__(self, base: str):
        self.base = base.rstrip("/")

    def call(self, method: str, path: str, body=None, *, raw: bytes | None = None, timeout: float = 600):
        data, headers = None, {"Accept": "application/json"}
        if raw is not None:
            data, headers["Content-Type"] = raw, "application/octet-stream"
        elif body is not None:
            data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
        req = urllib.request.Request(self.base + "/api" + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                text = r.read().decode("utf-8")
                if (r.headers.get("Content-Type") or "").startswith("application/json"):
                    return json.loads(text) if text else None
                return text
        except urllib.error.HTTPError as e:
            try:
                detail = json.loads(e.read().decode("utf-8")).get("detail")
            except ValueError:
                detail = None
            raise ApiError(e.code, detail) from None

    def get(self, path: str):
        return self.call("GET", path)

    def post(self, path: str, body=None):
        return self.call("POST", path, body if body is not None else {})

    def delete(self, path: str):
        return self.call("DELETE", path)

    # ---------------------------------------------------------------- seeding helpers

    def demo(self, scenario: str = "approach", seconds: float = 5, **extra) -> dict:
        """A synthetic demo recording (synchronous: ~1 s per simulated second, ~33 MB per second)."""
        return self.post("/recordings/demo", {"scenario": scenario, "seconds": seconds, **extra})

    def job(self, recording_id: str, preset_id: str | None = None, options: dict | None = None) -> dict:
        body: dict = {"recording_id": recording_id}
        if preset_id:
            body["preset_id"] = preset_id
        if options:
            body["options"] = options
        return self.post("/jobs", body)

    def wait_job(self, job_id: str, timeout: float = 240) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            job = self.get(f"/jobs/{job_id}")
            if job["status"] not in ACTIVE:
                return job
            if time.monotonic() > deadline:
                raise TimeoutError(f"job {job_id} still {job['status']} after {timeout} s")
            time.sleep(0.3)

    def wait_idle(self, timeout: float = 300) -> None:
        deadline = time.monotonic() + timeout
        while self.get("/jobs?status=queued,running"):
            if time.monotonic() > deadline:
                raise TimeoutError("the job queue did not drain")
            time.sleep(0.3)

    def upload_jsonl(self, name: str, body: bytes) -> dict:
        """A results-only recording (``<name>.jsonl``) through the staged upload API."""
        up = self.post("/uploads", {"name": name})["upload_id"]
        self.call("PUT", f"/uploads/{up}/files?path={name}.jsonl", raw=body)
        return self.post(f"/uploads/{up}/finalize")

    def processed(self, recording_id: str, **job_kw) -> dict:
        """The finished job of one recording (asserts it is done)."""
        job = self.wait_job(self.job(recording_id, **job_kw)["id"])
        assert job["status"] == "done", job
        return job


# ------------------------------------------------------------------------------------ build


def _newest_input() -> float:
    newest = 0.0
    for name in BUILD_INPUTS:
        p = FRONTEND_DIR / name
        if p.is_file():
            newest = max(newest, p.stat().st_mtime)
        elif p.is_dir():
            newest = max([newest, *(f.stat().st_mtime for f in p.rglob("*") if f.is_file())])
    return newest


@pytest.fixture(scope="session")
def dist(tmp_path_factory) -> Path:
    """The production build the suite runs against (see the module docstring)."""
    given = os.environ.get("WEBAPP_DIST")
    if given:
        path = Path(given).resolve()
        if not (path / "index.html").is_file():
            raise RuntimeError(f"WEBAPP_DIST={given} has no index.html (run npm run build)")
        return path
    checkout = FRONTEND_DIR / "dist"
    index = checkout / "index.html"
    if index.is_file() and index.stat().st_mtime >= _newest_input():
        return checkout
    if not (FRONTEND_DIR / "node_modules").is_dir():
        raise RuntimeError("webapp/frontend/dist is missing or stale and node_modules is not installed: run npm ci && npm run build")
    out = tmp_path_factory.mktemp("dist")
    log = out.parent / "vite-build.log"
    with open(log, "wb") as fh:
        rc = subprocess.call(["npx", "vite", "build", "--outDir", str(out), "--emptyOutDir", "--logLevel", "warn"],
                             cwd=FRONTEND_DIR, stdout=fh, stderr=subprocess.STDOUT, timeout=300)
    if rc != 0 or not (out / "index.html").is_file():
        raise RuntimeError(f"vite build failed ({rc}):\n{log.read_text(errors='replace')[-3000:]}")
    return out


# ---------------------------------------------------------------------------------- servers


@dataclass
class Backend:
    url: str
    data_dir: Path
    server_root: Path
    log: Path
    api: Api
    proc: subprocess.Popen = field(repr=False)


@pytest.fixture(scope="module")
def backend(dist, tmp_path_factory) -> Backend:
    """A fresh stand for one test module: the API and the built frontend on one origin."""
    base = tmp_path_factory.mktemp("webapp")
    data_dir, server_root, log = base / "data", base / "server", base / "backend.log"
    server_root.mkdir()
    port = free_port()
    env = {**os.environ, "RESENSE_WEB_DATA": str(data_dir), "RESENSE_DATA": str(server_root),
           "RESENSE_WEB_STATIC": str(dist), "PYTHONUNBUFFERED": "1"}
    with open(log, "wb") as fh:
        proc = subprocess.Popen([PYTHON, "-m", "resense_web", "--host", "127.0.0.1", "--port", str(port)], cwd=BACKEND_DIR,
                                env=env, stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)
    url = f"http://127.0.0.1:{port}"
    try:
        _wait_http(url + "/api/health", proc, log, timeout=60)
        yield Backend(url=url, data_dir=data_dir, server_root=server_root, log=log, api=Api(url), proc=proc)
    finally:
        _stop(proc)
        if not os.environ.get("WEBAPP_E2E_KEEP"):
            shutil.rmtree(data_dir, ignore_errors=True)
            shutil.rmtree(server_root, ignore_errors=True)


@pytest.fixture(scope="session")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api")
    exe = os.environ.get("PW_CHROMIUM") or next((p for p in CHROMIUM_CANDIDATES if os.path.exists(p)), None)
    pw = sync_api.sync_playwright().start()
    b = pw.chromium.launch(executable_path=exe, args=CHROMIUM_ARGS)
    try:
        yield b
    finally:
        b.close()
        pw.stop()


@dataclass
class App:
    """A browser page on the app and what it reported."""

    page: object
    base: str
    errors: list[str]

    def goto(self, route: str, **kw) -> None:
        self.page.goto(self.base + route, **kw)

    def path(self) -> str:
        """The current location without the origin ("/upload?source=demo")."""
        return self.page.url[len(self.base):]


@pytest.fixture
def app(browser, backend) -> App:
    ctx = browser.new_context(viewport={"width": 1600, "height": 1000}, base_url=backend.url)
    ctx.set_default_timeout(30_000)
    page = ctx.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    try:
        yield App(page=page, base=backend.url, errors=errors)
    finally:
        ctx.close()
