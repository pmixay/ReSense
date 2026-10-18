"""The N6 range candidate needs fresh agreeing rails; it never changes axis shape."""
from dataclasses import replace

import numpy as np
import pytest

from resense.config import TrackConfig
from resense.farrails import FarRails
from resense.track import RailsFit, _extend_axis_from_rails, default_track_model, estimate_track


def setup_support(monkeypatch, x=(32., 38., 44., 50.), offset=0.):
    cfg = TrackConfig(rails_axis_extension=True)
    model = default_track_model(cfg)
    model.axis_valid = 45.
    model.yaw = .01
    model.curvature = .00001
    model.center = -.05
    near = RailsFit(.15, -.05, .3, n_slabs=3, tan_yaw=.01,
                    xm=np.array([8., 17., 26.]), mids=np.array([.03, .12, .21]))
    xx = np.array(x)
    evidence = FarRails(x=xx, y=model.center_y(xx) + offset, n_candidates=len(x))
    monkeypatch.setattr('resense.farrails.far_rails', lambda *args: evidence)
    return cfg, model, near


def test_current_support_extends_range_without_changing_shape(monkeypatch):
    cfg, model, near = setup_support(monkeypatch)
    shape = (model.center, model.yaw, model.curvature, model.rail_offset, model.floor_coef.copy())
    _extend_axis_from_rails(np.empty((0, 3)), model, cfg, near, np.empty(0, dtype=int))
    assert model.axis_valid == 65.
    assert model.axis_valid_without_rails == 45.
    assert model.rail_axis_support == 50.
    assert (model.center, model.yaw, model.curvature, model.rail_offset) == shape[:4]
    np.testing.assert_array_equal(model.floor_coef, shape[4])


@pytest.mark.parametrize('case', ['off', 'no_rings', 'no_near', 'weak_near', 'one_slab', 'wall_present'])
def test_missing_required_evidence_never_extends(monkeypatch, case):
    cfg, model, near = setup_support(monkeypatch)
    ring = np.empty(0, dtype=int)
    if case == 'off':
        cfg.rails_axis_extension = False
    elif case == 'no_rings':
        ring = None
    elif case == 'no_near':
        near = None
    elif case == 'weak_near':
        near.score = .01
    elif case == 'one_slab':
        near.n_slabs = 1
    else:
        model.axis_sides = 1
    _extend_axis_from_rails(np.empty((0, 3)), model, cfg, near, ring)
    assert model.axis_valid == 45.
    assert model.rail_axis_support == 0.


@pytest.mark.parametrize(('x', 'offset'), [
    ((40.,), 0.),
    ((40., 40.1, 40.2, 40.3), 0.),
    ((40., 41., 42.), 0.),
    ((32., 38., 44., 50.), .1001),
])
def test_duplicates_short_fragments_and_disagreement_rejected(monkeypatch, x, offset):
    cfg, model, near = setup_support(monkeypatch, x, offset)
    _extend_axis_from_rails(np.empty((0, 3)), model, cfg, near, np.empty(0, dtype=int))
    assert model.axis_valid == 45.


def test_failed_floor_fit_cannot_hold_previous_rail_extension(monkeypatch):
    cfg, model, near = setup_support(monkeypatch)
    _extend_axis_from_rails(np.empty((0, 3)), model, cfg, near, np.empty(0, dtype=int))
    monkeypatch.setattr('resense.track._fit_floor', lambda *args, **kwargs: None)
    next_model = estimate_track(np.empty((0, 3)), cfg, prev=model)
    assert next_model.axis_valid == 45.
    assert next_model.axis_valid_without_rails == 0.
    assert next_model.rail_axis_support == 0.
    assert model.axis_valid == 65.  # previous result stays immutable


def test_no_support_frame_does_not_decay_from_extended_range(monkeypatch):
    cfg, model, near = setup_support(monkeypatch)
    model.axis_valid = 65.
    model.axis_valid_without_rails = 45.
    model.rail_axis_support = 50.
    monkeypatch.setattr('resense.track._fit_floor', lambda *args, **kwargs: (np.array([0., 0., -1.5]), (4., 30.), 10, .01))
    monkeypatch.setattr('resense.track.estimate_rails', lambda *args, **kwargs: replace(near))
    monkeypatch.setattr('resense.track.estimate_axis_from_walls', lambda *args, **kwargs: None)
    monkeypatch.setattr('resense.track.verify_floor_extrapolation', lambda *args, **kwargs: 30.)
    result = estimate_track(np.empty((0, 3)), cfg, prev=model, axis_ring=None)
    assert result.axis_valid == 45.
    assert result.rail_axis_support == 0.


def analytic_rail_scene(only_left=False):
    from resense.farrails import ring_index
    from resense.sensor import ray_directions
    rays = ray_directions().astype(np.float64)
    rays = rays[rays[:, 2] < -1e-4]
    points = rays * (-1.5 / rays[:, 2])[:, None]
    top_scale = -1.43 / rays[:, 2]
    sides = (-.795,) if only_left else (-.795, .795)
    for side in sides:
        hit = np.abs(rays[:, 1] * top_scale - side) < .045
        points[hit] = rays[hit] * top_scale[hit, None]
    keep = (points[:, 0] > 20.) & (points[:, 0] < 80.)
    xyz = points[keep].astype(np.float32)
    return xyz, ring_index(xyz)


@pytest.mark.parametrize('scene', ['paired', 'isolated_edge', 'duplicates', 'gap'])
def test_real_ring_geometry_support_and_negative_controls(scene):
    cfg = TrackConfig(rails_axis_extension=True)
    model = default_track_model(cfg)
    model.axis_valid = 45.
    model.rail_offset = .07
    model.center = 0.
    near = RailsFit(.07, 0., .07, n_slabs=3, tan_yaw=0.,
                    xm=np.array([8., 17., 26.]), mids=np.zeros(3))
    xyz, ring = analytic_rail_scene(only_left=scene == 'isolated_edge')
    if scene == 'duplicates':
        xyz, ring = np.tile(xyz, (3, 1)), np.tile(ring, 3)
    elif scene == 'gap':
        keep = (xyz[:, 0] < 35.) | (xyz[:, 0] > 60.)
        xyz, ring = xyz[keep], ring[keep]
    _extend_axis_from_rails(xyz, model, cfg, near, ring)
    if scene == 'isolated_edge':
        assert model.axis_valid == 45.
    elif scene == 'gap':
        assert model.axis_valid <= 50.  # nothing across the unsupported 25 m gap
        assert model.rail_axis_support < 35.
    else:
        assert model.axis_valid > 60.
        assert model.axis_valid == model.rail_axis_support + cfg.axis_valid_margin
        if scene == 'duplicates':
            plain = replace(model, axis_valid=45., rail_axis_support=0., axis_valid_without_rails=0.)
            original_xyz, original_ring = analytic_rail_scene()
            _extend_axis_from_rails(original_xyz, plain, cfg, near, original_ring)
            assert model.axis_valid == plain.axis_valid


def test_zero_original_axis_range_is_restored(monkeypatch):
    cfg, model, near = setup_support(monkeypatch)
    model.axis_valid = 0.
    _extend_axis_from_rails(np.empty((0, 3)), model, cfg, near, np.empty(0, dtype=int))
    assert model.axis_valid == 65.
    monkeypatch.setattr('resense.track._fit_floor', lambda *args, **kwargs: None)
    result = estimate_track(np.empty((0, 3)), cfg, prev=model)
    assert result.axis_valid == 0.
    assert result.rail_axis_support == 0.


def test_one_ring_cannot_pair_rail_heads_far_apart_longitudinally():
    from resense.farrails import FarRailParams, ring_pairs
    y = np.arange(-2.55, 2.56, .05)
    z = np.full_like(y, -1.5)
    z[np.abs(y + .8) < .04] = -1.42
    z[np.abs(y - .8) < .04] = -1.42
    x = np.where(y < 0., 35., 65.)
    xyz = np.column_stack((x, y, z))
    ring = np.zeros(len(y), dtype=int)
    def zero(xx):
        return np.zeros_like(xx)

    def rail_z(xx):
        return np.full_like(xx, -1.43)
    old = ring_pairs(xyz, ring, zero, rail_z, 26.5, FarRailParams())
    assert len(old) == 1 and old[0, 0] == 50.
    strict = ring_pairs(xyz, ring, zero, rail_z, 26.5,
                       FarRailParams(pair_max_forward_gap=5., pair_use_nearer_forward=True))
    assert len(strict) == 0
    xyz[y > 0., 0] = 38.
    near = ring_pairs(xyz, ring, zero, rail_z, 26.5,
                     FarRailParams(pair_max_forward_gap=5., pair_use_nearer_forward=True))
    assert len(near) == 1 and near[0, 0] == 35.


@pytest.mark.parametrize(('base', 'support', 'expected'), [(45., 50., 45.), (0., 50., 0.), (0., 0., 65.)])
def test_actual_detector_low_stage_keeps_pre_extension_admission(monkeypatch, base, support, expected):
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import Frame
    cfg = DetectorConfig()
    detector = Detector(cfg)
    model = default_track_model(cfg.track)
    model.axis_valid = 65.
    model.axis_valid_without_rails = base
    model.rail_axis_support = support
    detector.track = model
    monkeypatch.setattr(detector, '_fit_track', lambda xyz, periods: xyz)
    original = detector._low_stage
    seen = []

    def capture(*args):
        seen.append(args[-1])
        return original(*args)

    monkeypatch.setattr(detector, '_low_stage', capture)
    xyz = np.column_stack((np.linspace(4., 70., 100), np.zeros(100), np.full(100, -1.5))).astype(np.float32)
    frame = Frame(xyz=xyz, intensity=np.ones(100), stamp=.1)
    detector.process(frame, ego_speed=0.)
    assert seen == [expected]
