"""Deterministic bed-return scenes exercising the low stage through clustering and persistence.

No Open3D/ray caster: the bed and the small object have explicit returns in track coordinates.
"""
from pathlib import Path

import numpy as np
import pytest

from resense.config import DetectorConfig
from resense.detector import Detector
from resense.track import TrackModel


def test_near_policy_config_round_trip():
    cfg = DetectorConfig()
    path = Path(__file__).resolve().parents[1] / "configs" / "default.yaml"
    assert DetectorConfig.from_yaml(str(path)).to_dict() == cfg.to_dict()
    assert not cfg.lowobj.near_enabled
    enabled = DetectorConfig.from_dict({"lowobj": {"near_enabled": True}})
    assert enabled.lowobj.near_enabled
    assert DetectorConfig.from_dict(enabled.to_dict()).lowobj.near_enabled


def _near_cfg():
    cfg = DetectorConfig()
    cfg.lowobj.near_enabled = True
    return cfg


def _bed(trough=False, depth=0.32):
    x, y = np.meshgrid(np.arange(4.0, 34.0, 0.25), np.arange(-1.05, 1.06, 0.025))
    h = np.full_like(x, -depth)
    if trough:
        h[np.abs(y) < 0.13] = -0.58
    return np.stack([x.ravel(), y.ravel(), h.ravel()], axis=1).astype(np.float32)


def _patch(x, y, length=0.3, width=0.3, base=-0.32, height=0.1, step=0.04):
    xx, yy, zz = np.meshgrid(np.arange(x, x + length + 1e-5, step),
                             np.arange(y - width / 2, y + width / 2 + 1e-5, step),
                             [base + height])
    return np.stack([xx.ravel(), yy.ravel(), zz.ravel()], axis=1).astype(np.float32)


def _volume(x, y, length, width, base, height):
    xg, yg, zg = np.meshgrid(np.arange(x, x + length, 0.06),
                             np.arange(y - width / 2, y + width / 2, 0.06),
                             np.arange(base, base + height + 0.001, 0.05))
    return np.stack([xg.ravel(), yg.ravel(), zg.ravel()], axis=1).astype(np.float32)


def _approach(extra=None, *, trough=False, cfg=None, bed=None, lose_rails=False, depth=0.32):
    cfg = cfg or DetectorConfig()
    det = Detector(cfg)
    det.track = TrackModel(floor_coef=np.array([0.0, 0.0, -depth]), floor_range=(3, 50),
                           center=0.0, yaw=0.0, curvature=0.0, rail_offset=depth,
                           rail_score=0.2, axis_valid=50, floor_verified=50, rail_slabs=3)
    background = _bed(trough, depth) if bed is None else bed
    for k in range(6):
        if lose_rails and k == 2:
            det.track.rail_score = 0.0  # the existing bed template remains, but the near path closes
        obj = extra(k) if callable(extra) else extra
        xyz = background if obj is None else np.concatenate([background, obj])
        intensity = np.full(xyz.shape[0], 25.0, np.float32)
        cand, dy, h, mask, (valid, _, floor) = det._corridor(xyz, intensity)
        cand, straddle, near = det._low_stage(xyz, intensity, dy, h, mask, cand, min(valid, floor))
        clusters = det._cluster(cand, 1, valid, floor, straddle, near)
        gauge, warnings = det._confirm(clusters, 20.0 if callable(extra) else None, 0.1)
    return gauge, warnings, clusters


@pytest.mark.parametrize("distance,lateral", [(10, 0.0), (14, 0.2), (18, -0.2),
                                               (22, 0.1), (26, -0.1), (28, 0.0)])
def test_small_box_on_bed_between_rails_confirms_at_right_distance(distance, lateral):
    obj = _patch(distance, lateral)
    assert not _approach(obj)[0]  # shipped default: its top is below rail head
    gauge, warnings, clusters = _approach(obj, cfg=_near_cfg())
    assert len(gauge) == 1 and not warnings, [(c.kind, c.distance, c.zone) for c in clusters]
    assert gauge[0].kind == "low" and gauge[0].zone == "gauge"
    assert abs(gauge[0].distance - distance) < 0.4
    assert abs(gauge[0].lateral - lateral) < 0.2


@pytest.mark.parametrize("name,extra,trough", [
    ("rail fastener", _patch(18, 0.79), False),
    ("inductor below threshold", _patch(18, 0.0, height=0.06), False),
    ("drain cover", _patch(18, 0.0, length=1.2, width=0.4, base=-0.58, height=0.07), True),
    ("cable along bed", _patch(18, 0.0, length=2.0, width=0.3), False),
    ("guard rail", _patch(18, 0.7, length=2.0, width=0.12, base=-0.1, height=0.1), False),
    ("broad raised bed", _patch(18, 0.0, length=2.0, width=0.9), False),
    ("puddle mirror below trough", _patch(18, 0.0, base=-0.7, height=0.05), True),
])
def test_near_policy_rejects_hardware_and_linear_bed_structure(name, extra, trough):
    gauge, _, clusters = _approach(extra, trough=trough, cfg=_near_cfg())
    assert not gauge, (name, [(c.kind, c.distance, c.zone) for c in clusters])


def test_no_blanket_bed_alarm_or_gap_interpolation():
    assert not _approach(cfg=_near_cfg())[0]
    # An isolated return above a bed gap cannot establish a local reference.
    bed = _bed()
    bed = bed[(bed[:, 0] < 17) | (bed[:, 0] >= 21)]
    assert not _approach(_patch(18.4, 0.0), bed=bed, cfg=_near_cfg())[0]
    assert not _approach(_patch(18, 0.0), lose_rails=True, cfg=_near_cfg())[0]


def test_central_cube_and_near_range_boundary():
    cube = _patch(20, 0.0, height=0.3)
    gauge, _, _ = _approach(cube, cfg=_near_cfg())
    assert len(gauge) == 1 and abs(gauge[0].distance - 20) < 0.4
    assert not _approach(_patch(32, 0.0), cfg=_near_cfg())[0]


@pytest.mark.parametrize("distance", [12, 16, 20, 24, 27, 28])
def test_cube_and_dog_sized_box_below_rail_head(distance):
    for size, depth in [((0.3, 0.3, 0.3), 0.32), ((0.6, 0.3, 0.45), 0.58)]:
        obj = _patch(distance, 0.0, length=size[0], width=size[1], base=-depth, height=size[2])
        assert not _approach(obj, depth=depth)[0]
        gauge, _, _ = _approach(obj, depth=depth, cfg=_near_cfg())
        assert len(gauge) == 1 and gauge[0].zone == "gauge" and gauge[0].kind == "low"
        assert abs(gauge[0].distance - distance) < 0.6


@pytest.mark.parametrize("start", [17, 19, 21, 23, 25, 28])
def test_moving_box_between_rails_tracks_six_approaches(start):
    def moving(k):
        return _patch(start - 2 * k, 0.1)

    assert not _approach(moving)[0]
    gauge, _, _ = _approach(moving, cfg=_near_cfg())
    assert len(gauge) == 1 and gauge[0].zone == "gauge" and gauge[0].kind == "low"
    assert abs(gauge[0].distance - (start - 10)) < 0.6


@pytest.mark.parametrize("name,extra,at", [
    ("rail head box", _patch(18, 0.8, base=0.0), 18),
    ("across rail", _volume(20, 0.8, 0.4, 0.6, -0.18, 0.35), 20),
    ("lying person shallow bed", _volume(18, 0.0, 0.5, 1.8, -0.18, 0.35), 18),
    ("central hanging cable", _volume(18, 0.0, 0.12, 0.12, 0.6, 1.7), 18),
])
def test_existing_paths_keep_zone_and_distance(name, extra, at):
    baseline, _, _ = _approach(extra)
    assert baseline and any(abs(d.distance - at) < 0.6 and d.zone == "gauge" for d in baseline), name
    gauge, _, _ = _approach(extra, cfg=_near_cfg())
    assert gauge and any(abs(d.distance - at) < 0.6 and d.zone == "gauge" for d in gauge), name
