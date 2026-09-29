"""The real wiring end to end, no stand-ins: POST /api/recordings/demo (resense_web.demo) -> a job
through the worker subprocess (the sealed detector, resense_web.params) -> a run with clouds, a
summary and scores against the demo's ground truth (resense_web.evaluation) -> the live replay
of that run (resense_web.live) through the app's own settings."""
from __future__ import annotations

import csv
import io
import shutil
import time
from pathlib import Path

import numpy as np
import pytest
from conftest import make_client, wait_job
from starlette.websockets import WebSocketDisconnect

from resense_web import clouds
from resense_web.settings import get_settings

SECONDS = 5
N = SECONDS * 10


@pytest.fixture(scope="module")
def demo_run(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("integration")
    mp = pytest.MonkeyPatch()
    mp.setenv("RESENSE_WEB_DATA", str(tmp / "webdata"))
    mp.setenv("RESENSE_DATA", str(tmp / "server"))
    mp.setenv("RESENSE_WEB_STATIC", str(tmp / "no-dist"))
    (tmp / "server").mkdir()
    get_settings.cache_clear()
    try:
        with make_client(get_settings()) as client:
            r = client.post("/api/recordings/demo", json={"scenario": "approach", "seconds": SECONDS})
            assert r.status_code == 201, r.text
            rec = r.json()
            r = client.post("/api/jobs", json={"recording_id": rec["id"], "options": {"cloud_points": 8000}})
            assert r.status_code == 201, r.text
            job = wait_job(client, r.json()["id"])
            assert job["status"] == "done", client.get(f"/api/jobs/{job['id']}/log").text
            yield client, rec, job
    finally:
        mp.undo()
        get_settings.cache_clear()


def test_demo_recording_is_a_labelled_bag(demo_run):
    client, rec, _job = demo_run
    assert rec["kind"] == "rosbag2" and rec["source"] == "demo" and rec["n_frames"] == N
    assert rec["default_topic"] == "/lidar_points"
    assert rec["labels"] == {"available": True, "source": "builtin", "name": "demo_approach (эталон демо)"}
    assert client.get("/api/recordings").json()[0]["id"] == rec["id"]


def test_run_summary_stops_and_scores(demo_run):
    client, rec, job = demo_run
    assert job["progress"]["frames_done"] == N and job["progress"]["stage"] == "done"
    run = client.get(f"/api/runs/{job['run_id']}").json()
    assert run["recording"]["id"] == rec["id"] and run["source_kind"] == "rosbag2"
    assert run["has_clouds"] and run["cloud_frames"] == N
    s = run["summary"]
    assert s["n_frames"] == N and s["decisions"] == job["progress"]["decisions"]
    assert s["counts"]["STOP"] >= N * 0.8 and s["stop_episodes"] == 1
    first = s["first_stop"]
    assert first is not None and first["frame"] < 10 and first["distance"] > 25
    assert s["distance_min"] > 20 and s["latency_ms"]["p95"] > 0 and s["processing_fps"] > 0
    ev = s["eval"]
    assert ev is not None, client.get(f"/api/jobs/{job['id']}/log").text
    assert ev["frames_labelled"] == N and ev["frames_with_object_in_gauge"] == N
    assert ev["recall"] >= 0.8 and ev["false_stop_frames"] == 0 and ev["first_detection_distance"] > 25
    assert ev["labels_name"] == rec["labels"]["name"]
    stop_eps = [e for e in run["episodes"] if e["decision"] == "STOP"]
    assert len(stop_eps) == 1 and stop_eps[0]["last_frame"] == N - 1
    assert any(e["decision"] == "STOP" for e in run["events"])
    series = client.get(f"/api/runs/{job['run_id']}/series").json()
    assert series["labels_in_gauge"] == [True] * N and series["decisions"] == s["decisions"]


def test_clouds_are_in_the_vehicle_frame(demo_run):
    client, _rec, job = demo_run
    index = client.get(f"/api/runs/{job['run_id']}/clouds").json()
    assert index == {"frames": list(range(N)), "points": 8000, "format": "RSC1"}
    last_stop = N - 1
    xyz, _inten, flags = clouds.unpack_rsc1(client.get(f"/api/runs/{job['run_id']}/clouds/{last_stop}").content)
    assert len(xyz) == 8000
    assert 1.0 < xyz[:, 0].min() and 150 < xyz[:, 0].max() < 215          # ahead, up to the sensor's reach
    track = xyz[(np.abs(xyz[:, 1]) < 1.0) & (xyz[:, 0] > 5) & (xyz[:, 0] < 40)]
    assert np.percentile(track[:, 2], 5) == pytest.approx(-1.5, abs=0.1)    # the track bed
    assert (flags & clouds.FLAG_CORRIDOR).any() and (flags & clouds.FLAG_OBJECT).any()
    person = xyz[(flags & clouds.FLAG_OBJECT) > 0]
    frame = client.get(f"/api/runs/{job['run_id']}/frames", params={"from": last_stop, "count": 1}).json()
    assert frame["frames"][0]["decision"] == "STOP"
    assert np.median(person[:, 0]) == pytest.approx(frame["frames"][0]["nearest_distance"], abs=1.0)


def test_downloads(demo_run):
    client, _rec, job = demo_run
    base = f"/api/runs/{job['run_id']}/download"
    lines = client.get(f"{base}/results.jsonl").text.splitlines()
    assert len(lines) == N
    report = client.get(f"{base}/report.json").json()
    assert report["schema"] == "resense_web_report" and report["run"]["summary"]["eval"]["recall"] >= 0.8
    rows = list(csv.reader(io.StringIO(client.get(f"{base}/frames.csv").text)))
    assert len(rows) == N + 1 and rows[-1][3] == "STOP"


def test_live_sim_replays_the_run(demo_run):
    client, _rec, job = demo_run
    with client.websocket_connect(f"/api/live/sim?run_id={job['run_id']}&speed=10") as ws:
        first = [ws.receive_json() for _ in range(3)]
        ws.send_json({"cmd": "seek", "pos": N - 5})
        msg = ws.receive_json()
        while msg["pos"] < N - 5:
            msg = ws.receive_json()
    assert [m["pos"] for m in first] == [0, 1, 2] and [m["cloud_pos"] for m in first] == [0, 1, 2]
    assert all(m["sim"] and m["snapshot_kind"] == "frame" and m["node"]["latency_ms"] > 0 for m in first)
    assert msg["pos"] == N - 5 and msg["decision"] == "STOP" and msg["nearest_distance"] > 20
    with client.websocket_connect("/api/live/sim?run_id=nope") as ws, pytest.raises(WebSocketDisconnect) as exc:
        ws.receive_json()
    assert exc.value.code == 4404


def test_demo_zip_and_server_copy_keep_the_ground_truth(demo_run, tmp_path):
    """The demo zip uploaded again, or the bag folder copied into the server folder, keeps its
    ground_truth.json as labels; the upload runs like the original."""
    client, rec, job = demo_run
    blob = client.get(f"/api/recordings/{rec['id']}/download").content
    uid = client.post("/api/uploads", json={"name": "демо из архива"}).json()["upload_id"]
    r = client.put(f"/api/uploads/{uid}/files", params={"path": "demo_approach.zip"}, content=blob)
    assert r.status_code == 200 and r.json()["size_bytes"] == len(blob)
    r = client.post(f"/api/uploads/{uid}/finalize")
    assert r.status_code == 201, r.text
    up = r.json()
    assert up["source"] == "upload" and up["kind"] == "rosbag2" and up["n_frames"] == N
    assert up["name"] == "демо из архива"
    assert up["labels"] == {"available": True, "source": "builtin", "name": "ground_truth.json (рядом с записью)"}
    j = wait_job(client, client.post("/api/jobs", json={"recording_id": up["id"],
                                                        "options": {"clouds": False}}).json()["id"])
    assert j["status"] == "done" and j["progress"]["decisions"] == job["progress"]["decisions"]
    assert client.get(f"/api/runs/{j['run_id']}").json()["summary"]["eval"]["recall"] >= 0.8

    settings = get_settings()
    shutil.copytree(Path(rec["path"]), settings.server_root / "tunnel" / "demo_approach")
    listing = client.get("/api/server-files", params={"path": "tunnel"}).json()
    assert [(e["name"], e["is_bag"], e["n_frames"]) for e in listing["entries"]] == [("demo_approach", True, N)]
    srv = client.post("/api/recordings/from-server", json={"path": "tunnel/demo_approach"}).json()
    assert srv["source"] == "server" and srv["labels"]["available"] and srv["labels"]["source"] == "builtin"


def test_cancel_a_running_worker(demo_run):
    client, rec, _job = demo_run
    job = client.post("/api/jobs", json={"recording_id": rec["id"], "options": {"cloud_points": 120000}}).json()
    t_end = time.monotonic() + 60
    while client.get(f"/api/jobs/{job['id']}").json()["progress"]["frames_done"] < 3:
        assert time.monotonic() < t_end
        time.sleep(0.05)
    r = client.post(f"/api/jobs/{job['id']}/cancel")
    assert r.status_code == 200, r.text
    cancelled = r.json()
    assert cancelled["status"] == "cancelled" and cancelled["run_id"] is None
    assert cancelled["progress"]["frames_done"] >= 3             # the worker's last snapshot, not an empty one
    settings = get_settings()
    row = client.app.state.ctx.jobs.get(job["id"])
    while (settings.runs_dir / row["run_id"]).exists() or client.app.state.ctx.jobs._proc is not None:
        assert time.monotonic() < t_end, "the partial run folder was not removed"
        time.sleep(0.1)
    assert client.post(f"/api/jobs/{job['id']}/cancel").status_code == 409
    assert all(r["job_id"] != job["id"] for r in client.get("/api/runs").json())
