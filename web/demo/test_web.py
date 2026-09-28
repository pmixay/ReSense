"""Tests for the P2 deliverables (RViz layout, Foxglove layout, demo run, dashboard replay, label tool).

Run from the repository root:  python -m pytest -q web/demo
(``testpaths`` in pyproject.toml only lists ``tests/``, so the plain ``pytest -q`` does not
collect this file — add ``web/demo`` there if the team wants it in CI.)  Everything runs
without the organizers' dataset; the browser tests skip when Playwright or Chromium is missing.
"""
import glob
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "web", "demo"))

RVIZ = os.path.join(ROOT, "ros2_ws", "src", "resense_ros", "rviz", "resense.rviz")
FOX = os.path.join(ROOT, "web", "foxglove_layout.json")
LABEL_TOOL = os.path.join(ROOT, "web", "label_tool.html")
PRESENTATION = os.path.join(ROOT, "docs", "presentation", "ReSense_LCT2026.pptx")
MOSCOW_SANS = (
    os.path.join(ROOT, "web", "assets", "fonts", "MoscowSansRegular.otf"),
    os.path.join(ROOT, "web", "assets", "fonts", "MoscowSansExtraBold.otf"),
)
RAW_TOPICS = ("/lidar_points", "/sensing/lidar/hesai128/pointcloud")


# --------------------------------------------------------------------------- A. RViz layout
def test_rviz_layout_parses_and_covers_both_bags():
    import yaml
    d = yaml.safe_load(open(RVIZ))
    vm = d["Visualization Manager"]
    assert vm["Global Options"]["Fixed Frame"] == "resense_lidar"
    by_topic = {disp.get("Topic", {}).get("Value"): disp for disp in vm["Displays"] if isinstance(disp.get("Topic"), dict)}
    for t in RAW_TOPICS:
        disp = by_topic[t]
        assert disp["Class"] == "rviz_default_plugins/PointCloud2"
        # reliable: `ros2 bag play` offers the recorded RELIABLE profile and a best-effort display
        # loses most 5-10 MB clouds (EXPERIMENTS.md section 3b, the RViz recording of 23.09)
        assert disp["Topic"]["Reliability Policy"] == "Reliable"
        assert disp["Topic"]["Depth"] == 5
        assert disp["Enabled"] is True
    assert by_topic["/resense/corridor_points"]["Class"] == "rviz_default_plugins/PointCloud2"
    assert by_topic["/resense/markers"]["Class"] == "rviz_default_plugins/MarkerArray"
    view = vm["Views"]["Current"]
    assert view["Class"] == "rviz_default_plugins/Orbit"
    assert view["Focal Point"]["Y"] < 0 and abs(view["Yaw"] - 1.5708) < 1e-3   # looking down the track (-Y is forward)


# --------------------------------------------------------------------------- C. Foxglove layout
def test_foxglove_layout_parses_and_has_the_panels():
    d = json.load(open(FOX))
    cfg = d["configById"]
    three_d = [c for k, c in cfg.items() if k.startswith("3D!")]
    assert len(three_d) == 1
    topics = three_d[0]["topics"]
    for t in RAW_TOPICS + ("/resense/corridor_points", "/resense/markers"):
        assert topics[t]["visible"] is True
    plots = {k: c for k, c in cfg.items() if k.startswith("Plot!")}
    plotted = {p["value"] for c in plots.values() for p in c["paths"]}
    assert {"/resense/nearest_distance.data", "/resense/latency_ms.data", "/resense/fps.data"} <= plotted
    for c in plots.values():
        for p in c["paths"]:
            assert p["timestampMethod"] in ("receiveTime", "headerStamp")
    assert any(c.get("path", "").startswith("/resense/obstacle_detected") for k, c in cfg.items() if k.startswith("Indicator!"))
    decision = [c for k, c in cfg.items() if k.startswith("Indicator!") and c.get("path") == "/resense/decision.data"]
    assert decision and {r["rawValue"] for r in decision[0]["rules"]} == {"GO", "CAUTION", "STOP", "FAULT"}
    assert cfg["Indicator!obstacle"]["fallbackLabel"] == "NO DATA"
    assert next(r["label"] for r in decision[0]["rules"] if r["rawValue"] == "GO") == "LAST GO: no obstacle detected"
    assert "/resense/clear_distance.data" in plotted
    assert any(c.get("topicPath") == "/resense/status" for k, c in cfg.items() if k.startswith("RawMessages!"))

    # every leaf of the mosaic layout is a configured panel and every panel is placed
    leaves = set()

    def walk(node):
        if isinstance(node, str):
            leaves.add(node)
        else:
            walk(node["first"])
            walk(node["second"])
    walk(d["layout"])
    assert leaves == set(cfg)


# --------------------------------------------------------------------------- B. demo run format
RESULT_KEYS = {"stamp", "obstacle", "warning", "nearest_distance", "detections", "warnings", "n_candidates",
               "n_points", "n_corridor", "track", "timing_ms"}


@pytest.fixture(scope="module")
def tiny_run(tmp_path_factory):
    pytest.importorskip("open3d", reason="open3d needed for the synthetic tunnel")
    import make_demo_run
    out = str(tmp_path_factory.mktemp("demo") / "tiny.jsonl")
    summary = make_demo_run.run(out, quiet=True, clear_before=3, approach=8, clear_after=3,
                                start=70.0, end=42.0, seed=1)
    return out, summary


def test_make_demo_run_writes_resense_run_format(tiny_run):
    out, summary = tiny_run
    lines = [json.loads(ln) for ln in open(out) if ln.strip()]
    assert len(lines) == summary["frames"] == 14
    for i, d in enumerate(lines):
        assert RESULT_KEYS <= set(d), d.keys() - RESULT_KEYS
        assert d["frame"] == i and d["frame_id"] == "synthetic"
        assert "node" not in d
        assert d["stamp"] == pytest.approx(i * 0.1)
    assert not lines[0]["obstacle"] and not lines[-1]["obstacle"]
    alarms = [d for d in lines if d["obstacle"]]
    assert alarms, "the approaching person was never confirmed"
    # 70 -> 42 m, then the person is gone; since v0.6.3 a reported obstacle is held over one missed
    # frame at its predicted distance (one 4 m step closer)
    assert all(36.0 <= d["nearest_distance"] <= 72.0 for d in alarms)


# --------------------------------------------------------------------------- B. dashboard replay in a browser
def _browser_available():
    try:
        from playwright.sync_api import sync_playwright  # noqa
    except ImportError:
        return False
    import check_dashboard
    try:
        with sync_playwright() as p:
            try:
                b = p.chromium.launch(headless=True)
            except Exception:
                path = check_dashboard.find_chromium()
                if not path:
                    return False
                b = p.chromium.launch(headless=True, executable_path=path)
            b.close()
        return True
    except Exception:
        return False


def _launch(p):
    import check_dashboard
    try:
        return p.chromium.launch(headless=True)
    except Exception:
        return p.chromium.launch(headless=True, executable_path=check_dashboard.find_chromium())


def test_dashboard_replays_jsonl_in_chromium(tiny_run, tmp_path):
    if not _browser_available():
        pytest.skip("playwright + chromium not available")
    import check_dashboard
    out, _ = tiny_run
    shot = str(tmp_path / "shot.png")
    r = check_dashboard.check(out, shot, None, speed=10.0, min_dist=40.0, max_dist=72.0, timeout_s=60.0)
    assert r["ok"], r["errors"]
    assert r["frames"] == 14
    assert r["observed"][0][1].startswith("ПРЕПЯТСТВИЕ НЕ ОБНАРУЖЕНО")
    # A confirmed track is intentionally held for one missed frame and projected one step
    # closer (4 m in this synthetic run), so the last displayed distance can be just below
    # the acceptance window used by check().
    assert r["nearest_min_m"] is not None and 36.0 <= r["nearest_min_m"] <= 72.0
    assert os.path.getsize(shot) > 10_000
    assert not r["errors"]


def test_dashboard_rejects_garbage_lines(tmp_path):
    """A results file with blank / broken lines still loads the good frames (page logic only)."""
    if not _browser_available():
        pytest.skip("playwright + chromium not available")
    from playwright.sync_api import sync_playwright
    import check_dashboard
    good = {"stamp": 1.5, "obstacle": True, "warning": False, "nearest_distance": 55.6, "detections": [
        {"id": 1, "zone": "gauge", "distance": 55.6, "lateral": 0.1, "center": [56.0, 0.1, 0.9], "size": [0.5, 0.5, 1.7],
         "n_points": 40, "confidence": 0.9, "age": 5, "height_min": 0.1, "intensity": 60.0}], "warnings": [],
        "n_candidates": 1, "n_points": 1000, "n_corridor": 40,
        "track": {"center": 0.1, "yaw": 0.0, "curvature": 0.0, "axis_valid": 120.0}, "timing_ms": {"total": 50.0},
        "frame": 7, "frame_id": "x", "node": {"latency_ms": 60.0, "fps": 9.8, "frames": 8, "dropped_frames": 2, "input_period_ms": 100.0}}
    text = "\n\nnot json\n" + json.dumps(good) + "\n{\"foo\": 1}\n"
    with sync_playwright() as p:
        b = _launch(p)
        page = b.new_page()
        page.goto("file://" + check_dashboard.INDEX, wait_until="domcontentloaded")
        page.wait_for_function("window.resense !== undefined")
        n = page.evaluate("window.resense.loadText(%s, 'x.jsonl')" % json.dumps(text))
        assert n == 1
        assert check_dashboard.banner_text(page) == "ПРЕПЯТСТВИЕ  55.6 м"
        page.locator("#node-card summary").click()
        assert page.inner_text("#n-dropped").startswith("2")       # node stats are shown when present
        assert "notice" in page.get_attribute("#node-card", "class")
        b.close()


def test_dashboard_freshness_and_live_stream_stall():
    """Invalid data and a stalled status stream must not retain a green monitored corridor."""
    if not _browser_available():
        pytest.skip("playwright + chromium not available")
    from playwright.sync_api import sync_playwright
    import check_dashboard
    with sync_playwright() as p:
        b = _launch(p)
        page = b.new_page()
        page.goto("file://" + check_dashboard.INDEX, wait_until="domcontentloaded")
        page.wait_for_function("window.resense !== undefined")
        base = {"stamp": 1.0, "snapshot_kind": "frame", "obstacle": False, "warning": False, "nearest_distance": None,
                "detections": [], "warnings": [], "clear_distance": 120, "decision": "GO",
                "health": {"level": "ok"}, "freshness": {"valid": True, "reason": "current", "go_allowed": True,
                "mode": "replay", "clock_reference": "publisher_utc", "queue_lag_s": 0,
                "source_age_s": .02, "residence_age_s": .01,
                "max_result_age_s": .5, "future_tolerance_s": .05}}
        # Fix UTC only for this delivery and simulate 50 ms of transport. Real live-stream
        # expiry timers keep running; the receipt assertions share the delivery's browser task.
        deliver = """f => {
            const readNow = Date.now, receiptMs = readNow();
            Date.now = () => receiptMs;
            try {
                f.freshness.evaluated_at_utc_s = receiptMs/1000 - .05;
                onStatus({data: JSON.stringify(f)});
                return {label: document.querySelector('#age-label').textContent,
                        age: document.querySelector('#source-age').textContent,
                        decision: document.querySelector('#decision').textContent};
            } finally { Date.now = readNow; }
        }"""
        received = page.evaluate(deliver, base)
        assert received["label"] == "После публикации записи"
        assert received["age"] == "70 мс"  # 20 ms at the node plus 50 ms in transport
        page.evaluate("checkLiveStream(state.lastStatusArrival + 501)")
        assert page.inner_text("#decision") == "ОШИБКА"
        assert page.inner_text("#clear") == "не определена"
        assert page.evaluate("state.cab.clearEnd") == 0
        # A new fresh message permits recovery; a later pause holds an outstanding STOP.
        stop = dict(base, obstacle=True, decision="STOP", nearest_distance=50, clear_distance=50,
                    freshness=dict(base["freshness"], go_allowed=False))
        page.evaluate(deliver, stop)
        page.evaluate("checkLiveStream(state.lastStatusArrival + 501)")
        assert page.inner_text("#decision") == "СТОП"
        assert "СТОП СОХРАНЁН" in check_dashboard.banner_text(page)
        assert page.evaluate("state.cab.clearEnd") == 0
        assert "последнее" in page.text_content("#dist")
        # Restart/first-epoch invalid clear cannot release the browser's held STOP.
        invalid_epoch = dict(base, freshness=dict(base["freshness"], valid=False, reason="epoch_unconfirmed"))
        page.evaluate(deliver, invalid_epoch)
        assert page.inner_text("#decision") == "СТОП"
        assert "СТОП СОХРАНЁН" in check_dashboard.banner_text(page)
        received = page.evaluate(deliver, base)
        assert received["decision"] == "НЕ ОБНАРУЖЕНО"
        aging = dict(base, freshness=dict(base["freshness"], source_age_s=.4))
        page.evaluate(deliver, aging)
        page.evaluate("checkLiveStream(state.lastStatusArrival + 101)")
        assert page.inner_text("#decision") == "ОШИБКА"
        # A buffered message must not receive a new freshness window on arrival.
        # Read the rejection reason in the same browser task as delivery: the live expiry
        # timer may subsequently replace it with status_stream_stale, still correctly FAULT.
        reason = page.evaluate("f => { f.freshness.evaluated_at_utc_s = Date.now()/1000 - 2; onStatus({data: JSON.stringify(f)}); return state.last.freshness.reason; }", base)
        assert page.inner_text("#decision") == "ОШИБКА"
        assert reason == "status_transport_stale"
        reason = page.evaluate("f => { f.freshness.evaluated_at_utc_s = Date.now()/1000 + 2; onStatus({data: JSON.stringify(f)}); return state.last.freshness.reason; }", base)
        assert page.inner_text("#decision") == "ОШИБКА"
        assert reason == "status_clock_skew"
        reason = page.evaluate("f => { onStatus({data: JSON.stringify(f)}); return state.last.freshness.reason; }", base)
        assert reason == "status_clock_unknown"
        page.evaluate("f => { f.freshness.evaluated_at_utc_s = Date.now()/1000 - 2; onStatus({data: JSON.stringify(f)}); }", stop)
        assert "СТОП СОХРАНЁН" in check_dashboard.banner_text(page)
        assert page.evaluate("state.last.stop_source_stamp") == 1.0
        page.evaluate(deliver, base)
        # The explicit contract takes precedence over a contradictory GO field.
        invalid = dict(base, freshness={"valid": False, "reason": "source_stale"})
        page.evaluate("f => onStatus({data: JSON.stringify(f)})", invalid)
        assert page.inner_text("#decision") == "ОШИБКА"
        assert page.evaluate("state.cab.clearEnd") == 0
        # Historical playback remains a snapshot; the live transport timer cannot alter it.
        page.evaluate("window.resense.setMode('replay')")
        page.evaluate("f => window.resense.applyResult(f)", base)
        page.evaluate("checkLiveStream(performance.now() + 10000)")
        assert page.inner_text("#decision") == "НЕ ОБНАРУЖЕНО"
        b.close()


def test_dashboard_builtin_demo_and_summary():
    """The jury can exercise the dashboard even when no bag or generated JSONL is available."""
    if not _browser_available():
        pytest.skip("playwright + chromium not available")
    from playwright.sync_api import sync_playwright
    import check_dashboard
    with sync_playwright() as p:
        b = _launch(p)
        page = b.new_page()
        page.goto("file://" + check_dashboard.INDEX, wait_until="domcontentloaded")
        page.wait_for_function("window.resense !== undefined")
        page.click("#demo")
        page.evaluate("window.resense.pause()")
        state = page.evaluate("({frames: window.resense.state.frames.length, summary: window.resense.state.summary})")
        assert state["frames"] == 60
        assert state["summary"] == {
            "frames": 60, "status_snapshots": 0, "stop_episodes": 1, "alarm_frames": 36, "warning_frames": 4,
            "nearest_m": pytest.approx(40.0), "max_detect_ms": 49,
        }
        page.locator("#summary-card summary").click()
        assert page.inner_text("#s-alarms") == "1 / 36"
        assert page.inner_text("#s-nearest") == "40.0 м"
        assert page.inner_text("#decision") == "НЕ ОБНАРУЖЕНО"
        assert page.inner_text("#health") == "норма"
        assert page.is_enabled("#export-report")
        b.close()


def test_dashboard_banner_honors_health_and_explicit_fault():
    """No obstacle flag must not turn a health warning or watchdog FAULT into a green banner."""
    if not _browser_available():
        pytest.skip("playwright + chromium not available")
    from playwright.sync_api import sync_playwright
    import check_dashboard
    with sync_playwright() as p:
        b = _launch(p)
        page = b.new_page()
        page.goto("file://" + check_dashboard.INDEX, wait_until="domcontentloaded")
        page.wait_for_function("window.resense !== undefined")
        cases = [
            ({"health": {"level": "error"}}, "bad", "ОШИБКА", "ОШИБКА"),
            ({"decision": "GO", "health": {"level": "error", "decision_level": "error"}},
             "bad", "ОШИБКА", "ОШИБКА"),
            ({"decision": "FAULT", "health": {"level": "ok"}}, "bad", "ОШИБКА", "ОШИБКА"),
            ({"decision": "CAUTION", "health": {"level": "error", "decision_level": "error"}},
             "bad", "ОШИБКА", "ОШИБКА"),
            ({"decision": "GO", "health": {"level": "warn", "decision_level": "warn"}},
             "warn", "ВНИМАНИЕ", "ВНИМАНИЕ"),
            ({"health": {"level": "warn", "decision_level": "warn"}}, "warn", "ВНИМАНИЕ", "ВНИМАНИЕ"),
            ({"health": {"level": "warn", "decision_level": "ok"}}, "clear", "ПРЕПЯТСТВИЕ НЕ ОБНАРУЖЕНО", "НЕ ОБНАРУЖЕНО"),
            ({"decision": "GO", "health": {"level": "warn", "decision_level": "ok"}},
             "clear", "ПРЕПЯТСТВИЕ НЕ ОБНАРУЖЕНО", "НЕ ОБНАРУЖЕНО"),
            ({"obstacle": True, "nearest_distance": 55.6, "health": {"level": "error"}}, "bad", "ПРЕПЯТСТВИЕ  55.6 м", "СТОП"),
        ]
        for extra, color, title, decision in cases:
            frame = {"stamp": 1.0, "obstacle": False, "warning": False, "nearest_distance": None,
                     "detections": [], "warnings": [], "clear_distance": 0.0, **extra}
            page.evaluate("frame => window.resense.applyResult(frame)", frame)
            assert page.get_attribute("#banner", "class") == color
            assert check_dashboard.banner_text(page).startswith(title)
            assert page.inner_text("#decision") == decision
        assert "Дальность контроля" in page.inner_text("#safety-card")
        assert "могут быть пропущены" in page.inner_text("#safety-card")
        b.close()


def test_dashboard_reconnect_ignores_old_stream_and_closes_on_replay():
    """An old ROS connection cannot overwrite the new stream or remain open in replay mode."""
    if not _browser_available():
        pytest.skip("playwright + chromium not available")
    from playwright.sync_api import sync_playwright
    import check_dashboard
    with sync_playwright() as p:
        b = _launch(p)
        page = b.new_page()
        page.goto("file://" + check_dashboard.INDEX, wait_until="load")
        page.wait_for_function("window.resense !== undefined")
        page.evaluate("""() => {
            window.__fakeRos = [];
            window.ROSLIB = {
              Ros: class {
                constructor() { this.handlers = {}; this.closed = false; window.__fakeRos.push(this); }
                on(name, fn) { this.handlers[name] = fn; }
                emit(name) { if (name === 'close') this.closed = true; if (this.handlers[name]) this.handlers[name](); }
                close() { this.closed = true; this.emit('close'); }
                publish(payload) {
                  const data = typeof payload === 'string' ? payload : JSON.stringify(payload);
                  this.statusCallback({data});
                }
              },
              Topic: class {
                constructor({ros}) { this.ros = ros; }
                subscribe(fn) { this.ros.statusCallback = fn; }
              }
            };
        }""")
        page.click("#connect")
        page.wait_for_function("window.__fakeRos.length === 1")
        assert page.locator("body").evaluate("el => el.classList.contains('live-stale')")
        assert page.locator("#panel-cab .stale-veil").is_visible()
        assert page.locator("#safety-card .stale-veil").is_visible()

        fresh = {"snapshot_kind": "frame", "obstacle": False, "warning": False, "decision": "GO", "nearest_distance": None,
                 "detections": [], "warnings": [], "clear_distance": 120, "health": {"level": "ok"},
                  "freshness": {"valid": True, "reason": "current", "go_allowed": True, "source_age_s": .02,
                                "mode": "replay", "clock_reference": "publisher_utc", "queue_lag_s": 0,
                               "residence_age_s": .01, "max_result_age_s": .5, "future_tolerance_s": .05}}
        page.evaluate("s => window.__fakeRos[0].publish({...s, freshness: {...s.freshness, evaluated_at_utc_s: Date.now()/1000}})", fresh)
        assert not page.locator("body").evaluate("el => el.classList.contains('live-stale')")

        page.click("#connect")
        page.wait_for_function("window.__fakeRos.length === 2")
        stop = {**fresh, "obstacle": True, "decision": "STOP", "nearest_distance": 50, "clear_distance": 50,
                "freshness": {**fresh["freshness"], "go_allowed": False}}
        page.evaluate("s => window.__fakeRos[1].publish({...s, freshness: {...s.freshness, evaluated_at_utc_s: Date.now()/1000}})", stop)
        title = page.inner_text("#banner-title")
        assert title == "ПРЕПЯТСТВИЕ 50.0 м"
        # Reconnect invalidates the old result synchronously, before a timer or new status can run.
        snapshot = page.evaluate("""s => {
            window.__fakeRos[1].publish({...s, freshness: {...s.freshness, evaluated_at_utc_s: Date.now()/1000}});
            document.getElementById('connect').click();
            return {valid: state.last.freshness.valid, held: state.last.stop_held,
                    distance: document.getElementById('dist').textContent};
        }""", stop)
        assert snapshot == {"valid": False, "held": True, "distance": "50.0 м (последнее)"}
        assert page.evaluate("window.__fakeRos.length === 3 && window.__fakeRos[1].closed")
        # An error also expires the current result immediately while retaining STOP.
        snapshot = page.evaluate("""s => {
            window.__fakeRos[2].publish({...s, freshness: {...s.freshness, evaluated_at_utc_s: Date.now()/1000}});
            window.__fakeRos[2].emit('error');
            return {valid: state.last.freshness.valid, held: state.last.stop_held};
        }""", stop)
        assert snapshot == {"valid": False, "held": True}
        page.evaluate("s => window.__fakeRos[2].publish({...s, freshness: {...s.freshness, evaluated_at_utc_s: Date.now()/1000}})", stop)
        page.evaluate("window.__fakeRos[2].emit('close')")
        assert page.inner_text("#banner-title") == "СТОП СОХРАНЁН: НЕТ АКТУАЛЬНЫХ ДАННЫХ"
        assert page.locator("body").evaluate("el => el.classList.contains('live-stale')")
        page.evaluate("window.__fakeRos[0].publish({obstacle:false, decision:'FAULT', health:{level:'error'}})")
        page.evaluate("window.__fakeRos[0].emit('close')")
        assert page.inner_text("#banner-title") != title
        assert page.inner_text("#decision") == "СТОП"

        page.evaluate("window.resense.setMode('replay')")
        assert page.evaluate("window.resense.state.mode") == "replay"
        assert page.evaluate("window.__fakeRos.every(ros => ros.closed)")
        replay = {"obstacle": False, "warning": False, "decision": "GO", "nearest_distance": None,
                  "detections": [], "warnings": [], "clear_distance": 80, "health": {"level": "ok"}}
        page.evaluate("r => window.resense.applyResult(r)", replay)
        title = page.inner_text("#banner-title")
        page.evaluate("window.__fakeRos[1].publish({obstacle:false, decision:'FAULT', health:{level:'error'}})")
        assert page.inner_text("#banner-title") == title == "ПРЕПЯТСТВИЕ НЕ ОБНАРУЖЕНО"
        assert not page.locator("body").evaluate("el => el.classList.contains('live-stale')")
        b.close()


def test_dashboard_fits_169_screen_and_cab_view_marks_the_obstacle():
    """A presentation screen shows the full dashboard; extra detail remains available in the side list."""
    if not _browser_available():
        pytest.skip("playwright + chromium not available")
    from playwright.sync_api import sync_playwright
    import check_dashboard
    with sync_playwright() as p:
        b = _launch(p)
        for width, height in ((1280, 720), (1366, 768), (1600, 900), (1920, 1080)):
            page = b.new_page(viewport={"width": width, "height": height})
            page.goto("file://" + check_dashboard.INDEX, wait_until="domcontentloaded")
            page.wait_for_function("window.resense !== undefined")
            page.click("#demo")
            page.evaluate("window.resense.pause(); window.resense.seek(30)")   # STOP, person at 79 m
            layout = page.evaluate("""() => ({ pageHeight: document.documentElement.scrollHeight,
                pageWidth: document.documentElement.scrollWidth, viewportHeight: innerHeight,
                viewportWidth: innerWidth })""")
            assert layout["pageHeight"] <= height + 1 and layout["pageWidth"] <= width + 1, layout
            cab = page.evaluate("window.resense.state.cab")
            assert cab["width"] > 600 and cab["height"] >= 360
            (box,) = cab["boxes"]
            assert box["zone"] == "gauge" and box["label"] == "ПРЕПЯТСТВИЕ · 79.0 м"
            assert 0 <= box["x0"] < box["x1"] <= cab["width"] and 0 <= box["y0"] < box["y1"] <= cab["height"]
            # the person stands on the track axis: its box is within the middle fifth of the view
            assert abs((box["x0"] + box["x1"]) / 2 - cab["width"] / 2) < cab["width"] / 10
            assert cab["clearEnd"] == pytest.approx(79.0, abs=0.1)
            assert cab["inset"] and cab["inset"]["zone"] == "gauge"
            page.click("#tab-plan")
            assert page.is_visible("#panel-plan") and not page.is_visible("#panel-cab")
            page.wait_for_function("Math.abs(document.querySelector('#top').width - document.querySelector('#top').clientWidth) <= 1")
            page.locator("#detector-card summary").click()
            assert page.locator("#detector-card").evaluate("section => section.open")
            page.locator('.top-nav a[href="#node-card"]').click()
            assert page.locator("#node-card").evaluate("section => section.open")
            page.click("#tab-cab")
            page.evaluate("window.resense.seek(59)")                           # GO again
            cab = page.evaluate("window.resense.state.cab")
            assert cab["boxes"] == [] and cab["inset"] is None and cab["clearEnd"] == pytest.approx(145.0)
            page.close()
        b.close()


def test_dashboard_shortcuts_work_after_clicking_a_control():
    """A clicked button keeps the focus (review of PR #12): ←/→ still step the replay, and Space
    toggles play/pause exactly once, on the play button (its own click) and on a view tab."""
    if not _browser_available():
        pytest.skip("playwright + chromium not available")
    from playwright.sync_api import sync_playwright
    import check_dashboard
    idx, playing = "window.resense.state.idx", "window.resense.state.playing"
    with sync_playwright() as p:
        b = _launch(p)
        page = b.new_page()
        page.goto("file://" + check_dashboard.INDEX, wait_until="domcontentloaded")
        page.wait_for_function("window.resense !== undefined")
        page.click("#demo")
        page.evaluate("window.resense.pause(); window.resense.seek(5)")
        assert page.evaluate("document.activeElement.id") == "demo"
        page.keyboard.press("ArrowRight")
        assert page.evaluate(idx) == 6
        page.keyboard.press("ArrowLeft")
        assert page.evaluate(idx) == 5
        page.click("#stepfwd")
        page.keyboard.press("ArrowRight")
        assert page.evaluate(idx) == 7
        page.click("#play")
        assert page.evaluate(playing) is True
        page.keyboard.press("Space")                    # the button's own click, not a second toggle
        assert page.evaluate(playing) is False
        page.click("#tab-plan")
        page.keyboard.press("Space")
        assert page.evaluate(playing) is True
        page.keyboard.press("Space")
        assert page.evaluate(playing) is False
        at = page.evaluate(idx)
        page.keyboard.press("ArrowLeft")                # the tabs' own key: switches the view, no step
        assert page.is_visible("#panel-cab") and page.evaluate(idx) == at
        page.click("#url")                              # text entry keeps its keys
        page.keyboard.press("ArrowRight")
        page.keyboard.press("Space")
        assert page.evaluate(idx) == at and page.evaluate(playing) is False
        page.click("#demo")                             # the demo starts playing, the focus stays on «Демо»
        assert page.evaluate(playing) is True
        page.evaluate("window.resense.seek(20)")
        page.keyboard.press("Space")                    # pauses; does not restart the demo from frame 0
        assert page.evaluate(playing) is False and page.evaluate(idx) >= 20
        b.close()


def test_dashboard_phone_width_has_16px_gutter_and_no_horizontal_scroll():
    if not _browser_available():
        pytest.skip("playwright + chromium not available")
    from playwright.sync_api import sync_playwright
    import check_dashboard
    with sync_playwright() as p:
        b = _launch(p)
        page = b.new_page(viewport={"width": 390, "height": 844})
        page.goto("file://" + check_dashboard.INDEX, wait_until="domcontentloaded")
        page.wait_for_function("window.resense !== undefined")
        page.click("#demo")
        page.evaluate("window.resense.pause(); window.resense.seek(30)")
        for tab in ("#tab-plan", "#tab-cab"):
            page.click(tab)
            layout = page.evaluate("""() => { const r = s => document.querySelector(s).getBoundingClientRect();
                return { scrollWidth: document.documentElement.scrollWidth, brand: r('.brand').left,
                         main: [r('main').left, r('main').right] }; }""")
            assert layout["scrollWidth"] <= 390, layout
            assert layout["brand"] == layout["main"][0] == 16 and layout["main"][1] == 390 - 16, layout
        b.close()


def test_dashboard_cab_view_on_the_real_node_stream():
    """The node's /resense/status stream from the Docker dry run on doubleT_obstacle: the fitted bed
    profile (floor_coef) places the 56 m object in the cab view."""
    if not _browser_available():
        pytest.skip("playwright + chromium not available")
    import gzip
    from playwright.sync_api import sync_playwright
    import check_dashboard
    text = gzip.open(os.path.join(ROOT, "docs", "evidence", "docker_2026-09-23", "obstacle_status.jsonl.gz"), "rt").read()
    with sync_playwright() as p:
        b = _launch(p)
        page = b.new_page(viewport={"width": 1600, "height": 1000})
        page.goto("file://" + check_dashboard.INDEX, wait_until="domcontentloaded")
        page.wait_for_function("window.resense !== undefined")
        assert page.evaluate("t => window.resense.loadText(t, 'obstacle_status.jsonl')", text) == 103
        idx = page.evaluate("window.resense.state.frames.findIndex(f => f.obstacle)")
        page.evaluate(f"window.resense.seek({idx})")
        cab = page.evaluate("window.resense.state.cab")
        gauge = [bx for bx in cab["boxes"] if bx["zone"] == "gauge"]
        assert gauge and gauge[0]["label"].startswith("ПРЕПЯТСТВИЕ · 56.")
        bx = gauge[0]
        assert 0 <= bx["x0"] < bx["x1"] <= cab["width"] and cab["height"] * 0.3 < bx["y1"] < cab["height"] * 0.8
        b.close()


def test_dashboard_uses_supplied_moscow_sans_visual_system():
    """The dashboard uses the supplied local fonts and Metro red with flat panels."""
    html = open(os.path.join(ROOT, "web", "index.html"), encoding="utf-8").read()
    css = open(os.path.join(ROOT, "web", "assets", "dashboard.css"), encoding="utf-8").read()
    assert 'href="assets/dashboard.css"' in html
    assert 'font-family: "Moscow Sans"' in css
    assert "--red: #e4000d" in css
    assert "box-shadow" not in css and "text-shadow" not in css
    for path in MOSCOW_SANS:
        assert os.path.getsize(path) > 20_000


def newest_ride_baseline():
    """The current gate baseline: the newest one (by its "created" stamp) that measured the ride; since
    27.09 the baselines are not all named *_ride* (regression_baseline_2026-09-27_quality.json)."""
    baselines = []
    for path in glob.glob(os.path.join(ROOT, "docs", "evidence", "results", "regression_baseline_*.json")):
        with open(path) as source:
            data = json.load(source)
        if data.get("ride", {}).get("available"):
            baselines.append((data["created"], data))
    return max(baselines, key=lambda item: item[0])[1]


def test_presentation_artifact_uses_the_organizers_slide_sequence():
    """The committed deck keeps the organizers' sequence and the current measured headlines."""
    assert os.path.getsize(PRESENTATION) > 1_000_000
    with zipfile.ZipFile(PRESENTATION) as zf:
        assert zf.testzip() is None
        root = ET.fromstring(zf.read("ppt/presentation.xml"))
        ns = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
              "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
        slide_ids = list(root.find("p:sldIdLst", ns))
        assert len(slide_ids) == 16
        rel_root = ET.fromstring(zf.read("ppt/_rels/presentation.xml.rels"))
        rels = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rel_root}
        slide_paths = ["ppt/" + rels[s.attrib[f"{{{ns['r']}}}id"]] for s in slide_ids]
        text = " ".join(
            " ".join(ET.fromstring(zf.read(path)).itertext()) for path in slide_paths
        ).replace("\u00a0", " ")
    for required in ("ReSense", "КОМАНДА", "КОРОТКО О РЕШЕНИИ", "ГЛАВНЫЙ КАДР", "13 759", "docker load"):
        assert required in text
    baseline = newest_ride_baseline()
    labelled = baseline["recordings"]["doubleT_obstacle"]["labelled"]["per_label"]
    person, rail = labelled["person_crossing"], labelled["object_on_rail_from_frame_75"]
    objects = baseline["set_O"]["objects"]
    top = objects["big_above"]
    for required in (
        str(baseline["five_empty"]["alarm_events"]),
        str(baseline["ride"]["alarm_events"]),
        f"{baseline['ride']['alarm_events'] / 13:.1f}".replace(".", ","),
        f"{person['hits']} из {person['frames']}",
        f"{rail['hits']} из {rail['frames']}",
        f"{baseline['set_O']['inside_objects_with_stop']} из {baseline['set_O']['inside_objects']}",
        f"{top['stop_frames']} из {top['visible_frames']}",          # the 2 x 2 m box at the envelope top
        f"непрерывно с {int(top['first_stop_m'] + 0.5)} м",
        f"доска — с {int(objects['long_low_on_rails']['first_stop_m'] + 0.5)} м",
    ):
        assert required in text
    # the test count on the slides is a full local pass, at least the 667 of 26.09
    counts = [int(n.replace(" ", "")) for n in re.findall(r"(\d[\d ]*)\+? тестов", text)]
    assert counts and min(counts) >= 667
    assert "релиз v1.0.0" not in text
    assert "пропущен" not in text                               # every in-envelope object gets a STOP
    assert "42–64" not in text                                  # the numpy timing of 23.09, not the shipped path
    assert "~149" not in text                                   # the 90 % hold counts misses before the first STOP
    assert "Привет, участник хакатона" not in text
    assert "Любое крепление" not in text
    assert "стыкуется с системой торможения" not in text
    assert "единицы процентов AP" not in text
    assert "/resense/status" in text


def test_overview_video_cards_follow_the_current_gate_baseline():
    """The overview video's cut table (scripts/make_overview_video.py) names the measured headlines of
    the newest ride baseline, picked as the deck test picks it: the ride card, the person and the
    object on the rail. A new baseline without a rebuilt video fails here."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("resense_make_overview_video_web",
                                                  os.path.join(ROOT, "scripts", "make_overview_video.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    baseline = newest_ride_baseline()
    events = baseline["ride"]["alarm_events"]
    cards = [c for b in module.BLOCKS for c in b["cards"]]
    ride = [c for c in cards if c["kind"] == "num" and "поездке" in c["label"]]
    assert ride, "no ride card in the cut table"
    for c in ride:
        assert f"({events} за 13 км)" in c["label"]
        assert c["big"] == f"{events / 13:.1f} на км".replace(".", ",")
    labelled = baseline["recordings"]["doubleT_obstacle"]["labelled"]["per_label"]
    person, rail = labelled["person_crossing"], labelled["object_on_rail_from_frame_75"]
    bigs = {c["big"] for c in cards if c["kind"] == "num"}
    assert f"{person['hits']} из {person['frames']}" in bigs
    # the object on the rail: the card shows the node path on the original recording (123 of 126,
    # docs/evidence/node_input_2026-09-28) and names the baseline's 1 cm cache replay in its label
    rail_cards = [c for c in cards if c["kind"] == "num" and "предметом на рельсе" in c["label"]]
    assert rail_cards
    for c in rail_cards:
        assert c["big"].endswith(f" из {rail['frames']}")
        assert f"на кэше 1 см — {rail['hits']}" in c["label"]
    assert module.check_table(files=False) == []


# --------------------------------------------------------------------------- F. label tool -> gt.json
GT_KEYS = {"kind", "size", "distance", "lateral", "yaw_deg", "reflectivity", "label", "in_gauge", "n_points"}


def test_label_tool_exports_inject_shaped_gt(tiny_run, tmp_path):
    if not _browser_available():
        pytest.skip("playwright + chromium not available")
    from playwright.sync_api import sync_playwright
    from resense.metrics import GTObstacle
    out, _ = tiny_run
    with sync_playwright() as p:
        b = _launch(p)
        page = b.new_page()
        page.goto("file://" + LABEL_TOOL, wait_until="domcontentloaded")
        page.wait_for_function("window.resenseLabel !== undefined")
        page.set_input_files("#file-jsonl", out)
        page.wait_for_function("Object.keys(window.resenseLabel.state.results).length > 0")
        keys = page.evaluate("Object.keys(window.resenseLabel.state.results).sort()")
        assert keys[0] == "00000" and keys[-1] == "00013" and len(keys) == 14   # frame index, 5 digits
        # a frame where the detector confirmed the person: prefill from the detection, then edit
        det_key = page.evaluate("Object.keys(window.resenseLabel.state.results).sort().find(k => window.resenseLabel.state.results[k].obstacle)")
        page.evaluate(f"window.resenseLabel.select('{det_key}')")
        page.click("#add-from-det")
        page.select_option("select[data-f=kind]", "person")
        page.fill("input[data-f=label]", "person_real")
        page.dispatch_event("input[data-f=label]", "change")
        page.fill("input[data-f=lateral]", "1.30")
        page.dispatch_event("input[data-f=lateral]", "change")
        assert page.is_checked("input[data-f=in_gauge]") is True  # 1.30 - 0.25 = 1.05
        page.fill("input[data-f=lateral]", "1.31")
        page.dispatch_event("input[data-f=lateral]", "change")
        assert page.is_checked("input[data-f=in_gauge]") is False
        page.select_option("select[data-f=kind]", "plank")
        page.fill("input[data-f=lateral]", "2.0")
        page.dispatch_event("input[data-f=lateral]", "change")
        assert page.is_checked("input[data-f=in_gauge]") is False
        page.fill("input[data-f=yaw_deg]", "90")
        page.dispatch_event("input[data-f=yaw_deg]", "change")
        assert page.is_checked("input[data-f=in_gauge]") is True  # rotated 2 m plank crosses the edge
        page.select_option("select[data-f=kind]", "person")
        page.fill("input[data-f=lateral]", "-2.5")           # outside the gauge -> in_gauge auto-unchecks
        page.dispatch_event("input[data-f=lateral]", "change")
        assert page.is_checked("input[data-f=in_gauge]") is False
        page.check("input[data-f=in_gauge]")                 # set by hand (e.g. reaching in from above) ...
        page.dispatch_event("input[data-f=in_gauge]", "change")
        page.fill("input[data-f=size2]", "1.6")
        page.dispatch_event("input[data-f=size2]", "change")
        page.fill("input[data-f=lateral]", "-2.5")
        page.dispatch_event("input[data-f=lateral]", "change")
        assert page.is_checked("input[data-f=in_gauge]") is True    # ... and kept when the object is edited
        page.uncheck("input[data-f=in_gauge]")
        page.dispatch_event("input[data-f=in_gauge]", "change")
        # a hand-typed frame, marked as checked and clear
        page.fill("#new-frame", "42")
        page.click("#add-frame")
        page.check("#checked")
        # export through the real download button and through the API
        with page.expect_download() as dl:
            page.click("#export")
        path = str(tmp_path / "gt.json")
        dl.value.save_as(path)
        gt_api = page.evaluate("window.resenseLabel.exportGT()")
        b.close()
    gt = json.load(open(path))
    assert gt == gt_api
    assert set(gt) == {det_key, "00042"}
    assert gt["00042"] == []
    (o,) = gt[det_key]
    assert set(o) == GT_KEYS
    assert o["kind"] == "person" and o["label"] == "person_real" and o["in_gauge"] is False
    assert o["lateral"] == -2.5 and 40.0 <= o["distance"] <= 72.0 and o["n_points"] >= 1
    assert len(o["size"]) == 3 and all(isinstance(v, (int, float)) for v in o["size"])
    g = GTObstacle.from_dict(o)                                   # what resense eval reads
    assert g.distance == o["distance"] and g.in_gauge is False
