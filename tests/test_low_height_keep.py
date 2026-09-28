"""Bounded continuation from current low returns close to the clean height threshold."""
from dataclasses import replace

import numpy as np
import pytest

from resense.clustering import Cluster
from resense.config import DetectorConfig, TrackingConfig
from resense.detector import Candidates, Detector
from resense.tracking import Tracker


def cluster(x=35.0, *, weak=False, lateral=-0.7, size=(0.4, 0.45, 0.23), kind="low", rail=False):
    center = np.array([x, lateral, -1.4])
    half = np.asarray(size) / 2
    return Cluster(points_idx=np.arange(12), n=6, n_raw=12, centroid=center,
                   bbox_min=center - half, bbox_max=center + half, distance=x - half[0],
                   lateral=lateral, height_min=-0.12, height_max=0.09 if weak else 0.12,
                   intensity=20, n_expected=8, score=1, zone="gauge", n_gauge=6,
                   kind=kind, rail_line=rail, low_height_weak=weak)


def tracker(**kwargs):
    return Tracker(TrackingConfig(stop_keep_low_s=0.3, doubt_extra_hits=0, **kwargs))


def establish(tr, **kwargs):
    for _ in range(6):
        tr.update([cluster(**kwargs)], frame_dt=0.1)
    assert len(tr.confirmed()) == 1
    return tr.tracks[0]


def test_weak_evidence_cannot_seed_or_confirm():
    tr = tracker()
    for _ in range(20):
        tr.update([cluster(weak=True)], frame_dt=0.1)  # direct callers cannot treat it as a seed
    assert not tr.tracks
    tr.update([cluster()], frame_dt=0.1)
    for _ in range(5):
        tr.update([], low_height=[cluster(weak=True)], frame_dt=0.1)
        assert not tr.confirmed()


def test_current_evidence_bridges_two_frames_and_clean_hit_refreshes_budget():
    tr = tracker()
    t = establish(tr)
    clean = t.low_clean
    confidence = t.confidence
    for k in range(2):
        tr.update([], low_height=[cluster(weak=True)], frame_dt=0.1)
        assert t.reported and t.misses == 0 and t.last.low_height_weak
        assert t.since_clean == pytest.approx(0.1 * (k + 1))
        assert t.low_clean is clean and t.confidence == confidence
    tr.update([cluster()], frame_dt=0.1)
    assert t.reported and not t.last.low_height_weak and t.since_clean == 0
    assert t.low_clean is t.last


@pytest.mark.parametrize("intervals", [[0.1] * 6, [0.05] * 10, [0.19, 0.12], [0.2, 0.1, 0.01], [0.3, 0.01]])
def test_weak_current_returns_expire_in_sensor_time(intervals):
    tr = tracker()
    t = establish(tr)
    elapsed = 0
    for dt in intervals:
        elapsed += dt
        tr.update([], low_height=[cluster(weak=True)], frame_dt=dt)
        if elapsed > 0.3 + 1e-9:
            assert not t.reported
        else:
            assert t.reported


def test_first_weak_observation_after_long_gap_gets_only_the_existing_miss_hold():
    tr = tracker()
    t = establish(tr)
    tr.update([], low_height=[cluster(weak=True)], frame_dt=0.31)
    assert t.reported and t.misses == 1 and not t.last.low_height_weak
    tr.update([], low_height=[cluster(weak=True)], frame_dt=0.1)
    assert not t.reported and t.misses == 2


def test_removal_uses_existing_hold_and_cannot_gain_an_extra_budget():
    tr = tracker()
    t = establish(tr)
    tr.update([], low_height=[cluster(weak=True)], frame_dt=0.1)
    tr.update([], frame_dt=0.1)
    assert t.reported and t.misses == 1
    tr.update([], frame_dt=0.1)
    assert not t.reported
    for _ in range(5):
        tr.update([], low_height=[cluster(weak=True)], frame_dt=0.1)
        assert not tr.confirmed()


@pytest.mark.parametrize("weak", [
    cluster(weak=True, lateral=-0.2),
    cluster(weak=True, size=(1.3, 0.45, 0.23)),
    cluster(weak=True, size=(0.4, 0.18, 0.23)),
    cluster(weak=True, rail=True),
    cluster(weak=True, kind=""),
])
def test_unrelated_or_rail_geometry_cannot_continue(weak):
    tr = tracker()
    t = establish(tr)
    tr.update([], low_height=[weak], frame_dt=0.1)
    tr.update([], low_height=[weak], frame_dt=0.1)
    assert not t.reported and t.misses == 2


def test_corridor_stop_cannot_use_low_height_evidence():
    tr = tracker()
    t = establish(tr, kind="")
    for _ in range(2):
        tr.update([], low_height=[cluster(weak=True)], frame_dt=0.1)
    assert not t.reported


def test_ambiguous_weak_cluster_does_not_choose_a_track():
    tr = tracker()
    for _ in range(6):
        tr.update([cluster(lateral=-0.8), cluster(lateral=-0.6)], frame_dt=0.1)
    assert len(tr.confirmed()) == 2
    for _ in range(2):
        tr.update([], low_height=[cluster(weak=True)], frame_dt=0.1)
    assert not tr.confirmed()


def test_shape_reference_does_not_drift_through_weak_hits():
    tr = tracker()
    t = establish(tr)
    tr.update([], low_height=[cluster(weak=True, size=(0.7, 0.45, 0.23))], frame_dt=0.1)
    assert t.misses == 0
    # 1.1 m would fit the previous 0.7 m weak hit, but not the original 0.4 m clean hit.
    tr.update([], low_height=[cluster(weak=True, size=(1.1, 0.45, 0.23))], frame_dt=0.1)
    assert t.misses == 1 and t.low_clean.size[0] == pytest.approx(0.4)


def test_approaching_object_uses_prediction_inside_the_tight_gate():
    tr = tracker()
    for k in range(6):
        tr.update([cluster(x=50.0 - k)], frame_dt=0.1)
    t = tr.tracks[0]
    for x in (44.0, 43.0):
        tr.update([], low_height=[cluster(x=x, weak=True)], frame_dt=0.1)
        assert t.reported and t.misses == 0 and t.centroid[0] == x


def candidates(top=0.09, *, width=0.45, length=0.4):
    xyz = np.stack(np.meshgrid(np.linspace(25.0, 25.0 + length, 4),
                              np.linspace(-0.9, -0.9 + width, 5),
                              np.linspace(top - 0.23, top, 3), indexing="ij"), axis=-1).reshape(-1, 3).astype(np.float32)
    n = len(xyz)
    return Candidates(xyz, xyz[:, 1].astype(float), xyz[:, 2].astype(float),
                      np.ones(n, bool), np.ones(n), np.arange(n), np.ones(n, bool))


def extracted(detector, top=0.09, **kwargs):
    straddle = candidates(top, **kwargs)
    empty = straddle.subset(np.zeros(len(straddle), bool))
    return detector._cluster(empty, 1, 100.0, 100.0, straddle)


def test_detector_routes_only_height_failures_and_preserves_default():
    cfg = DetectorConfig()
    off = Detector(cfg)
    assert extracted(off) == [] and off._low_height == []
    cfg.tracking = replace(cfg.tracking, stop_keep_low_s=0.3)
    on = Detector(cfg)
    assert extracted(on) == []
    assert len(on._low_height) == 1 and on._low_height[0].low_height_weak
    clean = extracted(on, 0.12)
    assert len(clean) == 1 and not clean[0].low_height_weak and not on._low_height
    for kwargs in ({"top": 0.06}, {"width": 0.3}, {"length": 1.0}):
        assert extracted(on, **kwargs) == [] and on._low_height == []


def test_foot_of_tall_corridor_object_is_not_continuation_evidence():
    cfg = DetectorConfig()
    cfg.tracking = replace(cfg.tracking, stop_keep_low_s=0.3)
    detector = Detector(cfg)
    straddle = candidates()
    corridor = candidates(0.65)
    corridor.low[:] = False
    # Corridor points above the same footprint must still invoke the existing foot guard.
    detector._cluster(corridor, 1, 100.0, 100.0, straddle)
    assert not detector._low_height


def bed_sequence(enabled, tops, *, distance=24.0, lateral=-0.6, step=0.0):
    """Explicit sparse returns over a dense bed, with a rail-height reference jitter.

    Two lower scan lines span the object, but only one return sees its raised top.
    No hard-coded detector target ROI or recorded points enter this scene.
    """
    from resense.track import TrackModel
    cfg = DetectorConfig()
    cfg.tracking.stop_keep_low_s = 0.3 if enabled else 0.0
    cfg.tracking.doubt_extra_hits = 0
    det = Detector(cfg)
    det.track = TrackModel(floor_coef=np.array([0.0, 0.0, -0.32]), floor_range=(3, 60),
                           center=0.0, yaw=0.0, curvature=0.0, rail_offset=0.32,
                           rail_score=0.2, axis_valid=60, floor_verified=60, rail_slabs=3)
    bx, by = np.meshgrid(np.arange(4.0, 58.0, 0.25), np.arange(-1.05, 1.06, 0.025))
    bed = np.column_stack([bx.ravel(), by.ravel(), np.full(bx.size, -0.32)]).astype(np.float32)
    out = []
    for k, top in enumerate(tops):
        x = distance - step * k
        if top is None:
            xyz = bed
        else:
            xx, yy = np.meshgrid([x, x + 0.4], np.linspace(lateral - 0.225, lateral + 0.225, 5))
            lower = np.column_stack([xx.ravel(), yy.ravel(), np.full(xx.size, -0.12)])
            obj = np.vstack([lower, [x + 0.2, lateral, 0.12]])
            xyz = np.concatenate([bed, obj]).astype(np.float32)
        det.track.rail_offset = 0.32 + (0.12 - top if top is not None else 0)
        intensity = np.full(len(xyz), 25, np.float32)
        cand, dy, h, mask, (valid, _, floor) = det._corridor(xyz, intensity)
        cand, straddle, near = det._low_stage(xyz, intensity, dy, h, mask, cand, min(valid, floor))
        clusters = det._cluster(cand, 1, valid, floor, straddle, near)
        gauge, _ = det._confirm(clusters, step / 0.1, 0.1)
        out.append(gauge)
    return out


@pytest.mark.parametrize("distance,lateral,step", [(18, -0.6, 0), (28, 0.6, 0), (42, -0.65, 0.5)])
def test_sparse_bed_returns_bridge_height_jitter_then_clear_on_removal(distance, lateral, step):
    tops = [0.12] * 6 + [0.09] * 2 + [0.12] + [None] * 4
    kwargs = dict(distance=distance, lateral=lateral, step=step)
    off, on = bed_sequence(False, tops, **kwargs), bed_sequence(True, tops, **kwargs)
    assert off[5] and on[5]
    assert off[6] and not off[7]
    assert on[6] and on[7] and on[7][0].reason == "low_height_hold"
    assert on[8] and on[8][0].reason == ""
    assert on[9] and not any(on[10:])


def test_sparse_bed_transients_and_permanent_height_failure_cannot_persist():
    assert not any(bed_sequence(True, [0.09] * 12))
    assert not any(bed_sequence(True, [0.12] * 2 + [0.09] * 12))
    out = bed_sequence(True, [0.12] * 6 + [0.09] * 10)
    assert all(out[5:9]) and not any(out[9:])
