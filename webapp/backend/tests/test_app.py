"""App wiring: the built frontend with SPA fallback, CORS for the Vite dev server, GZip for JSON,
Russian error bodies."""
from __future__ import annotations

import dataclasses

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
