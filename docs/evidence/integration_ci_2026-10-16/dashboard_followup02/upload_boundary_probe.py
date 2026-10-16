"""Opt-in pytest plugin for the real browser upload's log-snapshot interleaving."""
import json
import subprocess
import time

import pytest


@pytest.fixture(scope="session", autouse=True)
def delayed_backend(tmp_path_factory):
    release = tmp_path_factory.mktemp("chunk-log-boundary") / "release"
    popen = subprocess.Popen

    def launch(args, *a, **kw):
        if isinstance(args, list) and args[1:3] == ["-m", "resense_web"]:
            args = [args[0], "-c", "import delayed_chunk_log; delayed_chunk_log.main()", *args[3:]]
        return popen(args, *a, **kw)

    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("UPLOAD_BOUNDARY_RELEASE", str(release))
        patch.setattr(subprocess, "Popen", launch)
        yield release


@pytest.fixture(autouse=True)
def delayed_chunk_success(request, monkeypatch, delayed_backend):
    if request.node.name != "test_big_upload_pause_drop_reload_resume":
        yield
        return
    release = delayed_backend
    module = request.module
    page = request.getfixturevalue("app").page
    backend = request.getfixturevalue("backend")
    reload_page = page.reload

    def reload_after_commit(**kw):
        # Isolate the log-reader race from the separate early-reload race: the real
        # server must already hold chunk 2, while its access-log delivery stays held.
        uid = module.upload_id(page)
        deadline = time.monotonic() + 30
        while backend.api.get(f"/uploads/{uid}")["bytes_received"] < 24 * module.MB:
            assert time.monotonic() < deadline, "chunk 2 did not commit before diagnostic reload"
            page.wait_for_timeout(50)
        return reload_page(**kw)

    monkeypatch.setattr(page, "reload", reload_after_commit)
    read = module.accepted_chunks
    injected = []

    def snapshot(backend, uid, since=0):
        stored = read(backend, uid, since)
        if since == 0 and not injected:
            assert stored == {0, 1}, stored
            # All upload responses and stored bytes are untouched. Only the actual access
            # log flush is placed between the old test's read and its later independent stat.
            release.touch()
            deadline = time.monotonic() + 10
            while 2 not in read(backend, uid):
                assert time.monotonic() < deadline, "real successful chunk-2 log did not arrive"
                time.sleep(0.01)
            injected.append({"snapshot": sorted(stored), "after_release": sorted(read(backend, uid)),
                             "server_bytes": backend.api.get(f"/uploads/{uid}")["bytes_received"]})
            print("UPLOAD_BOUNDARY_INJECTION", json.dumps(injected[-1]), flush=True)
        return stored

    monkeypatch.setattr(module, "accepted_chunks", snapshot)
    yield
    assert len(injected) == 1, "the intended log boundary was not exercised"
