"""Deliberately fail after staging, while withheld chunk routes still need finally cleanup."""
import pytest


@pytest.fixture(autouse=True)
def fail_with_held_routes(request, monkeypatch):
    if request.node.name == "test_big_upload_pause_drop_reload_resume":
        def fail(_page):
            raise RuntimeError("deliberate held-route teardown probe")
        monkeypatch.setattr(request.module, "upload_id", fail)
