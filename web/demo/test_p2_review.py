"""Full P2 review: consumer contract, reporting, annotation and demo tooling."""
import json

import pytest

from test_frontend_boundaries import dashboard
from test_web import LABEL_TOOL


def current(obstacle=False):
    return {"stamp": 10, "frame_id": "lidar", "snapshot_kind": "frame", "obstacle": obstacle,
            "decision": "STOP" if obstacle else "GO", "nearest_distance": 50 if obstacle else None,
            "detections": [], "warnings": [], "clear_distance": 50 if obstacle else 120,
            "freshness": {"valid": True, "reason": "current", "go_allowed": not obstacle, "mode": "replay",
                          "clock_reference": "publisher_utc", "queue_lag_s": 0,
                          "source_age_s": .01, "residence_age_s": .01,
                          "max_result_age_s": .5, "future_tolerance_s": .05}}


def deliver(page, frame):
    return page.evaluate("""f => {
        f.freshness.evaluated_at_utc_s = Date.now()/1000;
        onStatus({data: JSON.stringify(f)});
        return {decision: document.querySelector('#decision').textContent,
                held: state.last.stop_held, valid: state.last.freshness.valid};
    }""", frame)


def test_live_contract_rejects_contradictions_and_preserves_stop(page):
    dashboard(page)
    cases = [
        {"snapshot_kind": "watchdog"}, {"stop_held": True}, {"node": {"catchup": True}},
        {"freshness": {"queue_lag_s": .1}}, {"freshness": {"mode": "unknown"}},
        {"freshness": {"clock_reference": "acquisition_utc"}},
        {"freshness": {"reason": "epoch_unconfirmed"}},
        {"freshness": {"go_allowed": False}},
        {"health": {"level": "error"}}, {"decision": "FAULT"},
    ]
    for change in cases:
        deliver(page, current(True))
        frame = current()
        if "freshness" in change:
            frame["freshness"].update(change["freshness"])
        else:
            frame.update(change)
        result = deliver(page, frame)
        assert result == {"decision": "СТОП", "held": True, "valid": False}, change
        assert page.evaluate("state.cab.clearEnd") == 0
    assert deliver(page, current())["decision"] == "НЕ ОБНАРУЖЕНО"


def test_replay_missing_health_uses_offline_decision_and_summary_matches_display(page, tmp_path):
    dashboard(page)
    frames = [
        {"obstacle": False, "warning": False},
        {"obstacle": False, "decision": "STOP", "nearest_distance": 42},
        {"obstacle": False, "decision": "CAUTION"},
        {"obstacle": True, "nearest_distance": 40},
        {"snapshot_kind": "watchdog", "obstacle": True, "nearest_distance": 1},
    ]
    page.evaluate("t => resense.loadText(t, 'legacy.jsonl')", '\n'.join(map(json.dumps, frames)))
    assert page.text_content("#decision") == "НЕ ОБНАРУЖЕНО"
    assert page.evaluate("state.summary.stop_episodes") == 2
    assert page.evaluate("state.summary.alarm_frames") == 2
    assert page.evaluate("state.summary.warning_frames") == 1
    assert page.evaluate("state.summary.nearest_m") == 40
    assert page.evaluate("state.summary.frames") == 4
    assert page.evaluate("state.summary.status_snapshots") == 1
    assert page.evaluate("'alarm_events' in state.summary") is False
    with page.expect_download() as download:
        page.locator('#summary-card summary').click()
        page.click('#export-report')
    target = tmp_path / 'report.json'
    download.value.save_as(target)
    report = json.loads(target.read_text())
    assert report['schema_version'] == 2
    assert report['source'] == 'legacy.jsonl'
    assert report['summary']['stop_episodes'] == 2


def test_delayed_file_read_cannot_override_new_source(page):
    dashboard(page)
    page.evaluate("""() => {
        window.readers = [];
        window.FileReader = class { constructor() { readers.push(this); } readAsText() {} };
        readReplayFile({name: 'old.jsonl'});
        resense.loadText(JSON.stringify({obstacle:false}), 'new.jsonl');
        readers[0].result = JSON.stringify({obstacle:true, nearest_distance:2});
        readers[0].onload();
    }""")
    assert page.evaluate("state.sourceName") == 'new.jsonl'
    assert page.evaluate("state.last.obstacle") is False


def test_cab_stop_never_extends_published_monitoring_cap(page):
    dashboard(page)
    frame = {**current(True), 'clear_distance': 20}
    page.evaluate("f => resense.loadText(JSON.stringify(f), 'cap.jsonl')", frame)
    assert page.evaluate('state.cab.clearEnd') == 20


def test_bundled_roslib_subscribes_expires_and_recovers_through_websocket(page):
    import time
    sockets, subscriptions = [], []

    def connected(socket):
        sockets.append(socket)
        socket.on_message(lambda message: subscriptions.append(json.loads(message)))

    page.route_web_socket('ws://localhost:9090/**', connected)
    dashboard(page)
    page.wait_for_function('typeof ROSLIB !== "undefined"')
    page.click('#connect')
    page.wait_for_function("document.querySelector('#conn').textContent === 'Подключено'")
    assert any(m.get('op') == 'subscribe' and m.get('topic') == '/resense/status' for m in subscriptions)

    def publish(frame):
        frame['freshness']['evaluated_at_utc_s'] = time.time()
        sockets[-1].send(json.dumps({'op': 'publish', 'topic': '/resense/status',
                                    'msg': {'data': json.dumps(frame)}}))

    publish(current(True))
    page.wait_for_function("document.querySelector('#banner-title').textContent.includes('50.0')")
    page.wait_for_function('state.streamStale === true')
    assert page.text_content('#decision') == 'СТОП'
    assert page.locator('#panel-cab .stale-veil').is_visible()
    publish(current())
    page.wait_for_function("document.querySelector('#decision').textContent === 'НЕ ОБНАРУЖЕНО'")
    assert not page.locator('#panel-cab .stale-veil').is_visible()
    sockets[-1].close()
    page.wait_for_function("document.querySelector('#decision').textContent === 'ОШИБКА'")


def test_label_results_need_absolute_indices_and_a_new_recording_resets_labels(page):
    page.goto('file://' + LABEL_TOOL)
    assert page.evaluate("resenseLabel.loadResults('{\"obstacle\":false}', 'no-index.jsonl')") == 0
    result = json.dumps({"frame": 42, "obstacle": False})
    page.evaluate("t => resenseLabel.loadResults(t, 'first.jsonl')", result)
    page.evaluate("resenseLabel.loadGT({'00042': []})")
    page.evaluate("t => resenseLabel.loadResults(t, 'second.jsonl')", result)
    assert page.evaluate("resenseLabel.exportGT()") == {}


def test_label_numeric_edits_cannot_export_invalid_or_blank_measurements(page):
    page.goto('file://' + LABEL_TOOL)
    page.evaluate("resenseLabel.loadGT({'00042': [{kind:'person', distance:50}]})")
    for field, value in [('size0', '-1'), ('size2', ''), ('distance', '-2'), ('n_points', '-1'), ('n_points', '1.5')]:
        before = page.evaluate("resenseLabel.exportGT()")
        page.fill(f'input[data-f="{field}"]', value)
        page.dispatch_event(f'input[data-f="{field}"]', 'change')
        assert page.evaluate("resenseLabel.exportGT()") == before, (field, value)


def test_label_import_preserves_evaluator_metadata_and_obstacle_extensions(page):
    page.goto('file://' + LABEL_TOOL)
    data = {'_meta': {'source': 'manual review'}, '00042': [
        {'kind': 'box', 'label': 'rail target', 'distance': 50, 'in_gauge': False,
         'size': [.4, .5, .3], 'name': 'rail_box', 'speed_mps': 12}]}
    page.evaluate('data => resenseLabel.loadGT(data)', data)
    exported = page.evaluate('resenseLabel.exportGT()')
    assert exported['_meta'] == data['_meta']
    assert exported['00042'][0]['name'] == 'rail_box'
    assert exported['00042'][0]['speed_mps'] == 12


def test_label_tool_phone_table_scrolls_without_widening_the_page(page):
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto('file://' + LABEL_TOOL)
    page.evaluate("resenseLabel.loadGT({'00042': [{kind:'person',distance:50}], '00043': []})")
    assert page.evaluate('document.documentElement.scrollWidth') <= 390
    assert page.locator('.table-scroll').evaluate('el => el.scrollWidth > el.clientWidth')
    page.locator('#frames li[data-key="00043"]').focus()
    page.keyboard.press('Enter')
    assert page.evaluate('resenseLabel.state.current') == '00043'


def test_label_file_reads_are_applied_in_selection_order(page):
    page.goto('file://' + LABEL_TOOL)
    page.evaluate("""() => {
        window.finishResults = null;
        queueFile({name: 'results.jsonl', text: () => new Promise(resolve => { finishResults = resolve; })}, loadResults);
        queueFile({name: 'gt.json', text: async () => '{"00042": []}'}, text => loadGT(JSON.parse(text)));
    }""")
    page.wait_for_function('finishResults !== null')
    page.evaluate("finishResults('{\"frame\":42,\"obstacle\":false}')")
    page.evaluate('fileQueue')
    assert page.evaluate('resenseLabel.exportGT()') == {'00042': []}


@pytest.mark.parametrize('health,obstacle,warning,expected', [
    ({'level': 'error'}, False, False, 'FAULT'),
    ({'level': 'error'}, True, False, 'STOP'),
    ({'level': 'warn'}, False, False, 'CAUTION'),
    ({'level': 'warn', 'decision_level': 'ok'}, False, False, 'GO'),
    ({'level': 'ok'}, False, True, 'CAUTION'),
])
def test_hero_render_decision_matches_node_health_priority(health, obstacle, warning, expected):
    import importlib.util
    from pathlib import Path
    from types import SimpleNamespace
    spec = importlib.util.spec_from_file_location('hero', Path(__file__).resolve().parents[2] / 'scripts/hero_view.py')
    hero = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hero)
    assert hero.decision(SimpleNamespace(health=health, obstacle=obstacle, warning=warning)) == expected


def test_hero_missing_requested_frame_does_not_render_another_frame(monkeypatch, tmp_path):
    import importlib.util
    import sys
    from pathlib import Path
    from types import SimpleNamespace
    spec = importlib.util.spec_from_file_location('hero', Path(__file__).resolve().parents[2] / 'scripts/hero_view.py')
    hero = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hero)
    monkeypatch.setattr(sys, 'argv', ['hero', '--npy', 'fixture', '--frame', '42', '--out', str(tmp_path / 'image.png')])
    monkeypatch.setattr(hero, 'iter_npy_frames', lambda *a, **kw: iter([(41, object())]))
    monkeypatch.setattr(hero, 'Detector', lambda cfg: SimpleNamespace(process=lambda frame: object()))
    monkeypatch.setattr(hero, 'render', lambda *a, **kw: pytest.fail('rendered an unrequested frame'))
    with pytest.raises(SystemExit, match='requested frame 42 is absent'):
        hero.main()
