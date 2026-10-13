"""App wiring: the built frontend with SPA fallback, CORS for the Vite dev server, GZip for JSON,
Russian error bodies; the server's keep-alive (it must outlast a reverse proxy's)."""
from __future__ import annotations

import dataclasses
import os
import socket
import subprocess
import sys
import time

from conftest import make_client


def test_spa_fallback_and_static(env, tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>ReSense</title>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret")
    with make_client(dataclasses.replace(env, frontend_dist=dist)) as client:
        r = client.get("/")
        assert r.status_code == 200 and "<title>ReSense</title>" in r.text
        r = client.get("/runs/abc/player")                    # client-side route -> index.html
        assert r.status_code == 200 and "<title>ReSense</title>" in r.text
        r = client.get("/assets/app.js")
        assert r.status_code == 200 and "immutable" in r.headers["cache-control"]
        assert "console.log" in r.text
        assert client.get("/assets/stale-chunk.js").status_code == 404    # never index.html for a missing asset
        assert "secret" not in client.get("/../secret.txt").text
        assert "secret" not in client.get("/%2e%2e/secret.txt").text
        r = client.get("/api/unknown/thing")                  # never the SPA under /api
        assert r.status_code == 404 and r.json() == {"detail": "Не найдено"}


def test_without_a_build(client):
    r = client.get("/")
    assert r.status_code == 200 and "npm run build" in r.text


def test_cors_gzip_and_errors(client):
    r = client.get("/api/presets", headers={"Origin": "http://localhost:5173"})
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    r = client.options("/api/jobs", headers={"Origin": "http://127.0.0.1:5173",
                                             "Access-Control-Request-Method": "POST"})
    assert r.status_code == 200
    r = client.get("/api/presets/schema", headers={"Accept-Encoding": "gzip"})
    assert r.headers.get("content-encoding") == "gzip"
    r = client.post("/api/jobs", content=b"{not json", headers={"content-type": "application/json"})
    assert r.status_code == 422 and r.json()["detail"].startswith("Некорректный запрос")
    r = client.post("/api/jobs", json={})
    assert r.status_code == 422 and "recording_id" in r.json()["detail"] and "обязательное" in r.json()["detail"]
    r = client.put("/api/presets")
    assert r.status_code == 405 and r.json()["detail"] == "Метод не поддерживается"


def test_keep_alive_outlasts_the_proxy(env, monkeypatch):
    """uvicorn closes an idle connection after 5 s unless told otherwise; a reverse proxy keeps its
    idle upstream connections longer (Caddy 2 min) and may send a request on one uvicorn is closing:
    Caddy answers 502, a POST is never retried. The server keeps idle connections 130 s."""
    import uvicorn

    from resense_web import __main__ as main_mod
    from resense_web.settings import get_settings
    seen = {}
    monkeypatch.setattr(uvicorn, "run", lambda *a, **kw: seen.update(kw))
    assert main_mod.main([]) == 0 and seen["timeout_keep_alive"] == 130
    assert main_mod.main(["--timeout-keep-alive", "75"]) == 0 and seen["timeout_keep_alive"] == 75
    monkeypatch.setenv("RESENSE_WEB_KEEPALIVE_S", "200")
    get_settings.cache_clear()
    assert main_mod.main([]) == 0 and seen["timeout_keep_alive"] == 200


def _get(sock: socket.socket) -> bytes:
    sock.sendall(b"GET /api/health HTTP/1.1\r\nHost: x\r\n\r\n")
    data = b""
    while b"\r\n\r\n" not in data or not data.endswith(b"}"):
        chunk = sock.recv(4096)
        if not chunk:
            raise ConnectionError("the server closed the kept-alive connection")
        data += chunk
    return data


def test_an_idle_connection_survives_uvicorns_default(env):
    """The real server (python -m resense_web): a connection idle for 6 s, past uvicorn's default
    5 s keep-alive, still serves the next request."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen([sys.executable, "-m", "resense_web", "--host", "127.0.0.1", "--port", str(port),
                             "--log-level", "warning"], env=dict(os.environ), cwd=os.getcwd(),
                            stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        t_end = time.monotonic() + 60
        while True:
            try:
                sock = socket.create_connection(("127.0.0.1", port), timeout=10)
                break
            except OSError:
                assert proc.poll() is None and time.monotonic() < t_end, "the server did not start"
                time.sleep(0.2)
        with sock:
            assert b" 200 OK" in _get(sock)
            time.sleep(6.0)
            assert b" 200 OK" in _get(sock)
    finally:
        proc.terminate()
        proc.wait(10)
