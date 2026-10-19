"""H1 physical collision evidence, independent of free-top observations."""
import copy
import hashlib
import runpy
from pathlib import Path

import numpy as np
import pytest

from resense.clustering import find_clusters
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.gauge import gauge_core_mask, point_in_polygon, widened_profile
from resense.tracking import Tracker

physical_column = runpy.run_path(str(Path(__file__).parent / "fixtures/h1_physical.py"))["physical_column"]


def column_clusters(xyz, ring, cfg=None, axis_error=0.0, union_error=None, axis_valid=225.0,
                    history_above=None):
    cfg = cfg or DetectorConfig()
    rail_dy, h = xyz[:, 1] - axis_error, xyz[:, 2] + 1.83
    dy = rail_dy if union_error is None else xyz[:, 1] - union_error
    warning = point_in_polygon(dy, h, widened_profile(cfg.gauge, cfg.gauge.warning_margin))
    warning &= (xyz[:, 0] >= cfg.gauge.range_min) & (xyz[:, 0] <= cfg.gauge.range_max)
    idx = np.flatnonzero(warning)
    frame_idx = idx.copy()
    if history_above is not None:
        frame_idx[h[idx] > history_above] = -1
    core = gauge_core_mask(dy[idx], h[idx], xyz[idx, 0], cfg.gauge)
    return find_clusters(xyz[idx], np.full(len(idx), 35, np.float32), dy[idx], h[idx], core, cfg.cluster,
                         frame_idx=frame_idx, gauge=cfg.gauge, axis_valid=axis_valid, height_valid=225,
                         ring=None if ring is None else ring[idx], dy_report=rail_dy[idx],
                         in_rail=gauge_core_mask(rail_dy[idx], h[idx], xyz[idx, 0], cfg.gauge),
                         frame_xyz=xyz, frame_h=h, frame_dy=rail_dy, frame_ring=ring)


def matched(xyz, ring, labels, **kwargs):
    return [c for c in column_clusters(xyz, ring, **kwargs)
            if len(c.points_idx) and np.mean(labels[c.points_idx] == 1) > 0.5]


def stop_history(c, misses=()):
    tracker = Tracker(DetectorConfig().tracking)
    stops = []
    for f in range(20):
        tracker.update([] if f in misses else [copy.deepcopy(c)], frame_dt=0.1)
        stops.append(any(t.zone == "gauge" for t in tracker.confirmed()))
    return stops


def test_case45_raw_positive_control():
    xyz, ring, labels = physical_column()
    assert hashlib.sha256(xyz.tobytes()).hexdigest() == "680878ed4f0b233cec517f999ca8648b1193522c929b7ce0f9df9fad7d545a20"
    c, = matched(xyz, ring, labels)
    assert (int((labels == 1).sum()), c.n_gauge, c.ring_count) == (84, 80, 20)
    assert (c.zone, c.reason) == ("gauge", "")
    assert not c.spared
    stops = stop_history(c, misses=(9, 10))
    assert any(stops[:9]) and any(stops[11:])


@pytest.mark.parametrize("lateral", [-0.68, 0.68])
@pytest.mark.parametrize("top,absorbing,beam", [(3.22, None, False), (4.12, None, False),
                                               (4.12, (2.54, 4.12), False), (2.72, None, True)])
def test_observed_inside_body_remains_collision_with_any_upper_surface(lateral, top, absorbing, beam):
    xyz, ring, labels = physical_column(lateral=lateral, top=top, absorbing=absorbing, beam=beam)
    c, = matched(xyz, ring, labels)
    assert (c.zone, c.reason) == ("gauge", "")
    assert any(stop_history(c))


@pytest.mark.parametrize("distance", [37.0, 67.0, 109.0, 137.0])
@pytest.mark.parametrize("lateral", [-1.29, 1.29, -1.5, 1.5])
@pytest.mark.parametrize("axis_error", [-0.3, 0.0, 0.3])
def test_outside_body_under_bounded_model_errors_never_gains_core(distance, lateral, axis_error):
    assert abs(lateral) - 0.23 > 1.05  # independent physical truth
    xyz, ring, labels = physical_column(distance=distance, lateral=lateral, top=4.12)
    for c in matched(xyz, ring, labels, axis_error=axis_error):
        assert not getattr(c, "collision_core", False)
        assert not any(stop_history(c))


def test_sensor_union_cannot_substitute_for_rail_relative_support():
    xyz, ring, labels = physical_column(lateral=1.29, top=4.12)
    for c in matched(xyz, ring, labels, union_error=0.61):
        assert not getattr(c, "collision_core", False)
        assert not any(stop_history(c))


def test_core_cannot_override_axis_validity():
    xyz, ring, labels = physical_column()
    c, = matched(xyz, ring, labels, axis_valid=40.0)
    assert (c.zone, c.reason) == ("warning", "beyond_axis")
    assert not any(stop_history(c))


@pytest.mark.parametrize("mode", ["absent", "reverse", "duplicate"])
def test_collision_proof_does_not_depend_on_ring_names_or_duplicate_echoes(mode):
    xyz, ring, labels = physical_column()
    if mode == "absent":
        ring = None
    elif mode == "reverse":
        ring = 127 - ring
    else:
        xyz, ring, labels = (np.repeat(x, 2, axis=0) for x in (xyz, ring, labels))
    c, = matched(xyz, ring, labels)
    assert (c.zone, c.reason, c.spared) == ("gauge", "", False)


def test_missing_independent_boundaries_cannot_supply_collision_proof():
    xyz, ring, labels = physical_column()
    keep = np.abs(xyz[:, 1]) < 1.4
    c, = matched(xyz[keep], ring[keep], labels[keep])
    assert (c.zone, c.reason, c.collision_core) == ("warning", "column", False)


def test_historical_upper_points_cannot_supply_current_vertical_core():
    xyz, ring, labels = physical_column()
    c, = matched(xyz, ring, labels, history_above=1.4)
    assert (c.zone, c.reason, c.collision_core) == ("warning", "column", False)


def test_feature_off_reproduces_the_inherited_miss():
    xyz, ring, labels = physical_column()
    cfg = DetectorConfig()
    cfg.cluster.column_core_margin = 0
    c, = matched(xyz, ring, labels, cfg=cfg)
    assert (c.zone, c.reason, c.collision_core) == ("warning", "column", False)


def test_one_positive_core_cannot_release_a_measured_column_history():
    xyz, ring, labels = physical_column()
    core, = matched(xyz, ring, labels)
    cfg = DetectorConfig()
    cfg.cluster.column_core_margin = 0
    column, = matched(xyz, ring, labels, cfg=cfg)
    tracker = Tracker(cfg.tracking)
    for _ in range(12):
        tracker.update([copy.deepcopy(column)], frame_dt=0.1)
    tracker.update([copy.deepcopy(core)], frame_dt=0.1)
    assert not any(t.zone == "gauge" for t in tracker.confirmed())
    for _ in range(12):
        tracker.update([copy.deepcopy(core)], frame_dt=0.1)
    assert any(t.zone == "gauge" for t in tracker.confirmed())


def test_full_fresh_confirmation_releases_only_the_old_column_hold():
    xyz, ring, labels = physical_column()
    core, = matched(xyz, ring, labels)
    cfg = DetectorConfig()
    cfg.cluster.column_core_margin = 0
    column, = matched(xyz, ring, labels, cfg=cfg)
    tracker = Tracker(cfg.tracking)
    for _ in range(12):
        tracker.update([copy.deepcopy(column)], frame_dt=0.1)
    for _ in range(4):
        tracker.update([copy.deepcopy(core)], frame_dt=0.1)
        assert not any(t.zone == "gauge" for t in tracker.confirmed())
    tracker.update([copy.deepcopy(core)], frame_dt=0.1)
    track, = tracker.tracks
    assert sum(track.column_hist) == 5  # measured history was not erased
    assert not track.column_held
    assert not any(t.zone == "gauge" for t in tracker.confirmed())  # 5/10 fails the unchanged 60% vote
    tracker.update([copy.deepcopy(core)], frame_dt=0.1)
    assert any(t.zone == "gauge" for t in tracker.confirmed())
    tracker.update([copy.deepcopy(column)], frame_dt=0.1)
    assert track.column_held
    assert not any(t.zone == "gauge" for t in tracker.confirmed())


def test_a_missing_scan_breaks_the_collision_reconfirmation_run():
    xyz, ring, labels = physical_column()
    core, = matched(xyz, ring, labels)
    cfg = DetectorConfig()
    cfg.cluster.column_core_margin = 0
    column, = matched(xyz, ring, labels, cfg=cfg)
    tracker = Tracker(cfg.tracking)
    for c in [column] * 12 + [core] * 4:
        tracker.update([copy.deepcopy(c)], frame_dt=0.1)
    tracker.update([], frame_dt=0.1)
    tracker.update([copy.deepcopy(core)], frame_dt=0.1)
    track, = tracker.tracks
    assert track.column_held
    for _ in range(4):
        tracker.update([copy.deepcopy(core)], frame_dt=0.1)
    assert not track.column_held


@pytest.mark.parametrize("lateral", [-0.68, 0.68, -1.29, 1.29])
def test_full_detector_uses_observed_rails_without_oracle_model(lateral):
    xyz, ring, labels = physical_column(lateral=lateral, rails=True)
    cfg = DetectorConfig()
    detector = Detector(cfg)
    matches = []
    for i in range(14):
        frame = Frame(xyz=xyz, intensity=np.full(len(xyz), 35, np.float32), ring=ring, stamp=i * 0.1)
        result = detector.process(frame)
        matches.append(any(abs(d.distance - 67.0) < 1 and abs(d.center[1] - lateral) < 0.5
                           for d in result.detections))
    assert result.track.rail_slabs > 0
    if abs(lateral) < 1:
        assert all(matches[8:])
    else:
        assert not any(matches)
