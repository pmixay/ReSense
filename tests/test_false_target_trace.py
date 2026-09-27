"""Diagnostic replay must observe matching without changing detector state."""
from copy import deepcopy

import numpy as np

from resense.clustering import Cluster
from resense.config import TrackingConfig
from resense.tracking import Tracker
from scripts.trace_false_targets import observe_associations, selection


def cluster(x, y=0.0, z=0.0):
    c = np.array([x, y, z], dtype=float)
    return Cluster(points_idx=np.arange(3), n=10, n_raw=20, centroid=c,
                   bbox_min=c - .25, bbox_max=c + .25, distance=x - .25, lateral=y,
                   height_min=.2, height_max=.7, intensity=30.0, n_expected=10,
                   score=1.0, zone="gauge", n_gauge=10)


def test_observer_preserves_tracking_on_match_miss_and_reseed():
    plain, observed = Tracker(TrackingConfig()), Tracker(TrackingConfig())
    observe_associations(observed)
    frames = [[cluster(30)], [cluster(29)], [], [cluster(27, .1)], [cluster(26, .2)]]
    for i, clusters in enumerate(frames):
        if i == 3:
            angle = .01
            rotation = np.array([[np.cos(angle), -np.sin(angle), 0],
                                 [np.sin(angle), np.cos(angle), 0], [0, 0, 1]])
            plain.reseed(rotation, 5)
            observed.reseed(rotation, 5)
        plain.update(deepcopy(clusters), frame_dt=.1)
        observed.update(deepcopy(clusters), frame_dt=.1)
        assert len(plain.tracks) == len(observed.tracks)
        for a, b in zip(plain.tracks, observed.tracks):
            for key, value in a.__dict__.items():
                if key == "last":
                    assert value.__dict__.keys() == b.last.__dict__.keys()
                    for ck, cv in value.__dict__.items():
                        np.testing.assert_equal(cv, b.last.__dict__[ck])
                else:
                    np.testing.assert_equal(value, b.__dict__[key])
        if i in (0, 2):
            assert observed.observed_associations == {}
    match = observed.observed_associations[1]
    assert match["previous_hits"] == 3
    np.testing.assert_allclose(match["residual"], observed.tracks[0].centroid - match["predicted"])


def test_selection_uses_piece_local_identity_and_bounded_context():
    rows = [{"detections": []} for _ in range(30)]
    rows[0]["detections"] = [{"id": 7}]
    rows[10]["detections"] = [{"id": 7}, {"id": 2}]
    rows[29]["detections"] = [{"id": 7}]
    events, snapshots = selection(rows)
    assert events == {7: [0, 10, 29], 2: [10]}
    assert {0, 10, 29}.issubset(snapshots[7])
    assert all(0 <= i < 30 for indexes in snapshots.values() for i in indexes)
