"""Resumable uploads: chunked files (CRC-32, gzip transfer encoding, any order, resume after a
restart), the upload status, finalize in the background (progress, joining, races with writes and
delete), whole-file PUTs with checks, stale cleanup."""
from __future__ import annotations

import dataclasses
import gzip
import io
import os
import threading
import time
import zipfile
import zlib
from pathlib import PurePosixPath

import pytest
from conftest import make_client, random_clouds, write_bag

CHUNK = 64 * 1024


@pytest.fixture(scope="module")
def tiny_bag(tmp_path_factory):
    return write_bag(tmp_path_factory.mktemp("tiny_chunked") / "tiny", random_clouds(3, 6000))


def start(client, name=None) -> str:
    r = client.post("/api/uploads", json={"name": name} if name else None)
    assert r.status_code == 200, r.text
    return r.json()["upload_id"]


def declare(client, uid, path, size, chunk=CHUNK, fingerprint="fp"):
    return client.post(f"/api/uploads/{uid}/chunked",
                       json={"path": path, "size_bytes": size, "chunk_size": chunk, "fingerprint": fingerprint})


def send(client, uid, path, index, raw: bytes, *, crc=True, gz=False, body=None):
    headers = {"content-type": "application/octet-stream"}
    if crc:
        headers["X-Content-CRC32"] = f"{zlib.crc32(raw):08x}"
    if gz:
        headers["X-Content-Encoding"] = "gzip"
    data = body if body is not None else (gzip.compress(raw) if gz else raw)
    return client.put(f"/api/uploads/{uid}/chunked/{index}", params={"path": path}, content=data, headers=headers)


def chunks(data: bytes, size=CHUNK):
    return [data[i:i + size] for i in range(0, len(data), size)]


def upload_chunked(client, uid, path, data, order=None, gz_every=2):
    assert declare(client, uid, path, len(data)).status_code == 200
    parts = chunks(data)
    for i in (order if order is not None else range(len(parts))):
        r = send(client, uid, path, i, parts[i], gz=(i % gz_every == 0))
        assert r.status_code == 200, r.text
    return r.json()


def wait_status(client, uid, state, timeout=30.0):
    t_end = time.monotonic() + timeout
    while True:
        st = client.get(f"/api/uploads/{uid}").json()
        if st.get("state") == state or (state == "failed" and st.get("error")):
            return st
        assert time.monotonic() < t_end, st
        time.sleep(0.05)


def test_chunked_bag_out_of_order_with_gzip(client, env, tiny_bag):
    uid = start(client)
    db3 = (tiny_bag / "tiny_0.db3").read_bytes()
    assert len(db3) > 3 * CHUNK
    r = declare(client, uid, "tiny/tiny_0.db3", len(db3))
    assert r.status_code == 200, r.text
    st = r.json()
    n = -(-len(db3) // CHUNK)
    assert st == {"path": "tiny/tiny_0.db3", "size_bytes": len(db3), "chunk_size": CHUNK, "n_chunks": n,
                  "received_chunks": 0, "received_bytes": 0, "complete": False, "missing": [[0, n - 1]]}
    parts = chunks(db3)
    order = list(range(n))[::-1]                  # last chunk (short) first
    for k, i in enumerate(order[:-1]):
        r = send(client, uid, "tiny/tiny_0.db3", i, parts[i], gz=(k % 2 == 0))
        assert r.status_code == 200, r.text
        assert r.json()["received_chunks"] == k + 1 and not r.json()["complete"]
    status = client.get(f"/api/uploads/{uid}").json()
    assert status["state"] == "receiving" and status["files"] == []
    assert status["partial"][0]["missing"] == [[0, 0]]
    assert status["bytes_received"] == len(db3) - len(parts[0])
    # finalize refuses while a part is missing
    r = client.post(f"/api/uploads/{uid}/finalize")
    assert r.status_code == 409 and "tiny/tiny_0.db3" in r.json()["detail"]
    r = send(client, uid, "tiny/tiny_0.db3", 0, parts[0])
    assert r.status_code == 200 and r.json()["complete"] and r.json()["received_bytes"] == len(db3)
    meta = (tiny_bag / "metadata.yaml").read_bytes()
    assert client.put(f"/api/uploads/{uid}/files", params={"path": "tiny/metadata.yaml", "size": len(meta)},
                      content=meta, headers={"X-Content-CRC32": f"{zlib.crc32(meta):08x}"}).status_code == 200
    status = client.get(f"/api/uploads/{uid}").json()
    assert sorted(status["files"], key=lambda f: f["path"]) == [
        {"path": "tiny/metadata.yaml", "size_bytes": len(meta)}, {"path": "tiny/tiny_0.db3", "size_bytes": len(db3)}]
    assert status["partial"] == [] and status["bytes_received"] == len(db3) + len(meta)
    r = client.post(f"/api/uploads/{uid}/finalize")
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["kind"] == "rosbag2" and rec["n_frames"] == 3 and rec["name"] == "tiny"
    from pathlib import Path
    assert Path(rec["path"], "tiny_0.db3").read_bytes() == db3
    assert not (env.uploads_dir / uid).exists()
    done = client.get(f"/api/uploads/{uid}").json()            # the outcome stays readable
    assert done["state"] == "done" and done["recording"]["id"] == rec["id"]
    assert client.post(f"/api/uploads/{uid}/finalize").json()["id"] == rec["id"]   # a repeated call joins


def test_resume_after_a_restart_and_a_changed_file(env):
    data = os.urandom(5 * CHUNK + 123)
    parts = chunks(data)
    with make_client(env) as client:
        uid = start(client)
        assert declare(client, uid, "big.bin", len(data)).status_code == 200
        for i in (0, 1, 3):
            assert send(client, uid, "big.bin", i, parts[i]).status_code == 200
    with make_client(env) as client:                           # a new server process on the same data
        st = client.get(f"/api/uploads/{uid}").json()
        assert st["partial"][0]["missing"] == [[2, 2], [4, 5]]
        assert st["bytes_received"] == 3 * CHUNK
        r = declare(client, uid, "big.bin", len(data))        # same file: resumes
        assert r.json()["missing"] == [[2, 2], [4, 5]] and r.json()["received_chunks"] == 3
        r = send(client, uid, "big.bin", 1, parts[1])          # a received chunk again: no-op
        assert r.status_code == 200 and r.json()["received_chunks"] == 3
        for i in (2, 4, 5):
            assert send(client, uid, "big.bin", i, parts[i], gz=True).status_code == 200
        assert (env.uploads_dir / uid / "files" / "big.bin").read_bytes() == data
        # declaring the finished file again resumes as complete; another fingerprint starts over
        assert declare(client, uid, "big.bin", len(data)).json()["complete"]
        r = declare(client, uid, "big.bin", len(data), fingerprint="other")
        assert r.json()["missing"] == [[0, 5]] and not (env.uploads_dir / uid / "files" / "big.bin").exists()
        r = declare(client, uid, "big.bin", len(data) + 1, fingerprint="other")
        assert r.json()["received_chunks"] == 0 and r.json()["size_bytes"] == len(data) + 1


def test_corrupted_and_invalid_chunks(client, env):
    uid = start(client)
    data = os.urandom(2 * CHUNK + 10)
    parts = chunks(data)
    assert declare(client, uid, "a.bin", len(data)).status_code == 200
    bad = bytearray(parts[0])
    bad[100] ^= 0xFF
    r = send(client, uid, "a.bin", 0, parts[0], body=bytes(bad))          # CRC of the good bytes
    assert r.status_code == 400 and "Контрольная сумма" in r.json()["detail"]
    r = send(client, uid, "a.bin", 0, parts[0], body=parts[0][:-5])       # truncated
    assert r.status_code == 400 and "не полностью" in r.json()["detail"]
    r = send(client, uid, "a.bin", 0, parts[0], gz=True, body=gzip.compress(parts[0])[:-4])
    assert r.status_code == 400 and "gzip" in r.json()["detail"]
    r = send(client, uid, "a.bin", 0, parts[0], body=parts[0] + b"x")     # longer than the chunk
    assert r.status_code == 413
    bomb = gzip.compress(b"\0" * (4 * CHUNK))                              # inflates beyond the chunk
    r = send(client, uid, "a.bin", 0, parts[0], gz=True, body=bomb)
    assert r.status_code == 400
    assert send(client, uid, "a.bin", 3, b"x").status_code == 422           # beyond the file
    assert send(client, uid, "nope.bin", 0, parts[0]).status_code == 404    # not declared
    r = client.put(f"/api/uploads/{uid}/chunked/0", params={"path": "a.bin"}, content=parts[0],
                   headers={"X-Content-CRC32": "zz"})
    assert r.status_code == 422
    r = client.put(f"/api/uploads/{uid}/chunked/0", params={"path": "a.bin"}, content=parts[0],
                   headers={"X-Content-Encoding": "br"})
    assert r.status_code == 422
    assert client.get(f"/api/uploads/{uid}").json()["partial"][0]["received_chunks"] == 0
    assert send(client, uid, "a.bin", 2, parts[2], crc=False).status_code == 200   # CRC is optional
    # declarations: chunk size bounds, unsafe paths, a path under an existing file
    assert declare(client, uid, "b.bin", 10, chunk=1000).status_code == 422
    assert declare(client, uid, "../b.bin", 10).status_code == 422
    assert client.put(f"/api/uploads/{uid}/files", params={"path": "f"}, content=b"1").status_code == 200
    assert declare(client, uid, "f/inner.bin", 10).status_code == 409


def test_zero_size_file_and_limits(env, monkeypatch):
    small = dataclasses.replace(env, max_upload_bytes=4 * CHUNK)
    with make_client(small) as client:
        uid = start(client)
        r = declare(client, uid, "empty.bin", 0)
        assert r.status_code == 200 and r.json()["complete"] and r.json()["n_chunks"] == 0
        assert (small.uploads_dir / uid / "files" / "empty.bin").is_file()
        r = declare(client, uid, "big.bin", 5 * CHUNK)
        assert r.status_code == 413 and "ГБ" in r.json()["detail"]
        assert declare(client, uid, "ok.bin", 3 * CHUNK).status_code == 200
        r = client.put(f"/api/uploads/{uid}/files", params={"path": "more.bin"}, content=b"0" * (2 * CHUNK))
        assert r.status_code == 413                          # the declared 3 chunks are reserved
        from resense_web import uploads
        monkeypatch.setattr(uploads, "disk_free", lambda _p: 10)
        r = declare(client, uid, "other.bin", CHUNK)
        assert r.status_code == 507 and "места" in r.json()["detail"]


def test_whole_file_put_with_gzip_crc_and_size(client, env):
    uid = start(client)
    data = b"line\n" * 50_000
    gz = gzip.compress(data)
    hdr = {"X-Content-Encoding": "gzip", "X-Content-CRC32": f"{zlib.crc32(data):08x}"}
    r = client.put(f"/api/uploads/{uid}/files", params={"path": "d/x.txt", "size": len(data)}, content=gz, headers=hdr)
    assert r.status_code == 200 and r.json() == {"path": "d/x.txt", "size_bytes": len(data)}
    assert (env.uploads_dir / uid / "files" / "d" / "x.txt").read_bytes() == data
    r = client.put(f"/api/uploads/{uid}/files", params={"path": "y.txt"}, content=data,
                   headers={"X-Content-CRC32": "00000000"})
    assert r.status_code == 400 and "Контрольная сумма" in r.json()["detail"]
    r = client.put(f"/api/uploads/{uid}/files", params={"path": "z.txt", "size": len(data) + 1}, content=data)
    assert r.status_code == 400 and "не полностью" in r.json()["detail"]
    r = client.put(f"/api/uploads/{uid}/files", params={"path": "w.txt", "size": 10}, content=gz,
                   headers={"X-Content-Encoding": "gzip"})
    assert r.status_code == 400                               # inflates beyond the declared size
    r = client.put(f"/api/uploads/{uid}/files", params={"path": "v.txt"}, content=b"not gzip",
                   headers={"X-Content-Encoding": "gzip"})
    assert r.status_code == 400
    names = sorted(p.name for p in (env.uploads_dir / uid / "files").iterdir())
    assert names == ["d"]                                     # nothing half-written is left behind


def _slow_unzip(monkeypatch, delay=0.8):
    from resense_web import uploads
    real = uploads.safe_extract_zip

    def slow(*a, **k):
        time.sleep(delay)
        return real(*a, **k)
    monkeypatch.setattr(uploads, "safe_extract_zip", slow)


def _results_zip(n=5) -> bytes:
    from test_uploads import result_lines
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("ride/run.jsonl", result_lines(n))
    return buf.getvalue()


def test_finalize_in_background_with_progress(client, env, monkeypatch):
    _slow_unzip(monkeypatch)
    uid = start(client, "Ночной проезд")
    assert client.put(f"/api/uploads/{uid}/files", params={"path": "ride.zip"}, content=_results_zip()).status_code == 200
    r = client.post(f"/api/uploads/{uid}/finalize", params={"wait": "false"})
    assert r.status_code == 202, r.text
    st = r.json()
    assert st["state"] == "finalizing" and st["finalize"]["stage"] in ("starting", "unpacking")
    # nothing may change the area meanwhile
    r = client.put(f"/api/uploads/{uid}/files", params={"path": "late.txt"}, content=b"x")
    assert r.status_code == 409
    assert declare(client, uid, "late.bin", CHUNK + 1).status_code == 409
    assert client.delete(f"/api/uploads/{uid}").status_code == 409
    done = wait_status(client, uid, "done")
    assert done["recording"]["name"] == "Ночной проезд" and done["recording"]["kind"] == "jsonl"
    assert done["finalize"] is None and done["error"] is None
    assert client.get(f"/api/recordings/{done['recording']['id']}").status_code == 200
    assert not (env.uploads_dir / uid).exists()


def test_two_finalize_calls_share_one_run(client, monkeypatch):
    _slow_unzip(monkeypatch, 0.5)
    uid = start(client)
    client.put(f"/api/uploads/{uid}/files", params={"path": "ride.zip"}, content=_results_zip())
    out = []
    threads = [threading.Thread(target=lambda: out.append(client.post(f"/api/uploads/{uid}/finalize")))
               for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert [r.status_code for r in out] == [201, 201]
    assert out[0].json()["id"] == out[1].json()["id"]
    assert len(client.get("/api/recordings").json()) == 1


def test_failed_finalize_keeps_the_area_for_more_files(client, env):
    from test_uploads import result_lines
    uid = start(client)
    client.put(f"/api/uploads/{uid}/files", params={"path": "notes.txt"}, content=b"hello")
    r = client.post(f"/api/uploads/{uid}/finalize", params={"wait": "false"})
    assert r.status_code == 202
    st = wait_status(client, uid, "failed")
    assert st["state"] == "receiving" and "не найдено" in st["error"]
    assert st["files"] == [{"path": "notes.txt", "size_bytes": 5}]
    assert client.put(f"/api/uploads/{uid}/files", params={"path": "run.jsonl"}, content=result_lines(3)).status_code == 200
    r = client.post(f"/api/uploads/{uid}/finalize")
    assert r.status_code == 201 and r.json()["n_frames"] == 3


def test_leftovers_of_interrupted_writes_and_unpacking_are_ignored(client, env, tiny_bag):
    from test_uploads import bag_files
    uid = start(client)
    for name, data in bag_files(tiny_bag, "ride/").items():
        assert client.put(f"/api/uploads/{uid}/files", params={"path": name}, content=data).status_code == 200
    files = env.uploads_dir / uid / "files"
    (files / "ride" / ".tiny_0.db3.part-abc123").write_bytes(b"junk")
    half = files / ".big.unpacking-xyz123"
    half.mkdir()
    (half / "metadata.yaml").write_text("broken")
    (half / "x_0.db3").write_bytes(b"0" * 10_000_000)       # bigger: would win find_input's pick
    assert [f["path"] for f in client.get(f"/api/uploads/{uid}").json()["files"]] == sorted(
        f"ride/{p.name}" for p in tiny_bag.iterdir())
    r = client.post(f"/api/uploads/{uid}/finalize")
    assert r.status_code == 201, r.text
    from pathlib import Path
    assert sorted(p.name for p in Path(r.json()["path"]).iterdir()) == sorted(p.name for p in tiny_bag.iterdir())


def test_delete_sweeps_a_write_that_outlived_it(env):
    from resense_web.uploads import UploadError, UploadStore
    env.ensure_dirs()
    store = UploadStore(env)
    uid = store.create("x")
    with store.writing(uid):
        store.declare(uid, PurePosixPath("late.bin"), CHUNK * 2, CHUNK)
        store.delete(uid)
        with pytest.raises(UploadError) as err:
            store.write_chunk(uid, PurePosixPath("late.bin"), 0, os.urandom(CHUNK), None)
        assert err.value.status == 404
        (env.uploads_dir / uid / "files").mkdir(parents=True, exist_ok=True)   # what a late write leaves
    assert not (env.uploads_dir / uid).exists()
    with pytest.raises(UploadError):
        store.status(uid)


def test_stale_areas_are_removed(env):
    from resense_web.uploads import UploadStore
    env.ensure_dirs()
    store = UploadStore(env)
    old, fresh = store.create("old"), store.create("fresh")
    store.declare(old, PurePosixPath("a.bin"), CHUNK * 2, CHUNK)
    past = time.time() - 4 * 24 * 3600
    for p in [env.uploads_dir / old, *(env.uploads_dir / old).rglob("*")]:
        os.utime(p, (past, past))
    assert store.cleanup_stale() == 1                       # the default TTL is 72 h
    assert not (env.uploads_dir / old).exists() and (env.uploads_dir / fresh).is_dir()


def test_a_retried_chunk_racing_the_original_is_a_no_op(env, monkeypatch):
    """The client gave up on a slow request and sent the chunk again while the server was still
    writing the first one, which then completed the file: the retry is answered 200, not 404."""
    from resense_web import uploads
    env.ensure_dirs()
    store = uploads.UploadStore(env)
    uid = store.create("x")
    data = os.urandom(CHUNK + 10)
    rel = PurePosixPath("a.bin")
    store.declare(uid, rel, len(data), CHUNK)
    store.write_chunk(uid, rel, 0, data[:CHUNK], zlib.crc32(data[:CHUNK]))
    real = uploads.decode_body

    def original_finishes_meanwhile(body, encoding, expected):
        monkeypatch.setattr(uploads, "decode_body", real)
        store.write_chunk(uid, rel, 1, data[CHUNK:], zlib.crc32(data[CHUNK:]))   # completes, moves the .part
        return real(body, encoding, expected)
    monkeypatch.setattr(uploads, "decode_body", original_finishes_meanwhile)
    r = store.write_chunk(uid, rel, 1, data[CHUNK:], zlib.crc32(data[CHUNK:]))
    assert r["complete"] and (env.uploads_dir / uid / "files" / "a.bin").read_bytes() == data


def test_a_write_of_a_file_declared_anew_is_refused_not_mixed_in(env, monkeypatch):
    """A chunk of the old declaration still in flight when the path is declared again (another
    size / fingerprint): its bytes must not land in the new file, nor its state on disk."""
    from resense_web import uploads
    env.ensure_dirs()
    store = uploads.UploadStore(env)
    uid = store.create("x")
    rel = PurePosixPath("a.bin")
    old = os.urandom(4 * CHUNK)
    store.declare(uid, rel, len(old), CHUNK, "old")
    new = os.urandom(2 * CHUNK)
    real = uploads.decode_body

    def redeclared_meanwhile(body, encoding, expected):
        monkeypatch.setattr(uploads, "decode_body", real)
        store.declare(uid, rel, len(new), CHUNK, "new")
        return real(body, encoding, expected)
    monkeypatch.setattr(uploads, "decode_body", redeclared_meanwhile)
    with pytest.raises(uploads.UploadError) as err:
        store.write_chunk(uid, rel, 1, old[CHUNK:2 * CHUNK], zlib.crc32(old[CHUNK:2 * CHUNK]))
    assert err.value.status == 409
    st = store.status(uid)["partial"][0]
    assert st["size_bytes"] == len(new) and st["received_chunks"] == 0
    for i in (0, 1):
        store.write_chunk(uid, rel, i, new[i * CHUNK:(i + 1) * CHUNK], zlib.crc32(new[i * CHUNK:(i + 1) * CHUNK]))
    assert (env.uploads_dir / uid / "files" / "a.bin").read_bytes() == new
    fresh = uploads.UploadStore(env)                       # what a restarted server reads from disk
    assert fresh.status(uid)["partial"] == [] and fresh.status(uid)["files"] == [{"path": "a.bin", "size_bytes": len(new)}]


def test_a_failed_completion_can_be_retried(env, monkeypatch):
    from resense_web import uploads
    env.ensure_dirs()
    store = uploads.UploadStore(env)
    uid = store.create("x")
    rel = PurePosixPath("a.bin")
    data = os.urandom(2 * CHUNK)
    store.declare(uid, rel, len(data), CHUNK)
    store.write_chunk(uid, rel, 0, data[:CHUNK], None)
    real_replace = os.replace
    monkeypatch.setattr(uploads.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("disk hiccup")))
    with pytest.raises(OSError):
        store.write_chunk(uid, rel, 1, data[CHUNK:], None)
    monkeypatch.setattr(uploads.os, "replace", real_replace)
    assert store.status(uid)["partial"][0]["missing"] == [[1, 1]]     # not counted as received
    assert store.write_chunk(uid, rel, 1, data[CHUNK:], None)["complete"]
    assert (env.uploads_dir / uid / "files" / "a.bin").read_bytes() == data


def test_a_silent_body_ends_with_408():
    """A connection that died without a FIN / RST must not keep its write (and the area) open."""
    import asyncio

    from resense_web.api.recordings import body_chunks
    from resense_web.uploads import UploadError

    class Stalled:
        async def stream(self):
            yield b"first"
            await asyncio.sleep(30)
            yield b"never"

    async def read():
        out = []
        async for c in body_chunks(Stalled(), idle_s=0.2):
            out.append(c)
        return out
    with pytest.raises(UploadError) as err:
        asyncio.run(read())
    assert err.value.status == 408


def test_a_whole_file_put_counts_as_activity(client, env):
    uid = start(client)
    meta = env.uploads_dir / uid / "meta.json"
    past = time.time() - 3600
    os.utime(meta, (past, past))
    assert client.put(f"/api/uploads/{uid}/files", params={"path": "d/x.bin"}, content=b"12").status_code == 200
    assert time.time() - meta.stat().st_mtime < 60
