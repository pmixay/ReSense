"""health.clear_cap_thin / health.clear_cap_persist (27.09, P3 range overclaim; resense/evidence.py):
evidence below the cluster bars caps clear_distance - a scan-line cluster inside the strict envelope,
and a sparse blob of envelope returns that comes nearer at a constant apparent speed over several
timestamped frames. Both are on by default since 27.09 (clear_cap_thin, clear_cap_persist 4) and
never change a detection or the decision."""

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from resense.config import DetectorConfig, GaugeConfig, HealthConfig
from resense.detector import Detector, thin_cap_distance
from resense.evidence import PersistentEvidence, sparse_blobs
from resense.frame import Frame
from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame

ROOT = Path(__file__).resolve().parents[1]


def test_shipped_in_the_code_and_both_parameter_files():
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        assert cfg.health.clear_cap_thin is True
        assert cfg.health.clear_cap_persist == 4
        assert cfg.health == DetectorConfig().health


def _hcfg(k=4, **kw):
    h = HealthConfig(clear_cap_persist=k)
    for key, v in kw.items():
        setattr(h, key, v)
    return h


def _cube(x, dy=0.8, h=1.2):
    """Two returns stacked vertically (one column, two rings) - the far 0.3 m cube of set O."""
    return np.array([x, x + 0.02]), np.array([dy, dy]), np.array([h - 0.1, h + 0.1])


def _feed(pe, frames, times=None):
    if times is None:
        times = np.arange(len(frames), dtype=np.float64) * pe.reference_dt_s
    out = []
    previous = None
    for (X, dy, h), stamp in zip(frames, times):
        dt_s = None if previous is None else float(stamp - previous)
        out.append(pe.update(X, dy, h, None, dt_s))
        previous = float(stamp)
    return out


def test_a_static_object_coming_nearer_caps_after_k_frames():
    pe = PersistentEvidence(_hcfg(4), GaugeConfig())
    caps = _feed(pe, [_cube(100.0 - 1.6 * k) for k in range(6)])
    assert caps[:3] == [None, None, None]
    assert caps[3] == pytest.approx(100.0 - 1.6 * 3)
    assert caps[5] == pytest.approx(100.0 - 1.6 * 5)
    pe.reset()                                    # a reset forgets the chain
    assert pe.update(*_cube(90.0), None, None) is None


@pytest.mark.parametrize("times", [
    np.arange(8, dtype=np.float64) * 0.1,
    np.arange(8, dtype=np.float64) * 0.2,
    np.array([0.0, 0.1, 0.2, 0.4, 0.5, 0.6, 0.7, 0.8]),
    np.array([0.0, 0.1, 0.3, 0.4, 0.6, 0.7, 0.9, 1.0]),
])
def test_constant_apparent_speed_chains_across_frame_rates_drops_and_irregular_gaps(times):
    pe = PersistentEvidence(_hcfg(4), GaugeConfig())
    frames = [_cube(100.0 - 16.0 * t) for t in times]
    caps = _feed(pe, frames, times)
    first = next(i for i, cap in enumerate(caps) if cap is not None)
    assert first == 3
    assert caps[first] == pytest.approx(100.0 - 16.0 * times[first])


def test_fast_replay_never_removes_the_existing_frame_cap():
    pe = PersistentEvidence(_hcfg(4), GaugeConfig())
    times = np.arange(8, dtype=np.float64) * 0.05
    caps = _feed(pe, [_cube(100.0 - 16.0 * t) for t in times], times)
    # The timestamp-aware chain waits for three nominal periods at 20 Hz, while the shipped
    # frame-based chain remains active and keeps its original earlier cap.
    assert caps[:3] == [None] * 3
    assert caps[3] == pytest.approx(100.0 - 16.0 * times[3])


def test_nominal_rate_timestamp_jitter_preserves_frame_based_chain():
    # These stamps vary around 10 Hz, but the recorded object advances one nominal scan step
    # each frame. Timestamp jitter must not erase the previously supported persistent cap.
    times = np.array([0.0, 0.053, 0.160, 0.300, 0.380, 0.490])
    frames = [_cube(100.0 - 1.6 * k) for k in range(len(times))]
    caps = _feed(PersistentEvidence(_hcfg(4), GaugeConfig()), frames, times)
    assert caps[:3] == [None, None, None]
    assert caps[3] == pytest.approx(100.0 - 1.6 * 3)


def test_inconsistent_speed_and_long_gaps_break_the_chain():
    pe = PersistentEvidence(_hcfg(4), GaugeConfig())
    # Each individual 10 Hz displacement is inside the former range, but alternating
    # apparent velocities are not one static object's approach.
    shifts = [0.0, 1.0, 3.0, 4.0, 6.0, 7.0, 9.0, 10.0]
    assert _feed(pe, [_cube(100.0 - x) for x in shifts]) == [None] * len(shifts)

    pe.reset()
    times = np.array([0.0, 0.1, 0.2, 0.6, 0.7, 0.8, 0.9, 1.0])
    caps = _feed(pe, [_cube(100.0 - 16.0 * t) for t in times], times)
    assert caps[:6] == [None] * 6
    assert caps[6] == pytest.approx(100.0 - 16.0 * times[6])


def test_clutter_that_does_not_come_nearer_or_jumps_does_not_cap():
    pe = PersistentEvidence(_hcfg(3), GaugeConfig())
    assert _feed(pe, [_cube(80.0) for _ in range(6)]) == [None] * 6               # same range: a surface row
    pe.reset()
    xs = [100.0, 98.4, 95.9, 94.6, 92.0, 90.9]                                     # shifts 1.6, 2.5, 1.3, 2.6, 1.1
    assert _feed(pe, [_cube(x) for x in xs]) == [None] * 6
    pe.reset()
    assert _feed(pe, [_cube(100.0 - 1.6 * k, dy=0.8 - 0.3 * k) for k in range(5)]) == [None] * 5  # moves across


def test_only_sparse_isolated_envelope_blobs_count():
    h = _hcfg(1)
    pe = PersistentEvidence(h, GaugeConfig())
    assert pe.update(*_cube(60.0), None, None) == pytest.approx(60.0)             # k = 1: any sparse blob
    assert pe.update(*_cube(60.0, dy=1.3), None, None) is None                     # outside the nominal envelope
    assert pe.update(*_cube(60.0, h=0.05), None, None) is None                     # below the envelope floor
    X, dy, hh = _cube(60.0)
    assert pe.update(X, dy, hh, np.array([True, True]), None) is None               # low-object candidates
    # a crowded stretch (a wall in the corridor): more than persist_max_around other returns within 2 m
    wall = np.linspace(59.0, 61.0, 20)
    X2, dy2, h2 = np.concatenate([X, wall]), np.concatenate([dy, np.full(20, 1.3)]), np.concatenate([hh, np.full(20, 1.0)])
    assert pe.update(X2, dy2, h2, None, None) is None
    # one return, or a blob longer than persist_max_extent
    assert pe.update(np.array([60.0]), np.array([0.5]), np.array([1.0]), None, None) is None
    blobs = sparse_blobs(np.array([60.0, 60.3, 60.6]), np.zeros(3), np.full(3, 1.0), np.ones(3, bool), h)
    assert blobs.shape[0] == 0
    # a scan line across the envelope (the box above it, the plank) is a blob
    row = sparse_blobs(np.full(5, 90.0), np.linspace(-0.6, 0.6, 5), np.full(5, 2.9), np.ones(5, bool), h)
    assert row.shape[0] == 1 and row[0, 3] == 5


def _thin(**kw):
    return SimpleNamespace(**dict(dict(thin=True, weak=False, kind="", zone="gauge", reason="", n_gauge=3,
                                       distance=30.0), **kw))


@pytest.mark.parametrize("change", [{"kind": "low"}, {"weak": True}, {"zone": "warning"}, {"reason": "elevated"}, {"thin": False},
                                   {"n_gauge": 2}, {"distance": 61.0}, {"distance": float("nan")},
                                   {"distance": -1.0}])
def test_thin_cap_needs_a_supported_undemoted_scan_line_in_the_trusted_range(change):
    assert thin_cap_distance([_thin(**change)], 3, 60.0) is None


def test_thin_cap_is_the_nearest_supported_one_in_a_single_frame():
    thin = [_thin(distance=40.0), _thin(), _thin(distance=20.0, n_gauge=2)]
    assert thin_cap_distance(thin, 3, 60.0) == 30.0
    assert thin_cap_distance(thin, 3, 60.0, n_acc=2) is None


def _run(cfg, frames):
    det = Detector(cfg)
    return [det.process(Frame(xyz=f.xyz, intensity=f.intensity, ring=f.ring, stamp=0.1 * k, meta=dict(f.meta)))
            for k, f in enumerate(frames)]


def test_detector_outputs_are_unchanged_but_clear_distance(tunnel):
    """A small box coming nearer at 1.5 m per frame in the synthetic tunnel: with both caps on every
    detection, warning, health level and the monitored range are those with both off, and
    clear_distance is never longer."""
    frames = [synthetic_tunnel_frame(rng=np.random.default_rng(20 + k),
                                     specs=[ObstacleSpec(kind="box", size=(0.3, 0.3, 0.3), distance=70.0 - 1.5 * k)])[0]
              for k in range(6)]
    off = DetectorConfig()
    off.health.clear_cap_thin = False                # both on by default since 27.09: the baseline pins them off
    off.health.clear_cap_persist = 0
    on = DetectorConfig()
    on.health.clear_cap_thin = True
    on.health.clear_cap_persist = 3
    a = _run(off, frames)
    for b in (_run(on, frames), _run(DetectorConfig(), frames)):   # k = 3 and the shipped k = 4
        for x, y in zip(a, b):
            assert (x.obstacle, x.warning, x.health["level"], x.health["decision_level"]) == \
                   (y.obstacle, y.warning, y.health["level"], y.health["decision_level"])
            assert [d.to_dict() for d in x.detections] == [d.to_dict() for d in y.detections]
            assert x.health["monitored_range"] == y.health["monitored_range"]
            assert y.clear_distance <= x.clear_distance + 1e-9


def test_full_detector_sparse_clearance_cap_survives_five_hz_sampling():
    times = np.arange(8, dtype=np.float64) * 0.2
    frames = []
    for k, t in enumerate(times):
        spec = ObstacleSpec(kind="box", size=(0.3, 0.3, 0.3), distance=100.0 - 16.0 * t,
                            lateral=0.8, base_z=-1.35, reflectivity=25.0)
        fr = synthetic_tunnel_frame(rng=np.random.default_rng(50000 + k), specs=[spec])[0]
        frames.append(Frame(xyz=fr.xyz, intensity=fr.intensity, stamp=float(t), meta=dict(fr.meta)))

    uncapped = DetectorConfig()
    uncapped.health.clear_cap_persist = 0
    base_detector, candidate_detector = Detector(uncapped), Detector(DetectorConfig())
    baseline, candidate = [], []
    for frame in frames:
        baseline.append(base_detector.process(frame))
        candidate.append(candidate_detector.process(frame))

    for a, b in zip(baseline, candidate):
        assert (a.obstacle, a.warning, a.health["level"], a.health["decision_level"]) == \
               (b.obstacle, b.warning, b.health["level"], b.health["decision_level"])
        assert [d.to_dict() for d in a.detections] == [d.to_dict() for d in b.detections]
        assert a.health["monitored_range"] == b.health["monitored_range"]

    target_ranges = 100.0 - 16.0 * times
    overclaim_rows = [i for i, (a, b) in enumerate(zip(baseline, candidate))
                      if a.clear_distance > target_ranges[i] + 1.0 and
                      b.clear_distance <= target_ranges[i] + 1.0]
    assert overclaim_rows
