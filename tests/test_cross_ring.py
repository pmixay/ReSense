"""Opt-in cross-ring evidence: metadata provenance, sparse admission and temporal gating."""
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from resense.config import ClusterConfig, DetectorConfig, SensorConfig
from resense.detector import Candidates, Detector, _clusters_of
from resense.frame import Frame, frame_from_compact
from resense.pointcloud import COMPACT16_DTYPE, compact16_dedup
from resense.track import default_track_model
from resense.tracking import Tracker

ROOT = Path(__file__).resolve().parents[1]


def _candidates(ring=(7, 7, 8), x=70.0):
    xyz = np.array([[x, -0.3, 0.3], [x + 0.04, 0, 0.45], [x + 0.08, 0.3, 0.6]], np.float32)
    return Candidates(xyz=xyz, dy=xyz[:, 1].copy(), h=xyz[:, 2].copy(),
                      in_gauge=np.ones(3, bool), intensity=np.full(3, 30.0, np.float32),
                      idx=np.arange(3), low=np.zeros(3, bool),
                      ring=None if ring is None else np.asarray(ring, np.int64))


@pytest.mark.parametrize("ring", [None, (-1, -1, -1), (7, 7, -1), (7, 7, 7)])
def test_unknown_or_single_ring_cannot_enable_three_voxel_relaxation(ring):
    assert _clusters_of(_candidates(ring), ClusterConfig(weak_min_rings=2), weak_from=60.0) == []


def test_current_strict_gauge_channels_only_and_ordinary_path_survives():
    cfg = ClusterConfig(weak_min_rings=2)
    cand = _candidates()
    cand.in_gauge[-1] = False
    assert _clusters_of(cand, cfg, weak_from=60.0) == []  # a second ring outside the gauge
    cand.in_gauge[:] = True
    cand.idx[-1] = -1
    assert _clusters_of(cand, cfg, weak_from=60.0) == []  # history cannot supply a second ring
    cand.idx[:] = np.arange(3)
    assert len(_clusters_of(cand, cfg, weak_from=60.0)) == 1
    # The old path works without channels, even while the experiment is enabled.
    cand = _candidates(None)
    assert len(_clusters_of(cand, replace(cfg, weak_min_points=3), weak_from=60.0)) == 1


@pytest.mark.parametrize("weak_from,min_rings", [(0.0, 2), (80.0, 2), (60.0, 0)])
def test_cross_ring_keeps_distance_and_opt_in_guards(weak_from, min_rings):
    assert _clusters_of(_candidates(), ClusterConfig(weak_min_rings=min_rings), weak_from=weak_from) == []


def test_candidate_concat_subset_and_accumulation_do_not_fabricate_channels():
    known, unknown = _candidates(), _candidates(None)
    assert unknown.concat(unknown).ring is None
    for a, b, expected in ((known, unknown, [7, 7, 8, -1, -1, -1]),
                           (unknown, known, [-1, -1, -1, 7, 7, 8])):
        merged = a.concat(b)
        np.testing.assert_array_equal(merged.ring, expected)
        mask = np.array([False, True, False, False, False, True])
        np.testing.assert_array_equal(merged.subset(mask).ring, np.asarray(expected)[mask])
    det = Detector()
    det.cfg.accumulation.enabled = True
    det.cfg.accumulation.n_frames = 3
    det.cfg.accumulation.min_range = 60.0
    det.track = default_track_model(det.cfg.track, sensor_height=det.cfg.track.rail_offset_default)
    det._accumulate(known, speed=10.0, dt=0.1)
    current = _candidates((7, 7, 7), x=69.0)
    merged, n_acc = det._accumulate(current, speed=10.0, dt=0.1)
    assert n_acc == 2
    np.testing.assert_array_equal(merged.ring[merged.idx < 0], [-1, -1, -1])
    cfg = ClusterConfig(min_points=10, weak_min_points=0, weak_min_rings=2)
    assert _clusters_of(merged, cfg, weak_from=60.0) == []


def test_dual_returns_decode_to_one_channel_not_two():
    arr = np.zeros(3, COMPACT16_DTYPE)
    arr["x"] = 14000
    arr["ring"] = 7
    packed = compact16_dedup(arr)
    assert len(packed) == 2
    frame = frame_from_compact(packed, SensorConfig())
    np.testing.assert_array_equal(frame.ring, [7, 7, 7])
    assert _clusters_of(_candidates(frame.ring), ClusterConfig(weak_min_rings=2), weak_from=60.0) == []


@pytest.mark.parametrize("approaching", [False, True])
def test_cross_ring_only_path_reaches_tracker_and_still_needs_approach(approaching):
    cfg = DetectorConfig.from_yaml(str(ROOT / "configs/experimental_cross_ring.yaml"))
    cfg.cluster.weak_min_points = 0  # cross-ring admission also works without the ordinary weak path
    det = Detector(cfg)
    tracker = Tracker(cfg.tracking)
    stops = []
    for k in range(8):
        cand = _candidates(x=78.0 - k if approaching else 78.0)
        clusters = det._cluster(cand, 1, 200.0, 200.0, None)
        assert clusters == []       # weak evidence must not become a normal cluster
        far = det._far_thin(clusters)
        assert len(far) == 1 and far[0].weak and far[0].ring_count == 2
        tracker.update(clusters, frame_dt=0.1, thin=det._thin, far_thin=far)
        stops.append(any(t.reported and t.zone == "gauge" for t in tracker.tracks))
    assert not any(stops[:4])
    assert all(stops[4:]) if approaching else not any(stops)
    assert any(t.reported for t in tracker.tracks)  # static evidence stays advisory, not hidden


@pytest.mark.synthetic
def test_frame_ring_alignment_after_nonfinite_filter_and_reset(tunnel, monkeypatch):
    frame, _, _ = tunnel
    det = Detector()
    # A few returns in the otherwise empty tunnel ensure candidate alignment is exercised.
    xyz = np.concatenate([[[np.nan, 0, 0]], frame.xyz, _candidates(x=20.0).xyz]).astype(np.float32)
    intensity = np.concatenate([[0], frame.intensity, [30, 30, 30]])
    rings = (np.arange(len(xyz)) % 128).astype(np.uint16)
    seen = []
    original = det._low_stage

    def capture(*args, **kwargs):
        groups = original(*args, **kwargs)
        for cand in groups:
            if cand is None:
                continue
            if det._frame_ring is None:
                assert cand.ring is None
            else:
                np.testing.assert_array_equal(cand.ring, rings[1:][cand.idx])
                seen.append(len(cand))
        return groups

    monkeypatch.setattr(det, "_low_stage", capture)
    det.process(Frame(xyz, intensity, ring=rings, stamp=0.1))
    assert sum(seen) > 0
    det.process(Frame(xyz[1:], intensity[1:], stamp=0.2))
    assert det._frame_ring is None
    det.process(Frame(xyz[1:], intensity[1:], ring=rings[1:], stamp=0.3))
    det.reset()
    assert det._frame_ring is None


@pytest.mark.synthetic
def test_default_decisions_do_not_depend_on_ring_metadata():
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
    frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(12), specs=[
        ObstacleSpec(kind="box", size=(0.5, 0.5, 0.5), distance=25.0, lateral=0.0, base_z=-0.2)])
    plain, tagged = Detector(), Detector()
    keys = ("obstacle", "warning", "nearest_distance", "detections", "warnings", "clear_distance",
            "track", "mount", "n_candidates", "n_corridor")
    for k in range(8):
        current = replace(frame, ring=None, stamp=0.1 * k)
        ring = np.full(frame.n, 7, np.uint16) if k % 2 else (np.arange(frame.n) % 128).astype(np.uint16)
        a = plain.process(current).to_dict()
        b = tagged.process(replace(current, ring=ring)).to_dict()
        assert {key: a[key] for key in keys} == {key: b[key] for key in keys}
    assert a["n_candidates"] > 0
