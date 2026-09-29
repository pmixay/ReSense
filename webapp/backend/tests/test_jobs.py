"""The job queue: validation, queue order, cancel (queued and running), retry, delete, restart
recovery, and a worker failure. The full detector path is in test_runs.py."""
from __future__ import annotations

import os
import sqlite3
import time

import numpy as np
import pytest
from conftest import make_client, random_clouds, sleeper_command, wait_job, write_bag


def _register_tiny(client, env, name="tiny", n=3):
    write_bag(env.server_root / name, random_clouds(n, 800))
    r = client.post("/api/recordings/from-server", json={"path": name})
    assert r.status_code == 201, r.text
    return r.json()


def _wait_status(client, job_id, status, timeout=15.0):
    t_end = time.monotonic() + timeout
    while time.monotonic() < t_end:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] == status:
            return job
        time.sleep(0.05)
    raise AssertionError(f"job {job_id} never became {status}: {job}")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:   # a zombie (not yet reaped by its parent) counts as dead
        with open(f"/proc/{pid}/stat") as fh:
            return fh.read().split(")")[-1].split()[0] != "Z"
    except OSError:
        return False


def test_create_validation(client, env):
    rec = _register_tiny(client, env)
    r = client.post("/api/jobs", json={"recording_id": "nosuchrec"})
    assert r.status_code == 404 and r.json()["detail"] == "Запись не найдена"
    r = client.post("/api/jobs", json={"recording_id": rec["id"], "preset_id": "nosuch"})
    assert r.status_code == 404 and "Набор" in r.json()["detail"]
    r = client.post("/api/jobs", json={"recording_id": rec["id"], "options": {"every": 0}})
    assert r.status_code == 422 and "every" in r.json()["detail"] and "не меньше 1" in r.json()["detail"]
    r = client.post("/api/jobs", json={"recording_id": rec["id"], "options": {"cloud_points": 10}})
    assert r.status_code == 422 and "cloud_points" in r.json()["detail"]
    r = client.post("/api/jobs", json={"recording_id": rec["id"], "options": {"bogus": 1}})
    assert r.status_code == 422 and "неизвестное поле" in r.json()["detail"]
    r = client.post("/api/jobs", json={"recording_id": rec["id"], "options": {"topic": "/nope"}})
    assert r.status_code == 422 and "/nope" in r.json()["detail"]
    r = client.post("/api/jobs", json={"recording_id": rec["id"], "options": {"start": 3}})
    assert r.status_code == 422 and "за пределами" in r.json()["detail"]
    assert client.get("/api/jobs", params={"status": "weird"}).status_code == 422
    assert client.get("/api/jobs/nosuch").status_code == 404
    assert client.delete("/api/jobs").status_code == 422


def test_queue_order_cancel_retry_delete(env):
    with make_client(env, worker_command=sleeper_command(60)) as client:
        rec = _register_tiny(client, env)
        ids = [client.post("/api/jobs", json={"recording_id": rec["id"],
                                              "options": {"every": 2, "limit": 5 if i == 2 else None}}).json()["id"]
               for i in range(3)]
        first = _wait_status(client, ids[0], "running")
        assert first["position"] is None and first["progress"]["stage"] in ("opening", "processing")
        jobs = client.get("/api/jobs").json()
        assert [j["id"] for j in jobs] == ids
        assert [j["position"] for j in jobs] == [None, 1, 2]
        assert jobs[1]["progress"] == {"frames_done": 0, "frames_total": 2, "fps": None, "eta_s": None,
                                       "stage": "queued", "stage_ms": {}, "decisions": "", "last": None}
        assert jobs[1]["options"] == {"topic": None, "every": 2, "start": 0, "limit": None, "clouds": True,
                                      "cloud_points": 30000, "ego_speed": None, "evaluate": True}
        assert [j["id"] for j in client.get("/api/jobs", params={"status": "queued"}).json()] == ids[1:]

        # cancel a queued job: it leaves the queue, the next one moves up
        r = client.post(f"/api/jobs/{ids[1]}/cancel")
        assert r.status_code == 200 and r.json()["status"] == "cancelled" and r.json()["finished_at"]
        assert client.get(f"/api/jobs/{ids[2]}").json()["position"] == 1
        assert client.post(f"/api/jobs/{ids[1]}/cancel").status_code == 409
        assert client.delete(f"/api/jobs/{ids[0]}").status_code == 409      # still running

        # cancel the running job: its process group dies, its partial run folder goes, the queue moves on
        db = client.app.state.ctx.db
        row = db.one("SELECT pid, run_id FROM jobs WHERE id = ?", (ids[0],))
        assert _pid_alive(row["pid"]) and (env.runs_dir / row["run_id"]).is_dir()
        r = client.post(f"/api/jobs/{ids[0]}/cancel")
        assert r.json()["status"] == "cancelled" and r.json()["run_id"] is None
        _wait_status(client, ids[2], "running")
        assert not _pid_alive(row["pid"])
        assert not (env.runs_dir / row["run_id"]).exists()

        # retry = a new queued job with the same recording / preset / options
        r = client.post(f"/api/jobs/{ids[1]}/retry")
        assert r.status_code == 201, r.text
        retry = r.json()
        assert retry["id"] not in ids and retry["status"] == "queued" and retry["options"]["every"] == 2
        assert client.post(f"/api/jobs/{ids[2]}/retry").status_code == 409     # not finished yet

        # finished jobs can be deleted one by one or all at once; running ones cannot
        assert client.delete(f"/api/jobs/{ids[1]}").status_code == 204
        assert client.get(f"/api/jobs/{ids[1]}").status_code == 404
        assert client.delete("/api/jobs", params={"finished": "true"}).status_code == 204
        left = [j["id"] for j in client.get("/api/jobs").json()]
        assert left == [ids[2], retry["id"]]
        assert isinstance(client.get(f"/api/jobs/{ids[2]}/log").text, str)
        sysinfo = client.get("/api/system").json()["counts"]
        assert sysinfo["jobs_running"] == 1 and sysinfo["jobs_queued"] == 1

        # a recording with a running job cannot be deleted; its queued jobs are cancelled on delete
        assert client.delete(f"/api/recordings/{rec['id']}").status_code == 409


def test_restart_recovery(env):
    with make_client(env, worker_command=sleeper_command(60)) as client:
        rec = _register_tiny(client, env)
        a = client.post("/api/jobs", json={"recording_id": rec["id"]}).json()["id"]
        b = client.post("/api/jobs", json={"recording_id": rec["id"]}).json()["id"]
        _wait_status(client, a, "running")
        run_a = client.app.state.ctx.db.one("SELECT run_id FROM jobs WHERE id = ?", (a,))["run_id"]
    # a graceful shutdown fails the running job too; the queued one stays queued
    con = sqlite3.connect(env.db_path)
    assert con.execute("SELECT status, error FROM jobs WHERE id = ?", (a,)).fetchone() == \
        ("failed", "прервано перезапуском сервера")
    assert con.execute("SELECT status FROM jobs WHERE id = ?", (b,)).fetchone() == ("queued",)
    # simulate a crash: the database still says "running" and a partial run folder is left
    con.execute("UPDATE jobs SET status = 'running', error = NULL, finished_at = NULL, pid = NULL WHERE id = ?", (a,))
    con.commit()
    con.close()
    (env.runs_dir / run_a).mkdir(parents=True, exist_ok=True)
    (env.runs_dir / run_a / "results.jsonl").write_text("{}\n")
    with make_client(env, worker_command=sleeper_command(60)) as client:
        job_a = client.get(f"/api/jobs/{a}").json()
        assert job_a["status"] == "failed" and job_a["error"] == "прервано перезапуском сервера"
        assert not (env.runs_dir / run_a).exists()
        _wait_status(client, b, "running")        # the queue continues


def test_worker_failure_is_reported(client, env):
    frames = env.server_root / "frames"
    frames.mkdir()
    from resense.pointcloud import COMPACT_DTYPE
    for i in range(2):
        np.save(frames / f"f_{i}.npy", np.zeros(10, COMPACT_DTYPE))
    rec = client.post("/api/recordings/from-server", json={"path": "frames"}).json()
    for f in frames.iterdir():
        f.unlink()
    job = wait_job(client, client.post("/api/jobs", json={"recording_id": rec["id"]}).json()["id"])
    assert job["status"] == "failed" and job["run_id"] is None
    assert job["error"] == "Не прочитано ни одного кадра — проверьте топик и диапазон кадров"
    log = client.get(f"/api/jobs/{job['id']}/log")
    assert log.status_code == 200 and log.headers["content-type"].startswith("text/plain")
    assert "Traceback" in log.text and "WorkerError" in log.text
    assert client.get("/api/runs").json() == []
    assert list(env.runs_dir.iterdir()) == []
    # a missing bag: the worker fails with a short Russian message
    bag = write_bag(env.server_root / "gone", random_clouds(2, 500))
    rec2 = client.post("/api/recordings/from-server", json={"path": "gone"}).json()
    for f in bag.iterdir():
        f.unlink()
    job = wait_job(client, client.post("/api/jobs", json={"recording_id": rec2["id"]}).json()["id"])
    assert job["status"] == "failed" and job["error"] and job["error"][0].isupper()
    assert all(ord(c) < 128 or "а" <= c.lower() <= "я" or c in "ё—«»№" for c in job["error"])


@pytest.mark.parametrize("n_frames,expected", [(10, 10), (None, None)])
def test_frames_total(n_frames, expected):
    from resense_web.jobs import frames_total
    assert frames_total(n_frames, {"start": 0, "every": 1}) == expected
    if n_frames:
        assert frames_total(n_frames, {"start": 3, "every": 2}) == 4
        assert frames_total(n_frames, {"start": 3, "every": 2, "limit": 2}) == 2
