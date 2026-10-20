"""Absolute raw-rail anchoring and far support, with known physical geometry."""
from dataclasses import replace

import numpy as np
import pytest

from resense.clustering import FrameRays
from resense.config import DetectorConfig
from resense.track import TrackModel
from test_column_collision_core import matched, physical_column, stop_history


def rays_of(xyz, ring, center=0., yaw=0.):
    cfg = DetectorConfig()
    model = TrackModel(np.array([0., 0., -2.18]), (3., 120.), center, np.arctan(yaw), 0.)
    return FrameRays(xyz, ring, xyz[:, 2] + 1.83, xyz[:, 1] - model.center_y(xyz[:, 0]), model, cfg.track)


@pytest.mark.parametrize('error', [-.6, 0., .6])
def test_absolute_rail_anchor_does_not_cancel_constant_model_error(error):
    xyz, ring, _ = physical_column()
    rays = rays_of(xyz, ring, error)
    anchor = rays.collision_axis_anchor()
    interval = rays.collision_axis_interval(67.)
    assert anchor is not None and anchor[0] <= -error <= anchor[1]
    assert interval is not None and interval[0] <= -error <= interval[1]
    assert interval[0] <= 0 <= interval[1]


@pytest.mark.parametrize('distance', [67., 109., 137.])
@pytest.mark.parametrize('lateral', [-1.29, 1.29])
@pytest.mark.parametrize('yaw_error', [-.004, .004])
def test_outside_body_under_yaw_error_cannot_gain_core(distance, lateral, yaw_error):
    xyz, ring, labels = physical_column(distance=distance, lateral=lateral, top=4.12)
    rays = rays_of(xyz, ring, yaw=yaw_error)
    interval = rays.collision_axis_interval(distance)
    assert interval is not None and interval[0] <= -yaw_error * distance <= interval[1]
    for c in matched(xyz, ring, labels, yaw_error=yaw_error):
        assert not c.collision_core and not any(stop_history(c))


@pytest.mark.parametrize('mode', ['absent', 'one_rail', 'wrong_spacing', 'held_floor'])
def test_missing_or_invalid_current_rail_anchor_abstains(mode):
    xyz, ring, labels = physical_column(rails=mode != 'absent', rail_spacing=2.1 if mode == 'wrong_spacing' else 1.59)
    if mode == 'one_rail':
        keep = ~((labels == 3) & (xyz[:, 0] < 30))
        xyz, ring = xyz[keep], ring[keep]
    rays = rays_of(xyz, ring)
    if mode == 'held_floor':
        rays.track = replace(rays.track, floor_held=True)
    assert rays.collision_axis_interval(67.) is None


@pytest.mark.parametrize('lateral', [-.68, .68])
def test_asymmetric_tunnel_does_not_assume_wall_midpoint_is_axis(lateral):
    xyz, ring, labels = physical_column(lateral=lateral, wall_left=3.25, wall_right=-1.85)
    assert (3.25 - 1.85) / 2 == .7  # wall centre is not rail centre
    interval = rays_of(xyz, ring).collision_axis_interval(67.)
    assert interval is not None and interval[0] <= 0 <= interval[1]
    c, = matched(xyz, ring, labels)
    assert c.collision_core and any(stop_history(c))


@pytest.mark.parametrize('lateral', [-.68, .68])
def test_far_current_body_has_observed_core_with_raw_rail_support(lateral):
    xyz, ring, labels = physical_column(distance=137., lateral=lateral, top=4.12)
    c, = matched(xyz, ring, labels)
    assert c.collision_core and c.zone == 'gauge'
    assert any(stop_history(c))


def test_frame_without_track_or_config_cannot_claim_absolute_anchor():
    xyz, ring, _ = physical_column()
    rays = FrameRays(xyz, ring, xyz[:, 2] + 1.83, xyz[:, 1])
    assert rays.collision_axis_interval(67.) is None
