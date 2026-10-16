"""Opt-in Playwright event probe: PYTHONPATH=<this directory> pytest -p web_ci_events ..."""
import json
import os
import time
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def browser_events(request):
    if "app" not in request.fixturenames:
        yield
        return
    app = request.getfixturevalue("app")
    delay = float(os.environ.get("WEB_CI_DELAY_RELOAD_S", "0"))
    if delay and request.node.name == "test_big_upload_pause_drop_reload_resume":
        reload_page = app.page.reload

        def delayed_reload(**kw):
            app.page.wait_for_timeout(delay * 1000)
            return reload_page(**kw)

        app.page.reload = delayed_reload
    if os.environ.get("WEB_CI_SEED") and request.node.name in (
        "test_server_folder_preset_and_options", "test_queue_cancel_retry_log_and_clear"
    ):
        api = request.getfixturevalue("backend").api
        names = {r["name"] for r in api.get("/recordings")}
        for scenario, seconds in (("approach", 15), ("crossing", 5)):
            if f"demo_{scenario}" not in names:
                api.demo(scenario, seconds)
    path = Path(os.environ.get("WEB_CI_EVENTS", "/tmp/web-ci-events.jsonl"))
    with path.open("a", encoding="utf-8") as fh:
        def log(event, detail):
            if fh.closed:
                return
            fh.write(json.dumps({"time": time.monotonic(), "test": request.node.name,
                                 "event": event, "detail": detail}, ensure_ascii=False) + "\n")
            fh.flush()

        def watch(page):
            page.on("request", lambda r: log("request", [r.method, r.url, r.resource_type]))
            page.on("requestfinished", lambda r: log("finished", [r.method, r.url]))
            page.on("requestfailed", lambda r: log("failed", [r.method, r.url, r.failure]))
            page.on("framenavigated", lambda f: log("navigated", f.url))
            page.on("load", lambda: log("load", page.url))
            page.on("domcontentloaded", lambda: log("domcontentloaded", page.url))
            page.on("dialog", lambda d: log("dialog", d.type))

        watch(app.page)
        app.page.context.on("page", watch)
        log("start", app.page.url)
        yield
        log("end", app.page.url)
