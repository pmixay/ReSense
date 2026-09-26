"""A1: ego approach allowance cannot enlarge the transverse association radius."""
from dataclasses import replace

import numpy as np
import pytest

from resense.clustering import Cluster
from resense.config import TrackingConfig
from resense.tracking import Tracker


def cluster(x, y=0.0, z=0.0, thin=False):
    center = np.array([x, y, z], dtype=float)
    return Cluster(points_idx=np.arange(12), n=12, n_raw=12, centroid=center,
                   bbox_min=center - .2, bbox_max=center + .2, distance=x - .2,
                   lateral=y, height_min=.2, height_max=.6, intensity=30.,
                   n_expected=12, score=1., zone="gauge", n_gauge=12, thin=thin)


def tracker():
    return Tracker(replace(TrackingConfig(), confirm_hits=1, confirm_time_s=0,
                           conf_threshold=0, near_escalate_voxels=0))


@pytest.mark.parametrize("thin", [False, True])
def test_transverse_jump_does_not_inherit_confirmation(thin):
    tr = tracker()
    tr.update([cluster(10)], frame_dt=.1)
    assert tr.tracks[0].reported
    jumped = cluster(9.5, 2., thin=thin)
    tr.update([] if thin else [jumped], frame_dt=.1, thin=[jumped] if thin else None)
    old = next(t for t in tr.tracks if t.id == 1)
    assert old.misses == 1 and old.hits == 1
    assert old.last.centroid[1] == 0
    if thin:
        assert len(tr.tracks) == 1  # a thin fragment never creates a new track
    else:
        assert len(tr.tracks) == 2


@pytest.mark.parametrize("thin", [False, True])
@pytest.mark.parametrize("dt,approach", [(.1, 4.7), (.3, 9.7)])
def test_pure_approach_uses_measured_interval(thin, dt, approach):
    tr = tracker()
    tr.update([cluster(40)], frame_dt=.1)
    target = cluster(40 - approach, thin=thin)
    tr.update([] if thin else [target], frame_dt=dt, thin=[target] if thin else None)
    assert len(tr.tracks) == 1 and tr.tracks[0].hits == 2 and tr.tracks[0].misses == 0


def test_capsule_rejects_diagonal_corner_and_preserves_ranking():
    tr = tracker()
    predicted = np.array([[40., 0., 0.]])
    candidates = np.array([[36., 2., 0.], [39., .5, .5], [38., 0., 0.], [43., 0., 0.]])
    distances = tr._association_distances(predicted, candidates, [40.], 2.5)[0]
    assert np.isinf(distances[0])  # old sphere allowed this diagonal corner
    assert np.isinf(distances[3])  # receding motion gets no ego allowance
    np.testing.assert_allclose(distances[1:3], [np.sqrt(1.5), 2.])


def test_capsule_boundary_and_original_total_distance_bound():
    tr = Tracker(replace(TrackingConfig(), gate_base=2., gate_per_m=0.))
    predicted = np.zeros((1, 3))
    candidates = np.array([[-4., 0., 0.], [-2., 2., 0.], [0., 0., 2.],
                           [-4.0001, 0., 0.], [-2., 2.0001, 0.], [.1, 0., 2.]])
    actual = tr._association_distances(predicted, candidates, [0.], 2.)[0]
    assert np.all(np.isfinite(actual[:3]))
    assert np.all(np.isinf(actual[3:]))
    for candidate, distance in zip(candidates, actual):
        if np.isfinite(distance):
            assert distance <= 2. + (2. if candidate[0] < 0 else 0.)


def test_velocity_and_reseed_are_used_before_gating():
    tr = tracker()
    tr.update([cluster(40)], frame_dt=.1)
    tr.update([cluster(38, .1)], frame_dt=.1)
    angle = .03
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0.],
                         [np.sin(angle), np.cos(angle), 0.], [0., 0., 1.]])
    tr.reseed(rotation, 5)
    expected = tr.tracks[0].centroid + tr.tracks[0].velocity
    tr.update([cluster(*expected)], frame_dt=.1)
    assert len(tr.tracks) == 1 and tr.tracks[0].hits == 3
    np.testing.assert_allclose(tr.tracks[0].centroid, expected)
