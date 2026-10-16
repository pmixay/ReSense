"""A big upload over a slow link in a real browser, the 25 GB case at a small scale: chunks with
live bytes / speed / time left, compression on the wire, pause and resume, a connection that drops
(retried as soon as it is back), a second tab that keeps its hands off it, a page reload in the middle (the same file picked again continues
where the server stopped, nothing is sent twice) and the recording at the end, byte for byte.

  python -m pytest -q webapp/e2e/test_upload_resume.py        (~1 min)
"""
from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path

import pytest
from e2e_helpers import api_route, real_errors, wait_until

pw = pytest.importorskip("playwright.sync_api")
expect = pw.expect

MB = 1024 * 1024
N_FRAMES = 40
LINK = 2 * MB          # bytes / s on the wire (CDP throttling)


def results_with_padding(path: Path, size: int) -> None:
    """A results .jsonl the server accepts, padded with junk lines it skips (base64 of random
    bytes: deflates to ~0.75, so gzip on the wire pays and the bytes stay checkable)."""
    frames = [json.dumps({"stamp": 100.0 + 0.1 * i, "frame": i, "obstacle": 15 <= i < 25, "warning": False,
                          "nearest_distance": 30.0 if 15 <= i < 25 else None, "detections": [], "warnings": [],
                          "n_points": 1000, "clear_distance": 90.0, "timing_ms": {"total": 20.0},
                          "health": {"level": "ok", "decision_level": "ok", "visibility": 120.0}}) for i in range(N_FRAMES)]
    with open(path, "w", encoding="ascii") as fh:
        per = (size - sum(len(f) + 1 for f in frames)) // N_FRAMES
        for f in frames:
            fh.write(f + "\n")
            junk = base64.b64encode(os.urandom(per * 3 // 4)).decode()
            for k in range(0, len(junk), 4096):
                fh.write("# " + junk[k:k + 4094] + "\n")


def throttle(cdp, offline: bool = False, up: int = LINK) -> None:
    cdp.send("Network.emulateNetworkConditions",
             {"offline": offline, "latency": 0, "downloadThroughput": -1, "uploadThroughput": up})


def upload_id(page) -> str:
    return json.loads(page.evaluate("localStorage.getItem('resense.upload.v1')"))["uploadId"]


def received(api, uid: str) -> int:
    return api.get(f"/uploads/{uid}")["bytes_received"]


def accepted_chunks(backend, uid: str, since: int = 0) -> set[int]:
    """Chunk indexes the server answered 200 for (its access log), from byte ``since`` of the log."""
    with open(backend.log, "rb") as fh:
        fh.seek(since)
        text = fh.read().decode("utf-8", errors="replace")
    return {int(i) for i in re.findall(rf'"PUT /api/uploads/{uid}/chunked/(\d+)\?[^"]*" 200', text)}


def test_big_upload_pause_drop_reload_resume(app, backend, tmp_path):
    page, api = app.page, backend.api
    ride = tmp_path / "long_ride.jsonl"
    results_with_padding(ride, 40 * MB)
    cdp = page.context.new_cdp_session(page)
    cdp.send("Network.enable")
    throttle(cdp)
    app.goto("/upload")
    # A throughput limit alone is not a synchronization barrier: four concurrent, compressed
    # chunks can finish while the assertions / second tab are running. Keep a strict subset
    # on the real server until reload, without changing the file size or upload concurrency.
    cutoff, offline = 2, False
    held_routes = []
    chunks = api_route(backend.url, r"/uploads/[^/]+/chunked/\d+\?")

    def gate(route):
        index = int(re.search(r"/chunked/(\d+)", route.request.url)[1])
        if offline or index < cutoff:
            route.continue_()  # offline failures must still come from Chromium's real network
        else:
            held_routes.append(route)

    page.route(chunks, gate)
    files = page.locator('input[type=file][accept^=".zip"]')
    # Routed Blob PUTs need not emit intermediate progress before their responses. Observe
    # both permitted acknowledgements before checking metrics / taking the pause snapshot:
    # abort cannot undo a complete body the server is already committing.
    with (
        page.expect_response(lambda r: r.request.method == "PUT" and chunks.search(r.url) and "/chunked/0?" in r.url) as first_chunk,
        page.expect_response(lambda r: r.request.method == "PUT" and chunks.search(r.url) and "/chunked/1?" in r.url) as second_chunk,
    ):
        files.set_input_files(str(ride))
    assert [first_chunk.value.status, second_chunk.value.status] == [200, 200]

    # live progress: bytes, speed, time left, the compression saved on the wire
    expect(page.get_by_text(re.compile(r"из\s40\sМБ"))).to_be_visible()
    expect(page.get_by_text(re.compile(r"^осталось \d+:\d\d$"))).to_be_visible()
    expect(page.get_by_text(re.compile(r"^сжатие −\d+\s%$"))).to_be_visible(timeout=20_000)
    uid = upload_id(page)

    # pause: the transfer stops (nothing more arrives), what arrived stays on the server
    page.get_by_role("button", name="Приостановить загрузку").click()
    expect(page.get_by_text("пауза", exact=True)).to_be_visible()
    held = received(api, uid)
    time.sleep(1.5)
    assert received(api, uid) == held

    # the connection is gone when the transfer resumes: it waits and retries by itself
    offline = True
    throttle(cdp, offline=True)
    page.get_by_role("button", name="Продолжить загрузку").click()
    expect(page.get_by_text(re.compile(r"нет связи · повтор через \d+ с"))).to_be_visible()
    expect(page.get_by_text(re.compile(r"^(Нет сети — загрузка продолжится|Связь с сервером прервалась)"))).to_be_visible()
    cutoff, offline = 3, False  # one more real chunk moves after recovery; the rest wait for reload
    throttle(cdp)                                             # back: the browser's «online» retries at once
    expect(page.get_by_text(re.compile(r"^осталось"))).to_be_visible(timeout=15_000)

    # a second tab sees the upload running there: it offers neither to continue nor to delete it
    other_tab = page.context.new_page()
    other_tab.goto(backend.url + "/upload")
    expect(other_tab.get_by_text("идёт в другой вкладке")).to_be_visible()
    expect(other_tab.get_by_role("button", name="Удалить незавершённую загрузку")).to_have_count(0)
    expect(other_tab.get_by_role("button", name="Выбрать файлы")).to_be_disabled()
    other_tab.close()

    # a reload in the middle: the browser asks first; the server keeps every finished chunk
    wait_until(lambda: received(api, uid) >= 8 * MB, timeout=60)
    assert api.get(f"/uploads/{uid}")["state"] == "receiving"
    dialogs = []

    def leave(d):
        dialogs.append(d.type)
        d.accept()

    page.once("dialog", leave)
    page.reload()
    assert dialogs == ["beforeunload"]
    for route in held_routes:
        try:
            route.abort()
        except pw.Error:  # the old document cancelled it on pause / reload
            pass
    page.unroute(chunks, gate)
    expect(page.get_by_text("не завершена")).to_be_visible()
    expect(page.get_by_text("выберите тот же файл, чтобы продолжить")).to_be_visible()
    expect(page.get_by_text(re.compile(r"на сервере .+ из\s40\sМБ"))).to_be_visible()
    before = received(api, uid)
    assert 8 * MB <= before < 40 * MB
    stored = accepted_chunks(backend, uid)
    n_chunks = -(-ride.stat().st_size // (8 * MB))
    assert stored and len(stored) < n_chunks
    log_mark = backend.log.stat().st_size

    # another file is not taken for it by mistake: it asks before replacing the unfinished upload
    other = tmp_path / "other.jsonl"
    other.write_text(ride.read_text(encoding="ascii")[:50_000].rsplit("\n", 1)[0] + "\n", encoding="ascii")
    files.set_input_files(str(other))
    expect(page.get_by_text(re.compile("она будет удалена"))).to_be_visible()
    page.get_by_role("button", name="Отмена", exact=True).click()
    expect(page.get_by_text("не завершена")).to_be_visible()

    # the same file continues the upload: only the missing chunks go
    files.set_input_files(str(ride))
    expect(page.get_by_text("докачка")).to_be_visible()
    throttle(cdp, up=-1)
    expect(page.get_by_text("проверено")).to_be_visible(timeout=60_000)
    rec = next(r for r in api.get("/recordings") if r["name"] == "long_ride")
    assert rec["kind"] == "jsonl" and rec["n_frames"] == N_FRAMES
    assert Path(rec["path"]).read_bytes() == ride.read_bytes()
    assert page.evaluate("localStorage.getItem('resense.upload.v1')") is None
    # the chunks the server held before the reload were not sent again
    after = accepted_chunks(backend, uid, since=log_mark)
    assert not (after & stored) and after | stored == set(range(n_chunks))
    # the run of the uploaded results
    job = api.job(rec["id"])
    assert api.wait_job(job["id"])["status"] == "done"
    errors = real_errors(app.errors, patterns=(r"ERR_INTERNET_DISCONNECTED", r"ERR_ABORTED", r"Failed to load resource"))
    assert errors == []
