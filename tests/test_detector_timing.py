"""Complete process timing, one-frame latency history, and unchanged health policy."""
from types import SimpleNamespace

import numpy as np
import pytest

import resense.detector as detector_module
from resense.config import DetectorConfig, GaugeConfig, HealthConfig, TrackConfig
from resense.detector import Detector, FrameResult
from resense.frame import Frame
from resense.health import HealthMonitor
from resense.track import default_track_model


class Clock:
    """One millisecond between adjacent reads; injected work advances the same clock."""
    def __init__(self):
        self.ms = 0.0

    def read(self):
        now = self.ms
        self.ms += 1.0
        return now / 1000.0


@pytest.fixture
def timed_detector(monkeypatch, request):
    clock = Clock()
    monkeypatch.setattr(detector_module, "time", SimpleNamespace(perf_counter=clock.read))
    cfg = DetectorConfig()
    assert cfg.health.latency_affects_decision is False
    # Isolate the latency warning while exercising the real detector and health update.
    cfg.health.min_points = 0
    cfg.health.min_visibility = 0
    cfg.health.min_lock_rate = 0
    cfg.health.latency_window = getattr(request, "param", 50)
    cfg.calibration.enabled = False
    det = Detector(cfg)
    delays = SimpleNamespace(health=200.0, mount=3.0, result=5.0)
    update = det.health.update
    mount_dict = det.calib.state.to_dict

    def slow_health(*args, **kwargs):
        value = update(*args, **kwargs)
        clock.ms += delays.health  # include work after the monitor computes its percentile
        return value

    def slow_mount():
        clock.ms += delays.mount
        return mount_dict()

    def slow_result(**kwargs):
        clock.ms += delays.result
        return FrameResult(**kwargs)

    monkeypatch.setattr(det.health, "update", slow_health)
    monkeypatch.setattr(det.calib.state, "to_dict", slow_mount)
    monkeypatch.setattr(detector_module, "FrameResult", slow_result)
    frame = Frame(np.empty((0, 3), np.float32), np.empty(0, np.float32))
    return det, frame, delays, clock


def test_total_covers_slow_health_mount_and_result_once(timed_detector):
    det, frame, _, _ = timed_detector
    first = det.process(frame)
    timing = first.timing_ms
    assert timing == pytest.approx({
        "track": 1, "corridor": 1, "egomotion": 1, "accumulate": 1,
        "cluster": 1, "tracking": 1, "stages": 6, "health": 204,
        "result": 6, "total": 216,
    })
    assert sum(timing[k] for k in ("stages", "health", "result")) == pytest.approx(timing["total"])
    assert first.health["latency_p95_ms"] == 0.0
    assert first.health["latency_basis"] == "previous_complete_process"
    assert first.health["latency_sample_age_frames"] is None
    assert list(det.health._lat) == []
    second = det.process(frame)
    assert list(det.health._lat) == [first.timing_ms["total"]]
    assert second.health["latency_p95_ms"] == 216.0
    assert second.health["latency_sample_age_frames"] == 1
    assert len(det.health._points) == len(det.health._lock) == 2
    assert second.to_dict()["timing_ms"] == {k: round(v, 2) for k, v in second.timing_ms.items()}


@pytest.mark.parametrize("affects", [False, True])
def test_health_inclusive_warning_starts_on_result_eleven(timed_detector, affects):
    det, frame, _, _ = timed_detector
    det.cfg.health.latency_affects_decision = affects
    for index in range(11):
        result = det.process(frame)
        assert len(det.health._lat) == index
        assert result.timing_ms["stages"] < det.cfg.health.latency_budget_ms < result.timing_ms["total"]
        if index < 10:
            assert result.health["level"] == result.health["decision_level"] == "ok"
            assert result.health["messages"] == []
    assert result.health["level"] == "warn"
    assert result.health["decision_level"] == ("warn" if affects else "ok")
    assert result.health["messages"] == ["latency p95 216 ms over the 100 ms budget"]
    assert len(det.health._points) == len(det.health._lock) == 11
    # Existing non-latency warnings/faults still affect the decision under either policy.
    frame.meta.update(n_raw=10, n_near=10)
    assert det.process(frame).health["decision_level"] == "warn"
    det.cfg.health.min_points = 1
    fault = det.process(frame)
    assert fault.health["level"] == fault.health["decision_level"] == "error"
    assert fault.clear_distance == fault.health["monitored_range"] == 0.0


@pytest.mark.parametrize("timed_detector", [3], indirect=True)
def test_window_evicts_completed_samples_and_reset_discards_pending(timed_detector):
    det, frame, delays, _ = timed_detector
    completed = []
    for delay in (200, 100, 50, 20, 10):
        delays.health = delay
        result = det.process(frame)
        assert list(det.health._lat) == pytest.approx(completed[-3:])
        expected = float(np.percentile(completed[-3:], 95)) if completed else 0.0
        assert result.health["latency_p95_ms"] == round(expected, 1)
        completed.append(result.timing_ms["total"])
    det.reset()
    assert det._previous_latency_ms is None
    assert not det.health._lat and not det.health._points and not det.health._lock
    first = det.process(frame)
    assert first.health["latency_sample_age_frames"] is None
    assert first.health["latency_p95_ms"] == 0.0
    assert not det.health._lat


@pytest.mark.parametrize("failure_stage", ["_fit_track", "result"])
def test_failed_call_does_not_leave_an_old_or_partial_pending_sample(timed_detector, monkeypatch, failure_stage):
    det, frame, _, _ = timed_detector
    det.process(frame)

    def fail(*args, **kwargs):
        raise RuntimeError("injected processing failure")

    with monkeypatch.context() as patch:
        if failure_stage == "result":
            patch.setattr(detector_module, "FrameResult", fail)
        else:
            patch.setattr(det, failure_stage, fail)
        with pytest.raises(RuntimeError, match="injected processing failure"):
            det.process(frame)
    assert det._previous_latency_ms is None
    retained = list(det.health._lat)
    recovered = det.process(frame)
    assert recovered.health["latency_sample_age_frames"] is None
    assert list(det.health._lat) == retained


def test_default_nonlatency_results_match_previous_supplied_stage_latency(tunnel, monkeypatch):
    clock = Clock()
    monkeypatch.setattr(detector_module, "time", SimpleNamespace(perf_counter=clock.read))
    previous, current = Detector(), Detector()
    supplied_update, complete_update = previous.health.update, current.health.update

    def stage_latency(*args, **kwargs):
        args = list(args)
        args[6] = 6.0  # the six original intervals on this deterministic clock
        return supplied_update(*args, **kwargs)

    def complete_latency(*args, **kwargs):
        out = complete_update(*args, **kwargs)
        clock.ms += 200.0
        return out

    monkeypatch.setattr(previous.health, "update", stage_latency)
    monkeypatch.setattr(current.health, "update", complete_latency)
    frame = tunnel[0]
    dirty = Frame(frame.xyz, frame.intensity, meta={"n_raw": 2 * frame.n, "n_near": frame.n})
    few = Frame(frame.xyz[:500], frame.intensity[:500])
    empty = Frame(frame.xyz[:0], frame.intensity[:0])
    levels, saw_latency_difference = set(), False
    for index, source in enumerate([frame] * 12 + [dirty, few, empty]):
        value = Frame(source.xyz, source.intensity, stamp=index * 0.1, meta=dict(source.meta))
        before, after = previous.process(value).to_dict(), current.process(value).to_dict()
        levels.add(after["health"]["decision_level"])
        saw_latency_difference |= before["health"]["level"] != after["health"]["level"]
        for row in (before, after):
            row.pop("timing_ms")
            health = row["health"]
            latency = [m for m in health["messages"] if m.startswith("latency p95 ")]
            if not latency:
                assert health["level"] == health["decision_level"]
            else:
                assert health["level"] in ("warn", "error")
            health["level"] = health["decision_level"]
            health["messages"] = [m for m in health["messages"] if m not in latency]
            for key in ("latency_p95_ms", "latency_basis", "latency_sample_age_frames"):
                health.pop(key)
        assert before == after
    assert levels == {"ok", "warn", "error"}
    assert saw_latency_difference  # exercise the changed monitor without changing the decision


@pytest.mark.parametrize("window", [0, 1, 9, 10, 50])
@pytest.mark.parametrize("affects", [False, True])
def test_numeric_health_callers_keep_current_sample_window_and_policy(window, affects):
    cfg = HealthConfig(min_points=0, min_visibility=0, min_lock_rate=0,
                       latency_window=window, latency_affects_decision=affects)
    monitor = HealthMonitor(cfg)
    track = default_track_model(TrackConfig())
    track.floor_shadow, track.floor_held = 1.0, True
    args = (np.empty((0, 3)), {}, track, GaugeConfig(), 100.0, 0.1)
    for index in range(10):
        out = monitor.update(*args, 216.0)
        warning = index == 9 and window >= 10
        assert out["latency_p95_ms"] == 216.0
        assert out["level"] == ("warn" if warning else "ok")
        assert out["decision_level"] == ("warn" if warning and affects else "ok")
        assert len(monitor._lat) == min(index + 1, max(1, window))
        assert out["floor_shadow_frames"] == out["floor_held_frames"] == index + 1
        assert "latency_basis" not in out and "latency_sample_age_frames" not in out
    history = list(monitor._lat)
    assert monitor.update(*args, None)["latency_p95_ms"] == 216.0
    assert list(monitor._lat) == history
    monitor.reset()
    assert monitor.update(*args, None)["latency_p95_ms"] == 0.0
    assert not monitor._lat
