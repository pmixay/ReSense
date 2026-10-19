"""Local H1 proof follows observed paired rails, independent of wall profiles."""
import numpy as np
import pytest

from test_column_axis_anchor import rays_of
from test_column_collision_core import matched, physical_column, stop_history


def rail_and_body_only(distance, lateral):
    xyz, ring, labels = physical_column(distance=distance, lateral=lateral, top=4.12)
    keep = (labels != 0) | (xyz[:, 2] < -1.8)
    return xyz[keep], ring[keep], labels[keep]


def test_body_inside_observed_rail_stations_needs_no_wall_continuation():
    xyz, ring, labels = rail_and_body_only(17., 0.)
    c, = matched(xyz, ring, labels)
    assert c.collision_core and any(stop_history(c))
    rays = rays_of(xyz, ring)
    assert rays.collision_axis_interval(17.) == rays.collision_axis_anchor()


@pytest.mark.parametrize('error', [-.6, 0., .6])
@pytest.mark.parametrize('lateral', [-1.29, 1.29])
def test_local_observed_rails_do_not_turn_outside_body_into_STOP(error, lateral):
    xyz, ring, labels = rail_and_body_only(17., lateral)
    assert np.all(np.abs(xyz[labels == 1, 1]) > 1.05)
    for c in matched(xyz, ring, labels, axis_error=error):
        assert not c.collision_core and not any(stop_history(c))


def test_local_rail_proof_does_not_extrapolate_beyond_observed_stations():
    xyz, ring, labels = rail_and_body_only(67., .68)
    c, = matched(xyz, ring, labels)
    assert not c.collision_core and not any(stop_history(c))


def test_local_rail_proof_abstains_without_rail_pair():
    xyz, ring, labels = physical_column(distance=17., rails=False)
    for c in matched(xyz, ring, labels):
        assert not c.collision_core and not any(stop_history(c))
