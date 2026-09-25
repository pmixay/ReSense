"""health.clear_cap (25.09, SCORECARD §6 row 6; opt-in, tried and not shipped): the
verified-clear distance stops at an unconfirmed or advisory object inside the envelope; STOP
and the decision are unchanged (docs/evidence/results/p3_clear_distance_2026-09-25.json)."""

import numpy as np
import pytest

from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame


def _run(det: Detector, frame: Frame, n: int):
    res = None
    for k in range(n):
        res = det.process(Frame(xyz=frame.xyz, intensity=frame.intensity, ring=frame.ring, stamp=0.1 * k,
                                meta=dict(frame.meta)))
    return res


def _cfg(on: bool) -> DetectorConfig:
    cfg = DetectorConfig()
    cfg.health.clear_cap = on
    return cfg


@pytest.fixture(scope="module")
def box_at_45():
    frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(5),
                                         specs=[ObstacleSpec(kind="box", size=(0.5, 0.5, 0.5), distance=45.0)])
    return frame


def test_unconfirmed_object_in_the_envelope_caps_clear_distance(box_at_45):
    """Three frames of a 0.5 m box on the axis at 45 m: not yet confirmed (0.5 s), so no STOP;
    without the cap the path reads clear far beyond it, with the cap it stops at the box."""
    off = _run(Detector(_cfg(False)), box_at_45, 3)
    on = _run(Detector(_cfg(True)), box_at_45, 3)
    assert not off.obstacle and not on.obstacle
    assert off.clear_distance > 100.0                           # the overclaim of v0.6
    assert on.clear_distance == pytest.approx(45.0, abs=1.0)
    assert on.health["candidate_distance"] == pytest.approx(on.clear_distance, abs=0.1)
    # nothing but clear_distance moves: same detections, same health level, same monitored range
    assert (on.obstacle, on.warning, on.health["level"]) == (off.obstacle, off.warning, off.health["level"])
    assert on.health["monitored_range"] == off.health["monitored_range"]


def test_a_near_real_obstacle_still_stops(box_at_45):
    """The same box, now held for 0.6 s: a STOP with the cap on, at the same distance as off,
    and clear_distance is the obstacle's distance."""
    frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(6),
                                         specs=[ObstacleSpec(kind="box", size=(0.6, 0.6, 0.6), distance=20.0)])
    off = _run(Detector(_cfg(False)), frame, 7)
    on = _run(Detector(_cfg(True)), frame, 7)
    assert on.obstacle and off.obstacle
    assert on.nearest_distance == pytest.approx(off.nearest_distance, abs=1e-6)
    assert on.nearest_distance == pytest.approx(20.0, abs=1.0)
    assert on.clear_distance == pytest.approx(on.nearest_distance, abs=0.1)
    assert [d.to_dict() for d in on.detections] == [d.to_dict() for d in off.detections]


def _cluster(distance, n_gauge, zone="gauge", reason=""):
    from resense.clustering import Cluster
    c = np.array([distance + 0.2, 0.0, 0.0])
    return Cluster(points_idx=np.zeros(0, dtype=int), n=10, n_raw=10, centroid=c, bbox_min=c - 0.2,
                   bbox_max=c + 0.2, distance=distance, lateral=0.0, height_min=0.5, height_max=1.0,
                   intensity=10.0, n_expected=10.0, score=1.0, zone=zone, n_gauge=n_gauge, reason=reason)


def test_clear_cap_distance_rules():
    """Which clusters cap: not the confirmed obstacle's own (its distance is the obstacle's),
    not one outside the strict envelope, not one seen too few frames; a column only while
    columns are not skipped."""
    from resense.config import GaugeConfig, HealthConfig
    from resense.detector import Candidates, clear_cap_distance
    from resense.tracking import Track

    obstacle = _cluster(12.0, 20)
    column = _cluster(20.0, 30, zone="warning", reason="column")
    beside = _cluster(25.0, 0, zone="warning")                 # advisory zone only
    fresh = _cluster(30.0, 5)                                   # first frame of an object in the envelope
    seen = _cluster(40.0, 5)
    tracks = [Track(id=1, centroid=obstacle.centroid, velocity=np.zeros(3), hits=6, last=obstacle,
                    zone_hist=[True] * 6, reported=True),
              Track(id=2, centroid=column.centroid, velocity=np.zeros(3), hits=9, last=column,
                    zone_hist=[False] * 9, column_hist=[True] * 9, column_hold=2, reported=True),
              Track(id=3, centroid=beside.centroid, velocity=np.zeros(3), hits=4, last=beside),
              Track(id=4, centroid=fresh.centroid, velocity=np.zeros(3), hits=1, last=fresh),
              Track(id=5, centroid=seen.centroid, velocity=np.zeros(3), hits=3, last=seen)]
    clusters = [obstacle, column, beside, fresh, seen]
    none = np.zeros(0, dtype=bool)
    empty = Candidates(xyz=np.zeros((0, 3), np.float32), dy=np.zeros(0), h=np.zeros(0), in_gauge=none,
                       intensity=np.zeros(0), idx=np.zeros(0, dtype=int), low=none)

    def cap(**kw):
        return clear_cap_distance(clusters, tracks, empty, np.zeros(0), np.zeros(0), GaugeConfig(),
                                  HealthConfig(clear_cap=True, **kw))

    assert cap(clear_cap_skip_columns=False) == 20.0            # the column (round 1); the obstacle skipped
    assert cap() == 30.0                                        # columns skipped: the unconfirmed object
    assert cap(clear_cap_min_hits=2) == 40.0
    assert cap(clear_cap_min_gauge=6) is None


def test_clear_cap_off_adds_no_output_key(tunnel):
    frame, _, _ = tunnel
    res = _run(Detector(_cfg(False)), frame, 2)
    assert "candidate_distance" not in res.health
