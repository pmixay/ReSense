"""The «Папка на сервере» browser (sandboxed to RESENSE_DATA), registration in place, recording
removal and labels."""
from __future__ import annotations

import io
import json
import os
import re
import shutil
import zipfile

import numpy as np
import pytest
from conftest import random_clouds, write_bag


@pytest.fixture
def server_tree(env, tmp_path):
    root = env.server_root
    write_bag(root / "bags" / "tiny", random_clouds(4, 1000))
    (root / "bags" / "notes.txt").write_text("x")
    (root / "bags" / ".hidden").mkdir()
    frames = root / "cache"
    frames.mkdir()
    from resense.pointcloud import COMPACT_DTYPE
    for i in range(3):
        a = np.zeros(300, COMPACT_DTYPE)
        a["x"] = np.linspace(1, 30, 300)
        np.save(frames / f"cache_{i * 5:04d}.npy", a)
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret")
    os.symlink(outside, root / "escape")
    os.symlink(outside / "secret.txt", root / "bags" / "secret_link.txt")
    return root


def test_listing(client, server_tree):
    r = client.get("/api/server-files")
    assert r.status_code == 200, r.text
    top = r.json()
    assert top["path"] == "" and top["parent"] is None
    names = [e["name"] for e in top["entries"]]
    assert names == ["bags", "cache"]                       # the symlink out of the root is hidden
    cache = next(e for e in top["entries"] if e["name"] == "cache")
    assert cache["is_npy_dir"] and cache["n_frames"] == 3 and cache["type"] == "dir"
    bags = client.get("/api/server-files", params={"path": "bags"}).json()
    assert bags["parent"] == "" and bags["path"] == "bags"
    tiny = next(e for e in bags["entries"] if e["name"] == "tiny")
    assert tiny["is_bag"] and tiny["n_frames"] == 4 and tiny["path"] == "bags/tiny" and tiny["size_bytes"] > 0
    assert [e["name"] for e in bags["entries"]] == ["tiny", "notes.txt"]
    inner = client.get("/api/server-files", params={"path": "bags/tiny"}).json()
    assert inner["parent"] == "bags"
    assert {e["name"] for e in inner["entries"]} == {"metadata.yaml", "tiny_0.db3"}


@pytest.mark.parametrize("path,status", [
    ("..", 400), ("../", 400), ("bags/../..", 400), ("/etc", 400), ("escape", 403), ("escape/", 403),
    ("bags/secret_link.txt", 403), ("nope", 404), ("bags\\tiny", 400), ("bags/notes.txt", 400),
])
def test_listing_sandbox(client, server_tree, path, status):
    r = client.get("/api/server-files", params={"path": path})
    assert r.status_code == status, r.text
    assert "secret" not in r.text


def test_missing_server_root(client, env):
    os.rmdir(env.server_root)
    r = client.get("/api/server-files")
    assert r.status_code == 404 and "не найдена" in r.json()["detail"]
    assert client.get("/api/system").json()["server_root_exists"] is False


def test_register_in_place(client, server_tree, env):
    r = client.post("/api/recordings/from-server", json={"path": "bags/tiny"})
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["source"] == "server" and rec["kind"] == "rosbag2" and rec["n_frames"] == 4
    assert rec["path"] == str((server_tree / "bags" / "tiny").resolve()) and rec["name"] == "tiny"
    # the same folder again (or via its metadata.yaml) returns the same recording
    r = client.post("/api/recordings/from-server", json={"path": "bags/tiny/metadata.yaml"})
    assert r.status_code == 200 and r.json()["id"] == rec["id"]
    npy = client.post("/api/recordings/from-server", json={"path": "cache"}).json()
    assert npy["kind"] == "npy" and npy["n_frames"] == 3 and npy["duration_s"] == pytest.approx(1.0)
    for bad, status in (("escape", 403), ("../x", 400), ("bags/notes.txt", 422), ("bags", 422)):
        r = client.post("/api/recordings/from-server", json={"path": bad})
        assert r.status_code == status, (bad, r.text)
    # deleting a server recording never touches the server folder
    assert client.delete(f"/api/recordings/{rec['id']}").status_code == 204
    assert (server_tree / "bags" / "tiny" / "metadata.yaml").is_file()
    assert client.get(f"/api/recordings/{rec['id']}").status_code == 404
    assert client.delete(f"/api/recordings/{rec['id']}").status_code == 404


def test_labels_upload_and_delete(client, server_tree, env):
    """Labels go through the real validator (resense_web.evaluation); deleting uploaded labels
    falls back to the repository's built-in labels matched by the recording name."""
    rec = client.post("/api/recordings/from-server", json={"path": "bags/tiny"}).json()
    assert rec["labels"] == {"available": False, "source": None, "name": None}
    labels = {"_meta": {"bag": "tiny", "frames": 4}, "00001": [{"distance": 12.0, "lateral": 0.1, "in_gauge": True}]}
    r = client.put(f"/api/recordings/{rec['id']}/labels", content=json.dumps(labels).encode())
    assert r.status_code == 200, r.text
    assert r.json()["labels"] == {"available": True, "source": "upload", "name": "tiny"}
    assert (env.recordings_dir / rec["id"] / "labels.json").is_file()
    assert not (server_tree / "bags" / "tiny" / "labels.json").exists()    # never written into the server folder
    r = client.put(f"/api/recordings/{rec['id']}/labels", content=b"{not json")
    assert r.status_code == 422 and "JSON" in r.json()["detail"]
    for bad in (b'{"frame_1": []}', b'{"00001": [{"lateral": 0.1}]}', b"{}", b"[1, 2]"):
        r = client.put(f"/api/recordings/{rec['id']}/labels", content=bad)
        assert r.status_code == 422 and re.search("[а-яА-Я]", r.json()["detail"]), (bad, r.text)
    r = client.delete(f"/api/recordings/{rec['id']}/labels")
    assert r.status_code == 200 and r.json()["labels"] == {"available": False, "source": None, "name": None}

    # a bag named like an organizers' recording gets the built-in labels/<name>.json
    shutil.copytree(server_tree / "bags" / "tiny", server_tree / "doubleT_obstacle")
    rec2 = client.post("/api/recordings/from-server", json={"path": "doubleT_obstacle"}).json()
    assert rec2["labels"] == {"available": True, "source": "builtin", "name": "doubleT_obstacle"}
    r = client.put(f"/api/recordings/{rec2['id']}/labels", content=json.dumps(labels).encode())
    assert r.json()["labels"]["source"] == "upload"
    r = client.delete(f"/api/recordings/{rec2['id']}/labels")
    assert r.status_code == 200 and r.json()["labels"] == {"available": True, "source": "builtin",
                                                          "name": "doubleT_obstacle"}


def test_system_and_health(client, env):
    assert client.get("/api/health").json() == {"ok": True}
    s = client.get("/api/system").json()
    assert s["detector_version"] == "1.0.0" and s["data_dir"] == str(env.data_dir)
    assert s["server_root_exists"] is True and s["cpu_count"] >= 1 and s["disk_free_bytes"] > 0
    assert set(s["features"]) == {"rosbags", "open3d", "native_kernels", "clouds"} and s["features"]["rosbags"]
    assert s["counts"] == {"recordings": 0, "runs": 0, "jobs_queued": 0, "jobs_running": 0}
    assert client.get("/api/nope").status_code == 404
    assert client.get("/api/nope").json()["detail"] == "Не найдено"


def test_demo_recording(client, env):
    """POST /api/recordings/demo with the real generator (resense_web.demo): a rosbag2 bag with
    its ground truth as built-in labels, downloadable as a zip, removed with the recording."""
    r = client.post("/api/recordings/demo", json={"scenario": "crossing", "seconds": 5, "seed": 3})
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["source"] == "demo" and rec["kind"] == "rosbag2" and rec["n_frames"] == 50
    assert rec["duration_s"] == pytest.approx(4.9, abs=0.01)
    assert rec["name"] == "demo_crossing" and rec["path"].startswith(str(env.recordings_dir))
    assert rec["default_topic"] == "/lidar_points" and rec["warnings"] == []
    assert rec["topics"] == [{"name": "/lidar_points", "type": "sensor_msgs/msg/PointCloud2", "count": 50}]
    assert rec["labels"] == {"available": True, "source": "builtin", "name": "demo_crossing (эталон демо)"}
    z = client.get(f"/api/recordings/{rec['id']}/download")
    assert z.status_code == 200 and z.headers["content-type"] == "application/zip" and z.content[:2] == b"PK"
    assert "content-encoding" not in z.headers
    names = zipfile.ZipFile(io.BytesIO(z.content)).namelist()
    assert sorted(names) == ["demo_crossing/demo_crossing_0.db3", "demo_crossing/ground_truth.json",
                             "demo_crossing/metadata.yaml"]
    assert client.get(f"/api/recordings/{rec['id']}/download").status_code == 200    # cached zip
    for bad in ({"scenario": "nope"}, {"seconds": 1}, {"seconds": 61}, {"seed": -1}):
        r = client.post("/api/recordings/demo", json=bad)
        assert r.status_code == 422 and re.search("[а-яА-Я]", r.json()["detail"]), (bad, r.text)
    assert client.delete(f"/api/recordings/{rec['id']}").status_code == 204
    assert not (env.recordings_dir / rec["id"]).exists() and not list(env.cache_dir.iterdir())
    server_rec = client.post("/api/recordings/from-server", json={"path": "."})
    assert server_rec.status_code == 422
