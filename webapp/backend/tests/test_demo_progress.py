"""Progress of the synchronous demo generation: POST /api/recordings/demo with a client-chosen
``progress_id`` and GET /api/recordings/demo/progress/{progress_id} polled while it runs."""
from __future__ import annotations

import re

from resense_web import demo
from resense_web.api.recordings import DemoProgress


def test_progress_while_generating(client, monkeypatch):
    pid = "demo-progress-1"
    real = demo.generate_demo_bag
    polled: list[dict] = []

    def spy(out, scenario="approach", seconds=15.0, seed=0, progress=None):
        assert progress is not None

        def report(f: float) -> None:
            progress(f)
            if 0.3 < f < 0.9 and not polled:      # a poll from "the browser" while the POST is running
                polled.append(client.get(f"/api/recordings/demo/progress/{pid}").json())

        return real(out, scenario=scenario, seconds=seconds, seed=seed, progress=report)

    monkeypatch.setattr(demo, "generate_demo_bag", spy)
    r = client.post("/api/recordings/demo", json={"scenario": "clear", "seconds": 5, "progress_id": pid})
    assert r.status_code == 201, r.text
    rec = r.json()
    assert len(polled) == 1
    mid = polled[0]
    assert mid["progress_id"] == pid and 0.3 < mid["fraction"] < 0.9
    assert mid["done"] is False and mid["recording_id"] is None and mid["error"] is None
    end = client.get(f"/api/recordings/demo/progress/{pid}").json()
    assert end == {"progress_id": pid, "fraction": 1.0, "done": True, "recording_id": rec["id"], "error": None}


def test_progress_errors(client, monkeypatch):
    r = client.get("/api/recordings/demo/progress/unknown-id-123")
    assert r.status_code == 404 and r.json()["detail"] == "Создание демо-записи не найдено"
    for bad in ("short", "has space in it", "x" * 65, "../../etc"):
        r = client.post("/api/recordings/demo", json={"seconds": 5, "progress_id": bad})
        assert r.status_code == 422 and re.search("[а-яА-Я]", r.json()["detail"]), (bad, r.text)

    def broken(out, scenario="approach", seconds=15.0, seed=0, progress=None):
        progress(0.1)
        raise ValueError("Длительность демо-записи должна быть от 5 до 60 с")

    monkeypatch.setattr(demo, "generate_demo_bag", broken)
    r = client.post("/api/recordings/demo", json={"seconds": 5, "progress_id": "failing-demo-1"})
    assert r.status_code == 422 and r.json()["detail"].startswith("Длительность")
    item = client.get("/api/recordings/demo/progress/failing-demo-1").json()
    assert item["done"] is False and item["error"].startswith("Длительность") and item["fraction"] == 0.1
    assert client.get("/api/recordings").json() == []


def test_registry_rejects_a_running_id_and_expires():
    reg = DemoProgress()
    assert reg.start("abcdefgh") is True
    assert reg.start("abcdefgh") is False           # still running
    reg.update("abcdefgh", 1.7)
    assert reg.get("abcdefgh")["fraction"] == 1.0
    reg.fail("abcdefgh", "ошибка")
    assert reg.start("abcdefgh") is True            # a failed one may be retried
    reg.finish("abcdefgh", "rec1")
    assert reg.get("abcdefgh")["recording_id"] == "rec1"
    reg.TTL_S = -1.0
    assert reg.get("abcdefgh") is None
