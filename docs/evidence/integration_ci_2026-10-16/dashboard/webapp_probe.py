"""Opt-in baseline diagnostics for the completed webapp CI failures."""
import json
import os
from pathlib import Path
import time

import pytest


@pytest.fixture(autouse=True)
def probe(request):
    if "app" not in request.fixturenames:
        yield
        return
    app = request.getfixturevalue("app")
    if os.environ.get("WEBAPP_PROBE_URL_ONLY") and request.node.name == "test_player_link_waits_for_rendered_destination":
        def url_only(page, run_id):
            import re
            from playwright.sync_api import expect
            expect(page).to_have_url(re.compile(rf"/player/{run_id}\?pos=\d+$"))
            return int(page.url.rsplit("=", 1)[1])
        request.getfixturevalue("monkeypatch").setattr(request.module, "player_pos", url_only)
    if request.node.name == "test_queue_cancel_retry_log_and_clear":
        api = request.getfixturevalue("backend").api
        names = {r["name"] for r in api.get("/recordings")}
        for scenario, seconds in (("approach", 15), ("crossing", 5)):
            if f"demo_{scenario}" not in names:
                api.demo(scenario, seconds)
    page = app.page
    page.add_init_script("""(() => {
        window.__slowGL = [];
        for (const C of [WebGLRenderingContext, WebGL2RenderingContext]) {
            for (const name of ['getShaderParameter', 'getProgramParameter', 'finish', 'getParameter', 'isContextLost', 'readPixels', 'drawArrays', 'drawElements']) {
                const original = C.prototype[name];
                if (!original) continue;
                C.prototype[name] = function(...args) {
                    const start = performance.now();
                    try { return original.apply(this, args); }
                    finally { const ms = performance.now() - start; if (ms > 30) window.__slowGL.push({name, ms, url: location.href}); }
                };
            }
        }
    })();""")
    cdp = page.context.new_cdp_session(page)
    rate = int(os.environ.get("WEBAPP_PROBE_CPU", "1"))
    cdp.send("Emulation.setCPUThrottlingRate", {"rate": rate})
    path = Path(os.environ.get("WEBAPP_PROBE_LOG", "/tmp/webapp-current-events.jsonl"))
    with path.open("a", encoding="utf-8") as stream:
        def log(kind, data):
            if not stream.closed:
                stream.write(json.dumps({"t": time.monotonic(), "test": request.node.name,
                                         "kind": kind, "data": data}, ensure_ascii=False) + "\n")
                stream.flush()
        page.on("request", lambda r: log("request", [r.method, r.url]))
        page.on("requestfinished", lambda r: log("finished", [r.method, r.url]))
        page.on("requestfailed", lambda r: log("failed", [r.method, r.url, r.failure]))
        page.on("framenavigated", lambda f: log("navigated", f.url))
        page.on("domcontentloaded", lambda: log("domcontentloaded", page.url))
        log("start", {"cpu_rate": rate})
        yield
        log("slowGL", page.evaluate("window.__slowGL"))
        log("end", page.url)
