"""Tests for the P2 deliverables (RViz layout, Foxglove layout, demo run, dashboard replay, label tool).

Run from the repository root:  python -m pytest -q web/demo
(``testpaths`` in pyproject.toml only lists ``tests/``, so the plain ``pytest -q`` does not
collect this file — add ``web/demo`` there if the team wants it in CI.)  Everything runs
without the organizers' dataset; the browser tests skip when Playwright or Chromium is missing.
"""
import json
import os
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "web", "demo"))

RVIZ = os.path.join(ROOT, "ros2_ws", "src", "resense_ros", "rviz", "resense.rviz")
FOX = os.path.join(ROOT, "web", "foxglove_layout.json")
LABEL_TOOL = os.path.join(ROOT, "web", "label_tool.html")
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
    assert r["observed"][0][1].startswith("PATH CLEAR")
    assert r["nearest_min_m"] is not None and 40.0 <= r["nearest_min_m"] <= 72.0
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
        assert check_dashboard.banner_text(page) == "OBSTACLE  55.6 m"
        assert page.inner_text("#n-dropped").startswith("2")       # node stats are shown when present
        assert "notice" in page.get_attribute("#node-card", "class")
        b.close()


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
        page.fill("input[data-f=lateral]", "-2.5")           # outside the gauge -> in_gauge auto-unchecks
        page.dispatch_event("input[data-f=lateral]", "change")
        assert page.is_checked("input[data-f=in_gauge]") is False
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
