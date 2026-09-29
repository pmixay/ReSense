"""WS /api/live/sim against a tiny fake run in a temporary data dir."""
from __future__ import annotations

import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from resense_web import live, settings

N = 6


def _frame(pos: int) -> dict:
    return {"pos": pos, "frame": 10 + 2 * pos, "t": 0.2 * pos, "stamp": 1000.0 + 0.2 * pos,
            "decision": "STOP" if pos in (2, 3) else "GO", "obstacle": pos in (2, 3), "warning": False,
            "nearest_distance": 55.0 if pos in (2, 3) else None, "detections": [], "warnings": [],
            "timing_ms": {"total": 40.0 + pos}, "health": {"level": "ok"}, "frame_id": "hesai_lidar"}


@pytest.fixture()
def sim(tmp_path, monkeypatch):
    run = tmp_path / "runs" / "run01"
    run.mkdir(parents=True)
    with open(run / "results.jsonl", "w", encoding="utf-8") as fh:
        for i in range(N):
            fh.write(json.dumps(_frame(i)) + "\n")
    (run / "clouds.json").write_text(json.dumps({"frames": [0, 3], "points": 30000, "format": "RSC1"}))
    (tmp_path / "runs" / "empty").mkdir()
    (tmp_path / "runs" / "empty" / "results.jsonl").write_text("")
    monkeypatch.setenv("RESENSE_WEB_DATA", str(tmp_path))
    settings.get_settings.cache_clear()
    app = FastAPI()
    app.include_router(live.router)
    with TestClient(app) as c:
        yield c
    settings.get_settings.cache_clear()


def _close_code(ws) -> int:
    with pytest.raises(WebSocketDisconnect) as e:
        ws.receive_json()
    return e.value.code


def test_streams_every_frame_then_closes(sim):
    with sim.websocket_connect("/api/live/sim?run_id=run01&speed=10") as ws:
        msgs = [ws.receive_json() for _ in range(N)]
        assert _close_code(ws) == 1000
    assert [m["pos"] for m in msgs] == list(range(N))
    assert [m["frame"] for m in msgs] == [10 + 2 * i for i in range(N)]
    assert [m["cloud_pos"] for m in msgs] == [0, 0, 0, 3, 3, 3]
    assert all(m["sim"] is True and m["snapshot_kind"] == "frame" for m in msgs)
    assert [m["node"]["frames"] for m in msgs] == list(range(1, N + 1))
    assert [m["node"]["latency_ms"] for m in msgs] == [40.0 + i for i in range(N)]
    assert all(m["node"]["dropped_frames"] == 0 and m["node"]["fps"] > 0 for m in msgs)
    assert msgs[2]["decision"] == "STOP" and msgs[2]["nearest_distance"] == 55.0


def test_loop_wraps_around(sim):
    with sim.websocket_connect("/api/live/sim?run_id=run01&speed=10&loop=true") as ws:
        pos = [ws.receive_json()["pos"] for _ in range(N + 3)]
    assert pos == list(range(N)) + [0, 1, 2]


def test_pause_seek_play(sim):
    with sim.websocket_connect("/api/live/sim?run_id=run01&speed=0.25") as ws:
        assert ws.receive_json()["pos"] == 0          # the first frame goes out at once
        ws.send_json({"cmd": "pause"})
        ws.send_json({"cmd": "seek", "pos": 4})
        m = ws.receive_json()                         # a seek shows its frame even while paused
        assert m["pos"] == 4 and m["cloud_pos"] == 3
        ws.send_json({"cmd": "play", "speed": 10})
        assert ws.receive_json()["pos"] == 5
        assert _close_code(ws) == 1000


def test_speed_command_and_garbage_are_tolerated(sim):
    with sim.websocket_connect("/api/live/sim?run_id=run01&speed=0.25&loop=1") as ws:
        assert ws.receive_json()["pos"] == 0
        ws.send_text("not json")
        ws.send_json({"cmd": "fly"})
        ws.send_json({"cmd": "seek", "pos": 999})     # clipped to the last frame
        assert ws.receive_json()["pos"] == N - 1
        ws.send_json({"cmd": "speed", "speed": 50})   # clipped to 10x
        assert ws.receive_json()["pos"] == 0          # loop
        assert ws.receive_json()["pos"] == 1


def test_unknown_run_and_bad_query(sim):
    for url, code in [("/api/live/sim?run_id=nope", 4404),
                      ("/api/live/sim?run_id=../etc", 4400),
                      ("/api/live/sim", 4400),
                      ("/api/live/sim?run_id=run01&speed=20", 4400),
                      ("/api/live/sim?run_id=run01&speed=abc", 4400),
                      ("/api/live/sim?run_id=run01&loop=maybe", 4400)]:
        with sim.websocket_connect(url) as ws:
            assert _close_code(ws) == code, url


def test_empty_run_closes_normally(sim):
    with sim.websocket_connect("/api/live/sim?run_id=empty") as ws:
        assert _close_code(ws) == 1000


def test_client_disconnect_mid_stream(sim):
    with sim.websocket_connect("/api/live/sim?run_id=run01&speed=1") as ws:
        ws.receive_json()
    # the server side must survive the client going away; a new session still works
    with sim.websocket_connect("/api/live/sim?run_id=run01&speed=10") as ws:
        assert ws.receive_json()["pos"] == 0


def test_cloud_pos_for():
    assert live.cloud_pos_for([], 5) is None
    assert live.cloud_pos_for([2, 5, 9], 1) is None
    assert live.cloud_pos_for([2, 5, 9], 5) == 5
    assert live.cloud_pos_for([2, 5, 9], 8) == 5
    assert live.cloud_pos_for([2, 5, 9], 100) == 9
