"""End to end through the real worker subprocess on a small real rosbag2 bag (synthetic tunnel, a
person at 30 m from frame 8), then every runs endpoint: detail, series, frame paging, RSC1 clouds,
downloads, rename, delete; plus the npy folder and the results-jsonl import paths."""
from __future__ import annotations

import csv
import io
import json

import numpy as np
import pytest
from conftest import copy_into_server, make_client, wait_job

from resense_web import clouds
from resense_web import runs as runs_mod
from resense_web.settings import get_settings

N_FRAMES = 20


@pytest.fixture(scope="module")
def done_run(tmp_path_factory, synthetic_bag):
    """A finished job on the synthetic bag (one worker run shared by the tests of this module)."""
    tmp = tmp_path_factory.mktemp("runs_env")
    mp = pytest.MonkeyPatch()
    mp.setenv("RESENSE_WEB_DATA", str(tmp / "webdata"))
    mp.setenv("RESENSE_DATA", str(tmp / "server"))
    (tmp / "server").mkdir()
    get_settings.cache_clear()
    settings = get_settings()
    try:
        with make_client(settings) as client:
            copy_into_server(settings, synthetic_bag)
            rec = client.post("/api/recordings/from-server", json={"path": synthetic_bag.name}).json()
            r = client.post("/api/jobs", json={"recording_id": rec["id"], "options": {"cloud_points": 6000}})
            assert r.status_code == 201, r.text
            job = wait_job(client, r.json()["id"])
            assert job["status"] == "done", client.get(f"/api/jobs/{job['id']}/log").text
            yield client, settings, rec, job
    finally:
        mp.undo()
        get_settings.cache_clear()


def test_job_progress_and_run_list(done_run):
    client, settings, rec, job = done_run
    p = job["progress"]
    assert p["stage"] == "done" and p["frames_done"] == N_FRAMES and p["frames_total"] == N_FRAMES
    assert len(p["decisions"]) == N_FRAMES and set(p["decisions"]) <= set("GCSF")
    assert p["last"]["frame"] == N_FRAMES - 1 and "total" in p["stage_ms"]
    assert job["run_id"] and job["started_at"] and job["finished_at"] and job["error"] is None
    runs = client.get("/api/runs").json()
    assert [r["id"] for r in runs] == [job["run_id"]]
    run = runs[0]
    assert run["name"] == rec["name"] and run["recording_id"] == rec["id"] and run["job_id"] == job["id"]
    assert run["preset"] == {"id": "standard", "name": "Стандарт 1.0"}
    assert run["has_clouds"] and run["cloud_frames"] == N_FRAMES and run["source_kind"] == "rosbag2"
    s = run["summary"]
    assert s["n_frames"] == N_FRAMES and s["decisions"] == p["decisions"]
    assert s["duration_s"] == pytest.approx(1.9, abs=0.01)
    assert sum(s["counts"].values()) == N_FRAMES
    # the person at 30 m (frames 8..19) is a confirmed STOP by the end, none before it appears
    assert "S" not in s["decisions"][:8] and s["decisions"].endswith("SSS")
    assert s["stop_episodes"] >= 1 and s["first_stop"]["frame"] >= 8
    assert 28.0 < s["distance_min"] <= s["distance_max"] < 32.0
    assert s["latency_ms"]["p50"] > 0 and s["latency_ms"]["max"] >= s["latency_ms"]["p95"]
    assert s["processing_fps"] > 0 and s["eval"] is None
    assert (settings.runs_dir / job["run_id"] / "worker.log").is_file()
    assert client.get("/api/system").json()["counts"]["runs"] == 1


def test_run_detail_and_series(done_run):
    client, settings, rec, job = done_run
    d = client.get(f"/api/runs/{job['run_id']}").json()
    assert d["recording"]["id"] == rec["id"]
    eps = d["episodes"]
    assert sum(e["n_frames"] for e in eps) == N_FRAMES and eps[-1]["decision"] == "STOP"
    assert eps[-1]["last_frame"] == N_FRAMES - 1 and eps[-1]["distance_min"] is not None
    assert all(e["decision"] != "GO" for e in d["events"][-1:])
    # what the run was made with, and its stored files
    assert d["options"]["cloud_points"] == 6000 and d["options"]["every"] == 1 and d["overrides"] == {}
    assert d["sizes"]["results_jsonl"] > 0 and d["sizes"]["clouds"] > 0
    assert d["sizes"]["results_jsonl"] == (settings.runs_dir / job["run_id"] / "results.jsonl").stat().st_size
    # the CSV is streamed without a length: its exact size is measured once and remembered
    csv_bytes = client.get(f"/api/runs/{job['run_id']}/download/frames.csv").content
    assert d["sizes"]["frames_csv"] == len(csv_bytes) > 0
    assert (settings.runs_dir / job["run_id"] / "frames.csv.size").read_text() == str(len(csv_bytes))
    assert client.get(f"/api/runs/{job['run_id']}").json()["sizes"]["frames_csv"] == len(csv_bytes)
    assert "options" not in client.get("/api/runs").json()[0]
    # no labels for this recording: the labels overlay is unavailable (200, not an error)
    assert client.get(f"/api/runs/{job['run_id']}/labels").json() == {
        "available": False, "labels_name": None, "in_gauge": [], "near": [], "far": []}
    assert client.get("/api/runs/nosuch/labels").status_code == 404
    series = client.get(f"/api/runs/{job['run_id']}/series").json()
    assert series["frame"] == list(range(N_FRAMES)) and series["decisions"] == d["summary"]["decisions"]
    for key in ("t", "nearest", "clear", "latency_ms", "n_detections", "n_warnings", "n_points", "visibility"):
        assert len(series[key]) == N_FRAMES, key
    assert series["labels_in_gauge"] is None
    assert series["n_detections"][-1] >= 1 and series["nearest"][-1] is not None
    assert series["t"][0] == 0.0 and series["t"][-1] == pytest.approx(1.9, abs=0.01)


def test_frames_paging(done_run):
    client, _settings, _rec, job = done_run
    url = f"/api/runs/{job['run_id']}/frames"
    page = client.get(url, params={"from": 5, "count": 4}).json()
    assert (page["from"], page["count"], page["total"]) == (5, 4, N_FRAMES)
    f = page["frames"][0]
    assert f["pos"] == 5 and f["frame"] == 5 and f["frame_id"] == "hesai_lidar" and f["t"] == pytest.approx(0.5)
    for key in ("stamp", "obstacle", "warning", "nearest_distance", "detections", "warnings", "track",
                "timing_ms", "health", "mount", "clear_distance", "decision", "n_corridor"):
        assert key in f, key
    last = client.get(url, params={"from": 18, "count": 500}).json()
    assert last["count"] == 2 and last["frames"][-1]["decision"] == "STOP"
    assert last["frames"][-1]["detections"][0]["distance"] == pytest.approx(30.0, abs=1.5)
    assert client.get(url, params={"from": 99}).json() == {"from": N_FRAMES, "count": 0, "total": N_FRAMES,
                                                            "frames": []}
    assert client.get(url, params={"count": 100000}).json()["count"] == N_FRAMES
    assert client.get(url, params={"from": -1}).status_code == 422
    assert client.get("/api/runs/nosuch/frames").status_code == 404


def test_clouds_rsc1(done_run):
    client, _settings, _rec, job = done_run
    idx = client.get(f"/api/runs/{job['run_id']}/clouds").json()
    assert idx == {"frames": list(range(N_FRAMES)), "points": 6000, "format": "RSC1"}
    r = client.get(f"/api/runs/{job['run_id']}/clouds/{N_FRAMES - 1}")
    assert r.status_code == 200 and r.headers["content-type"] == "application/octet-stream"
    assert "immutable" in r.headers["cache-control"] and "content-encoding" not in r.headers
    xyz, inten, flags = clouds.unpack_rsc1(r.content)
    assert len(xyz) >= 6000 - 1 and inten.dtype == np.uint8
    assert (flags & clouds.FLAG_CORRIDOR).any()
    obj = xyz[(flags & clouds.FLAG_OBJECT) != 0]
    assert len(obj) > 5                                        # the person's points, flagged as STOP object
    assert np.all(np.abs(obj[:, 0] - 30.0) < 1.5) and np.all(np.abs(obj[:, 1]) < 1.5)
    # the cloud is the mount-corrected vehicle frame: the tunnel floor is below the sensor
    assert np.median(xyz[:, 2]) < 0.5 and xyz[:, 0].max() > 60
    assert client.get(f"/api/runs/{job['run_id']}/clouds/{N_FRAMES}").status_code == 404
    assert client.get(f"/api/runs/{job['run_id']}/clouds/x").status_code == 422


def test_downloads(done_run):
    client, _settings, rec, job = done_run
    base = f"/api/runs/{job['run_id']}/download"
    r = client.get(f"{base}/results.jsonl")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    lines = [json.loads(x) for x in r.text.splitlines()]
    assert [x["pos"] for x in lines] == list(range(N_FRAMES)) and "decision" in lines[0]
    r = client.get(f"{base}/report.json")
    rep = r.json()
    assert rep["schema"] == "resense_web_report" and rep["version"] == 1 and rep["generated_at"]
    assert rep["run"]["id"] == job["run_id"] and rep["run"]["summary"]["n_frames"] == N_FRAMES
    assert "sizes" not in rep["run"] and rep["options"]["cloud_points"] == 6000 and rep["overrides"] == {}
    assert sum(e["n_frames"] for e in rep["episodes"]) == N_FRAMES
    assert "report.json" in r.headers["content-disposition"]
    r = client.get(f"{base}/frames.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0] == ["pos", "frame", "t", "decision", "nearest_distance", "clear_distance", "latency_ms",
                       "n_detections", "n_warnings", "n_points"]
    assert len(rows) == N_FRAMES + 1 and rows[-1][3] == "STOP" and float(rows[-1][4]) > 28
    assert ";" not in r.text and "frames.csv" in r.headers["content-disposition"]


def test_live_sim_wiring(done_run):
    """WS /api/live/sim (resense_web.live) is mounted and replays the worker's run files."""
    client, _settings, _rec, job = done_run
    with client.websocket_connect(f"/api/live/sim?run_id={job['run_id']}&speed=10") as ws:
        first = ws.receive_json()
        second = ws.receive_json()
    assert first["sim"] is True and first["snapshot_kind"] == "frame" and first["pos"] == 0
    assert first["cloud_pos"] == 0 and second["pos"] == 1 and "node" in first
    assert first["decision"] in ("GO", "CAUTION", "STOP", "FAULT")


def test_rename_and_delete(done_run):
    client, settings, rec, job = done_run
    run_id = job["run_id"]
    r = client.patch(f"/api/runs/{run_id}", json={"name": "  Прогон жюри  "})
    assert r.status_code == 200 and r.json()["name"] == "Прогон жюри"
    assert client.patch(f"/api/runs/{run_id}", json={"name": " "}).status_code == 422
    r = client.get(f"{'/api/runs/' + run_id}/download/frames.csv")
    assert "filename*=UTF-8''%D0%9F%D1%80%D0%BE%D0%B3%D0%BE%D0%BD_%D0%B6%D1%8E%D1%80%D0%B8" in \
        r.headers["content-disposition"]
    # deleting the job keeps the run; deleting the recording detaches it
    assert client.delete(f"/api/jobs/{job['id']}").status_code == 204
    assert client.get(f"/api/runs/{run_id}").json()["job_id"] is None
    assert client.delete(f"/api/recordings/{rec['id']}").status_code == 204
    detail = client.get(f"/api/runs/{run_id}").json()
    assert detail["recording_id"] is None and detail["recording"] is None
    assert client.get(f"/api/runs/{run_id}/clouds/0").status_code == 200
    assert client.delete(f"/api/runs/{run_id}").status_code == 204
    assert client.get(f"/api/runs/{run_id}").status_code == 404
    assert not (settings.runs_dir / run_id).exists()
    # no size for a run whose files are gone (and its folder is not brought back)
    assert runs_mod.frames_csv_size(settings, run_id) is None and not (settings.runs_dir / run_id).exists()


def test_npy_folder_and_jsonl_import(client, env, synthetic_clouds):
    """An npy folder (compact arrays, sensor frame) runs through the detector with every/limit; its
    results.jsonl, uploaded back, becomes a run without the detector and without clouds."""
    from resense.pointcloud import COMPACT_DTYPE
    frames = env.server_root / "cache"
    frames.mkdir()
    for i, (xyz, inten, ring) in enumerate(synthetic_clouds):
        a = np.zeros(len(xyz), COMPACT_DTYPE)
        a["x"], a["y"], a["z"] = xyz[:, 0], xyz[:, 1], xyz[:, 2]
        a["intensity"], a["ring"] = inten, ring
        np.save(frames / f"synth_{i:04d}.npy", a)
    rec = client.post("/api/recordings/from-server", json={"path": "cache"}).json()
    assert rec["kind"] == "npy" and rec["n_frames"] == N_FRAMES
    r = client.post("/api/jobs", json={"recording_id": rec["id"],
                                       "options": {"every": 2, "start": 1, "limit": 8, "clouds": False}})
    job = wait_job(client, r.json()["id"])
    assert job["status"] == "done", client.get(f"/api/jobs/{job['id']}/log").text
    assert job["progress"]["frames_total"] == 8
    run = client.get(f"/api/runs/{job['run_id']}").json()
    assert run["has_clouds"] is False and run["cloud_frames"] == 0 and run["source_kind"] == "npy"
    series = client.get(f"/api/runs/{job['run_id']}/series").json()
    assert series["frame"] == [1, 3, 5, 7, 9, 11, 13, 15]
    assert client.get(f"/api/runs/{job['run_id']}/clouds").json()["frames"] == []

    # the downloaded results as a jsonl recording: decisions recomputed, no detector, no clouds
    body = client.get(f"/api/runs/{job['run_id']}/download/results.jsonl").content
    uid = client.post("/api/uploads", json={"name": "импорт"}).json()["upload_id"]
    assert client.put(f"/api/uploads/{uid}/files", params={"path": "r.jsonl"}, content=body).status_code == 200
    jrec = client.post(f"/api/uploads/{uid}/finalize").json()
    assert jrec["kind"] == "jsonl" and jrec["n_frames"] == 8
    job2 = wait_job(client, client.post("/api/jobs", json={"recording_id": jrec["id"]}).json()["id"])
    assert job2["status"] == "done", client.get(f"/api/jobs/{job2['id']}/log").text
    assert job2["options"]["clouds"] is False
    run2 = client.get(f"/api/runs/{job2['run_id']}").json()
    assert run2["source_kind"] == "jsonl" and run2["has_clouds"] is False
    assert run2["summary"]["decisions"] == run["summary"]["decisions"]
    assert run2["summary"]["latency_ms"] == run["summary"]["latency_ms"]
    assert client.get(f"/api/runs/{job2['run_id']}/series").json()["frame"] == series["frame"]


def test_evaluation_with_uploaded_labels(client, env, synthetic_bag):
    """Labels uploaded for a recording are scored after the job (resense_web.evaluation) and
    drive ``labels_in_gauge`` of the series."""
    copy_into_server(env, synthetic_bag)
    rec = client.post("/api/recordings/from-server", json={"path": synthetic_bag.name}).json()
    person = {"distance": 30.0, "lateral": 0.0, "size": [0.4, 0.5, 1.7], "in_gauge": True, "n_points": 50}
    labels = {"_meta": {"bag": rec["name"], "frames": N_FRAMES},
              **{f"{i:05d}": ([person] if i >= 8 else []) for i in range(N_FRAMES)}}
    r = client.put(f"/api/recordings/{rec['id']}/labels", content=json.dumps(labels).encode())
    assert r.status_code == 200, r.text
    assert r.json()["labels"]["source"] == "upload"
    job = wait_job(client, client.post("/api/jobs", json={"recording_id": rec["id"],
                                                          "options": {"clouds": False}}).json()["id"])
    assert job["status"] == "done", client.get(f"/api/jobs/{job['id']}/log").text
    run = client.get(f"/api/runs/{job['run_id']}").json()
    ev = run["summary"]["eval"]
    assert ev is not None, client.get(f"/api/jobs/{job['id']}/log").text
    assert ev["frames_labelled"] == N_FRAMES and ev["frames_with_object_in_gauge"] == 12
    assert ev["frames_detected"] == run["summary"]["counts"]["STOP"] and ev["false_stop_frames"] == 0
    assert 0 < ev["recall"] <= 1 and isinstance(ev["raw"], dict)
    series = client.get(f"/api/runs/{job['run_id']}/series").json()
    assert series["labels_in_gauge"] == [False] * 8 + [True] * 12
    lab = client.get(f"/api/runs/{job['run_id']}/labels").json()
    assert lab["available"] and lab["labels_name"] == ev["labels_name"]
    assert lab["in_gauge"] == series["labels_in_gauge"]
    assert lab["near"] == [None] * 8 + [30.0] * 12 and lab["far"] == [None] * 8 + [30.4] * 12
    scored_run = job["run_id"]
    # evaluate=false: no scores, the chart overlay stays
    job = wait_job(client, client.post("/api/jobs", json={"recording_id": rec["id"], "options": {
        "clouds": False, "evaluate": False, "limit": 10}}).json()["id"])
    assert client.get(f"/api/runs/{job['run_id']}").json()["summary"]["eval"] is None
    assert client.get(f"/api/runs/{job['run_id']}/series").json()["labels_in_gauge"] == [False] * 8 + [True] * 2
    assert client.get(f"/api/runs/{job['run_id']}/labels").json()["near"] == [None] * 8 + [30.0] * 2
    # the uploaded label file goes with its recording: the overlay becomes unavailable, the scores stay
    assert client.delete(f"/api/recordings/{rec['id']}").status_code == 204
    assert client.get(f"/api/runs/{scored_run}/labels").json()["available"] is False
    assert client.get(f"/api/runs/{scored_run}").json()["summary"]["eval"]["frames_detected"] == ev["frames_detected"]


def test_npz_and_plain_array_frames(client, env, synthetic_clouds):
    """Frames as .npz (xyz + intensity) and a plain N x 4 .npy go through the generic reader."""
    frames = env.server_root / "mixed"
    frames.mkdir()
    for i, (xyz, inten, ring) in enumerate(synthetic_clouds[:6]):
        if i < 5:
            np.savez(frames / f"scan_{i:04d}.npz", xyz=xyz, intensity=inten, ring=ring)
        else:
            np.save(frames / f"scan_{i:04d}.npy", np.column_stack([xyz, inten]).astype(np.float32))
    rec = client.post("/api/recordings/from-server", json={"path": "mixed"}).json()
    assert rec["kind"] == "npy" and rec["n_frames"] == 6
    job = wait_job(client, client.post("/api/jobs", json={"recording_id": rec["id"],
                                                          "options": {"cloud_points": 5000}}).json()["id"])
    assert job["status"] == "done", client.get(f"/api/jobs/{job['id']}/log").text
    run = client.get(f"/api/runs/{job['run_id']}").json()
    assert run["summary"]["n_frames"] == 6 and run["cloud_frames"] == 6
    page = client.get(f"/api/runs/{job['run_id']}/frames", params={"count": 6}).json()
    assert [f["frame_id"] for f in page["frames"]] == [f"scan_{i:04d}.npz" for i in range(5)] + ["scan_0005.npy"]
    assert all(f["n_points"] > 20000 for f in page["frames"])
    xyz, _inten, _flags = clouds.unpack_rsc1(client.get(f"/api/runs/{job['run_id']}/clouds/5").content)
    assert len(xyz) >= 5000
