"""P2 regression checks for source switches, malformed records and label round trips."""
import json

from test_web import LABEL_TOOL


def dashboard(page):
    import check_dashboard
    page.goto("file://" + check_dashboard.INDEX)
    page.wait_for_function("window.resense !== undefined")


def test_replay_controls_cannot_publish_old_frames_into_live_view(page):
    dashboard(page)
    page.click("#demo")
    page.evaluate("resense.pause(); resense.seek(0)")
    page.evaluate("""() => {
        window.ROSLIB = {
            Ros: class { on() {} close() {} },
            Topic: class { subscribe() {} }
        };
    }""")
    page.click("#connect")
    for control in ("#play", "#stepback", "#stepfwd", "#seek"):
        assert page.is_disabled(control)
    # Public replay hooks and keyboard shortcuts must obey the same source boundary.
    page.evaluate("resense.play(); resense.step(1); resense.seek(0)")
    page.keyboard.press("ArrowRight")
    page.keyboard.press("Space")
    assert page.evaluate("resense.state.mode") == "live"
    assert page.evaluate("resense.state.playing") is False
    assert page.evaluate("resense.state.last") is None
    assert page.locator("#panel-cab .stale-veil").is_visible()
    assert page.text_content("#clear") in ("—", "не определена")


def test_empty_replay_clears_previous_result_and_can_recover(page):
    dashboard(page)
    page.click("#demo")
    page.evaluate("resense.pause(); resense.seek(30)")
    assert page.evaluate("resense.state.cab.boxes.length") > 0
    assert page.evaluate("resense.loadText('not json', 'empty.jsonl')") == 0
    assert page.evaluate("resense.state.cab.boxes") == []
    assert page.evaluate("resense.state.cab.clearEnd") == 0
    assert page.text_content("#dist") == "—"
    assert page.text_content("#decision") != "СТОП"
    page.click("#demo")
    page.evaluate("resense.pause()")
    assert page.evaluate("resense.state.frames.length") == 60


def test_result_import_rejects_bad_shapes_and_accepts_unknown_stop_distance(page):
    dashboard(page)
    clear = {"obstacle": False, "decision": "GO", "detections": [], "warnings": []}
    bad = [
        {**clear, "obstacle": "false"},
        {**clear, "nearest_distance": "55"},
        {**clear, "detections": {}},
        {**clear, "detections": [{}]},
        {**clear, "track": {"axis_valid": "120"}},
        {**clear, "health": {"messages": "broken"}},
        {**clear, "timing_ms": {"total": "12"}},
        {**clear, "decision": "NOT_A_DECISION"},
    ]
    stop = {**clear, "obstacle": True, "decision": "STOP", "nearest_distance": None}
    text = "\n".join(json.dumps(frame) for frame in [*bad, clear, stop])
    assert page.evaluate("t => resense.loadText(t, 'mixed.jsonl')", text) == 2
    page.evaluate("resense.seek(1)")
    assert page.text_content("#decision") == "СТОП"
    assert page.text_content("#dist") == "—"
    assert page.evaluate("resense.state.summary.nearest_m") is None
    # Malformed live records cannot clear a held STOP or reset the receipt timer.
    page.evaluate("resense.setMode('live')")
    page.evaluate("""s => onStatus({data: JSON.stringify({...s, snapshot_kind: 'frame', freshness: {
        reason: 'current', mode: 'replay', clock_reference: 'publisher_utc', queue_lag_s: 0,
        valid: true, go_allowed: false, source_age_s: 0, residence_age_s: 0, max_result_age_s: .5,
        future_tolerance_s: .05, evaluated_at_utc_s: Date.now()/1000
    }})})""", stop)
    page.evaluate("checkLiveStream(performance.now(), true)")
    before = page.evaluate("resense.state.lastStatusArrival")
    for frame in bad:
        page.evaluate("f => onStatus({data: JSON.stringify(f)})", frame)
    assert page.evaluate("resense.state.lastStatusArrival") == before
    assert page.text_content("#decision") == "СТОП"


def test_label_import_roundtrip_preserves_explicit_gauge_and_replaces_clear_frame(page):
    page.goto("file://" + LABEL_TOOL)
    obstacle = {"kind": "person", "distance": 50, "lateral": 0,
                "size": [.4, .5, 1.7], "in_gauge": True, "label": 'person "A" <reviewed>'}
    page.evaluate("o => resenseLabel.loadGT({'00042': [o]})", obstacle)
    assert page.input_value('input[data-f="label"]') == obstacle["label"]
    page.fill('input[data-f="lateral"]', '3')
    page.dispatch_event('input[data-f="lateral"]', 'change')
    assert page.is_checked('input[data-f="in_gauge"]')
    assert page.input_value('input[data-f="label"]') == obstacle["label"]
    page.evaluate("resenseLabel.loadGT({'00042': []})")
    assert page.evaluate("resenseLabel.exportGT()") == {"00042": []}
    page.evaluate("o => resenseLabel.loadGT({'00042': [o]})", obstacle)
    assert not page.is_checked("#checked")
    assert len(page.evaluate("resenseLabel.exportGT()['00042']")) == 1


def test_label_import_is_atomic_and_does_not_treat_invalid_data_as_clear(page):
    page.goto("file://" + LABEL_TOOL)
    page.evaluate("resenseLabel.loadGT({'00042': []})")
    for data in ({"00042": None}, {"00042": {}}, {"bad-frame": []},
                 {"00043": [], "00044": [None]}, {"00043": [{"distance": "far"}]}):
        error = page.evaluate("""data => {
            try { resenseLabel.loadGT(data); return null; }
            catch (error) { return error.message; }
        }""", data)
        assert error
        assert page.evaluate("resenseLabel.exportGT()") == {"00042": []}


def test_invalid_live_status_keeps_panels_covered_until_current_result(page):
    dashboard(page)
    frame = {"obstacle": False, "decision": "GO", "clear_distance": 120,
             "freshness": {"valid": False, "reason": "epoch_unconfirmed"}}
    page.evaluate("f => onStatus({data: JSON.stringify(f)})", frame)
    assert page.locator("#panel-cab .stale-veil").is_visible()
    assert page.text_content("#clear") == "не определена"
    page.evaluate("""f => onStatus({data: JSON.stringify({...f, snapshot_kind: 'frame', freshness: {
        reason: 'current', mode: 'replay', clock_reference: 'publisher_utc', queue_lag_s: 0,
        valid: true, go_allowed: true, source_age_s: 0, residence_age_s: 0, max_result_age_s: .5,
        future_tolerance_s: .05, evaluated_at_utc_s: Date.now()/1000
    }})})""", frame)
    assert not page.locator("#panel-cab .stale-veil").is_visible()
