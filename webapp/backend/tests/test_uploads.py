"""Uploads: streamed PUTs into a staging area, finalize (zip / loose bag / folder / jsonl / npy),
path sanitizing, zip-slip and size limits."""
from __future__ import annotations

import dataclasses
import io
import json
import zipfile

import numpy as np
import pytest
from conftest import make_client, random_clouds, write_bag


@pytest.fixture(scope="module")
def tiny_bag(tmp_path_factory):
    return write_bag(tmp_path_factory.mktemp("tiny") / "tiny", random_clouds(3, 1500))


def start_upload(client, name=None) -> str:
    r = client.post("/api/uploads", json={"name": name} if name else None)
    assert r.status_code == 200, r.text
    return r.json()["upload_id"]


def put(client, uid, path, data: bytes):
    return client.put(f"/api/uploads/{uid}/files", params={"path": path}, content=data,
                      headers={"content-type": "application/octet-stream"})


def upload(client, files: dict[str, bytes], name=None):
    uid = start_upload(client, name)
    for path, data in files.items():
        r = put(client, uid, path, data)
        assert r.status_code == 200, r.text
        assert r.json() == {"path": path, "size_bytes": len(data)}
    return uid, client.post(f"/api/uploads/{uid}/finalize")


def bag_files(bag, prefix=""):
    return {f"{prefix}{p.name}": p.read_bytes() for p in sorted(bag.iterdir())}


def zip_bytes(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in members.items():
            zf.writestr(name, data)
    return buf.getvalue()


def result_lines(n=5):
    return "".join(json.dumps({"stamp": 100.0 + 0.1 * i, "obstacle": i >= 3, "warning": False,
                               "nearest_distance": 40.0 if i >= 3 else None, "detections": [], "warnings": [],
                               "n_points": 1000, "clear_distance": 90.0, "timing_ms": {"total": 20.0 + i},
                               "health": {"level": "ok", "decision_level": "ok", "visibility": 120.0},
                               "frame": 10 + i}) + "\n" for i in range(n)).encode()


def test_zip_of_a_rosbag_folder(client, env, tiny_bag):
    data = zip_bytes({f"tiny/{k}": v for k, v in bag_files(tiny_bag).items()})
    uid, r = upload(client, {"tiny.zip": data})
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["kind"] == "rosbag2" and rec["source"] == "upload" and rec["name"] == "tiny"
    assert rec["n_frames"] == 3 and rec["default_topic"] == "/lidar_points"
    assert rec["topics"] == [{"name": "/lidar_points", "type": "sensor_msgs/msg/PointCloud2", "count": 3}]
    assert rec["duration_s"] == pytest.approx(0.2, abs=0.01)
    assert rec["path"].startswith(str(env.recordings_dir)) and rec["size_bytes"] > 0
    assert rec["labels"] == {"available": False, "source": None, "name": None}
    assert not (env.uploads_dir / uid).exists()
    assert [x["id"] for x in client.get("/api/recordings").json()] == [rec["id"]]
    assert client.get(f"/api/recordings/{rec['id']}").json()["name"] == "tiny"


def test_loose_bag_files_and_a_given_name(client, tiny_bag):
    _, r = upload(client, bag_files(tiny_bag))
    assert r.status_code == 201, r.text
    assert r.json()["name"] == "tiny" and r.json()["kind"] == "rosbag2"
    _, r = upload(client, bag_files(tiny_bag, "folder/"), name="Мой бэг")
    assert r.status_code == 201 and r.json()["name"] == "Мой бэг"


def test_lone_db3_without_metadata(client, tiny_bag):
    _, r = upload(client, {"tiny_0.db3": (tiny_bag / "tiny_0.db3").read_bytes()})
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["kind"] == "rosbag2" and rec["n_frames"] == 3 and rec["name"] == "tiny"
    assert any("metadata.yaml" in w for w in rec["warnings"])


def test_results_jsonl(client):
    _, r = upload(client, {"run.jsonl": b"---\n" + result_lines(5)})
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["kind"] == "jsonl" and rec["n_frames"] == 5 and rec["name"] == "run"
    assert rec["duration_s"] == pytest.approx(0.4) and rec["default_topic"] is None
    _, r = upload(client, {"bad.jsonl": b'{"a": 1}\n'})
    assert r.status_code == 422 and "obstacle" in r.json()["detail"]


def _npy(i, n=500):
    from resense.pointcloud import COMPACT_DTYPE
    a = np.zeros(n, COMPACT_DTYPE)
    a["x"] = np.linspace(1, 50, n)
    a["ring"] = i % 128
    buf = io.BytesIO()
    np.save(buf, a)
    return buf.getvalue()


def _npz(n=500):
    buf = io.BytesIO()
    np.savez(buf, xyz=np.random.default_rng(0).normal(size=(n, 3)).astype(np.float32), intensity=np.ones(n))
    return buf.getvalue()


def test_npy_and_npz_folders(client):
    _, r = upload(client, {f"cache/scan_{i:04d}.npy": _npy(i) for i in range(4)})
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["kind"] == "npy" and rec["n_frames"] == 4 and rec["name"] == "cache"
    assert rec["duration_s"] == pytest.approx(0.3)
    _, r = upload(client, {"frames.zip": zip_bytes({f"f{i}.npz": _npz() for i in range(3)})})
    assert r.status_code == 201, r.text
    assert r.json()["kind"] == "npy" and r.json()["n_frames"] == 3


@pytest.mark.parametrize("path", ["../evil", "/etc/x", "a\\b", "a/../../b", "a\x00b", ""])
def test_put_rejects_unsafe_paths(client, env, path):
    uid = start_upload(client)
    r = put(client, uid, path, b"x")
    assert r.status_code == 422, r.text
    assert isinstance(r.json()["detail"], str)
    assert not any(p.is_file() for p in (env.uploads_dir / uid / "files").rglob("*"))


def test_zip_slip_is_rejected(client, env, tmp_path):
    uid, r = upload(client, {"evil.zip": zip_bytes({"ok/metadata.yaml": b"x", "../../escaped.txt": b"pwned"})})
    assert r.status_code == 422
    assert "недопустимый путь" in r.json()["detail"]
    assert not list(env.data_dir.rglob("escaped.txt")) and not list(tmp_path.rglob("escaped.txt"))


def test_nothing_usable_keeps_staging_then_abort(client, env):
    uid, r = upload(client, {"readme.txt": b"hello"})
    assert r.status_code == 422 and "не найдено" in r.json()["detail"]
    assert (env.uploads_dir / uid).is_dir()
    assert client.delete(f"/api/uploads/{uid}").status_code == 204
    assert not (env.uploads_dir / uid).exists()
    assert put(client, uid, "x.bin", b"1").status_code == 404
    assert client.post("/api/uploads/nosuchupload/finalize").status_code == 404
    assert client.post("/api/uploads/../x/finalize").status_code in (404, 405)


def test_empty_upload_and_replacing_a_file(client):
    uid = start_upload(client)
    assert client.post(f"/api/uploads/{uid}/finalize").status_code == 422
    assert put(client, uid, "a/run.jsonl", b"junk").status_code == 200
    assert put(client, uid, "a/run.jsonl", result_lines(2)).status_code == 200      # replaced
    assert put(client, uid, "a/run.jsonl/x", b"1").status_code == 409               # file in the way
    r = client.post(f"/api/uploads/{uid}/finalize")
    assert r.status_code == 201 and r.json()["n_frames"] == 2


def test_size_limits(env):
    small = dataclasses.replace(env, max_upload_bytes=10_000)
    with make_client(small) as client:
        uid = start_upload(client)
        assert put(client, uid, "a.bin", b"0" * 6000).status_code == 200
        r = put(client, uid, "b.bin", b"0" * 6000)                  # 12 000 > 10 000 in total
        assert r.status_code == 413 and "ГБ" in r.json()["detail"]
        files = list((small.uploads_dir / uid / "files").iterdir())
        assert [p.name for p in files] == ["a.bin"]                 # no partial file left behind
        assert put(client, uid, "c.bin", b"0" * 3000).status_code == 200
        # a zip that inflates beyond the limit (zip-bomb guard)
        uid2 = start_upload(client)
        assert put(client, uid2, "bomb.zip", zip_bytes({"big/zero.npy": b"\0" * 200_000})).status_code == 200
        r = client.post(f"/api/uploads/{uid2}/finalize")
        assert r.status_code == 422 and "распаковки" in r.json()["detail"]


def test_mcap_bag(client, tmp_path):
    """rosbag2 with mcap storage (probed through rosbags), topic chosen among several."""
    import importlib.util

    from rosbags.rosbag2 import StoragePlugin, Writer
    from rosbags.typesys import Stores, get_typestore
    from conftest import SMOKE_SCRIPT
    spec = importlib.util.spec_from_file_location("smoke_for_mcap", SMOKE_SCRIPT)
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    ts = get_typestore(Stores.ROS2_HUMBLE)
    rng = np.random.default_rng(0)
    bag = tmp_path / "ride"
    with Writer(bag, version=9, storage_plugin=StoragePlugin.MCAP) as w:
        a = w.add_connection("/cloud_a", "sensor_msgs/msg/PointCloud2", typestore=ts)
        b = w.add_connection("/cloud_b", "sensor_msgs/msg/PointCloud2", typestore=ts)
        for i, (xyz, it, ring) in enumerate(random_clouds(5, 300)):
            stamp = 10 ** 18 + i * 10 ** 8
            w.write(a, stamp, smoke.make_message(ts, xyz, it, ring, stamp, 0.1 * i, rng))
            if i < 2:
                w.write(b, stamp, smoke.make_message(ts, xyz, it, ring, stamp, 0.1 * i, rng))
    _, r = upload(client, {"ride.zip": zip_bytes({f"ride/{p.name}": p.read_bytes() for p in bag.iterdir()})})
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["kind"] == "rosbag2" and rec["default_topic"] == "/cloud_a" and rec["n_frames"] == 5
    assert [t["count"] for t in rec["topics"]] == [5, 2]
    assert any("несколько топиков" in w for w in rec["warnings"])
    r = client.post("/api/jobs", json={"recording_id": rec["id"], "options": {"topic": "/cloud_b"}})
    assert r.status_code == 201 and r.json()["progress"]["frames_total"] == 2


def test_zip_with_conflicting_members(client):
    _, r = upload(client, {"odd.zip": zip_bytes({"a": b"file", "a/b.jsonl": result_lines(1)})})
    assert r.status_code == 422 and "конфликтующие" in r.json()["detail"]
