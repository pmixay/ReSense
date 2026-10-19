"""F1 lane switches of 19.10 (docs/evidence/f1_false_alarms_2026-10-19): all off by default.

* ``lowobj.local_rail_margin`` / ``rail_band_range`` (``lowobj.rail_reference_check``): a low cluster's top
  is compared with the frame's own rail lines around it, not only the model's (extrapolated) plane;
* ``lowobj.no_rail_low_within``: without the rail pair a farther low cluster is advisory;
* ``cluster.mount_cross_tol`` (``Detector._mount_cross_check``): a near-field cluster whose height band only
  a broken track model puts in the envelope is advisory;
* ``tracking.settle_min_hits`` (``Tracker._settle``): a settled static track mostly outside the gauge stays
  advisory whatever its last ten votes.
"""
from __future__ import annotations

import numpy as np
import pytest

from resense.clustering import Cluster
from resense.config import DetectorConfig, LowObjectConfig, TrackingConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.lowobj import local_rail_reference, low_free_mask, no_rail_advisory, rail_reference_check
from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
from resense.track import TrackModel
from resense.tracking import Tracker

FLOOR_Z = -1.5
RAIL_HEAD_Z = FLOOR_Z + 0.18
HALF = 0.5 * 1.59


def _low(x0, lat, top, width=0.3, length=0.3, n=6, idx=None):
    return Cluster(points_idx=np.arange(n) if idx is None else idx, n=n, n_raw=n,
                   centroid=np.array([x0 + length / 2, lat, top]), bbox_min=np.array([x0, lat - width / 2, 0.0]),
                   bbox_max=np.array([x0 + length, lat + width / 2, top]), distance=x0, lateral=lat,
                   height_min=0.0, height_max=top, intensity=10.0, n_expected=5.0, score=1.0,
                   zone="gauge", n_gauge=n, kind="low")


def _rails(x0, x1, left=0.0, right=0.0, step=0.4):
    """Rail-head returns along both rails (one per ``step`` m), heights ``left`` / ``right`` above the plane,
    plus bed returns 0.15 m below the plane."""
    xs = np.arange(x0, x1, step)
    X = np.concatenate([xs, xs, xs])
    dy = np.concatenate([np.full(xs.size, HALF), np.full(xs.size, -HALF), np.zeros(xs.size)])
    h = np.concatenate([np.full(xs.size, left), np.full(xs.size, right), np.full(xs.size, -0.15)])
    return X, dy, h


def test_local_reference_reads_the_rails_not_the_plane():
    cfg = LowObjectConfig()
    X, dy, h = _rails(30.0, 50.0, left=0.05, right=0.03)
    centre = _low(40.0, 0.0, 0.06)
    on_left = _low(40.0, HALF, 0.06)
    assert local_rail_reference(centre, X, dy, h, cfg, 1.59) == pytest.approx(0.04)
    assert local_rail_reference(on_left, X, dy, h, cfg, 1.59) == pytest.approx(0.05)
    # the cluster's own extent +- 0.3 m is not part of its reference: an object on the rail does not raise it
    Xo = np.concatenate([X, np.full(5, 40.15)])
    dyo = np.concatenate([dy, np.full(5, HALF)])
    ho = np.concatenate([h, np.full(5, 0.10)])
    assert local_rail_reference(on_left, Xo, dyo, ho, cfg, 1.59) == pytest.approx(0.05)
    # no rail returns: no reference (the existing rule alone)
    assert local_rail_reference(centre, X[2 * (X.size // 3):], dy[2 * (X.size // 3):], h[2 * (X.size // 3):],
                                cfg, 1.59) is None


def test_one_rail_only_serves_a_cluster_on_that_rail():
    cfg = LowObjectConfig()
    X, dy, h = _rails(30.0, 50.0, left=0.05)
    keep = dy > 0                               # the left rail only
    X, dy, h = X[keep], dy[keep], h[keep]
    assert local_rail_reference(_low(40.0, HALF, 0.1), X, dy, h, cfg, 1.59) == pytest.approx(0.05)
    assert local_rail_reference(_low(40.0, 0.0, 0.1), X, dy, h, cfg, 1.59) is None
    assert local_rail_reference(_low(40.0, -HALF, 0.1), X, dy, h, cfg, 1.59) is None


def test_rail_reference_check_keeps_what_rises_above_the_rails():
    cfg = LowObjectConfig(local_rail_margin=0.03)
    X, dy, h = _rails(30.0, 50.0, left=0.05, right=0.05)    # the model's plane 5 cm low here
    fixture = _low(40.0, 0.0, 0.06)                        # 1 cm above the rail heads: bed fixture
    box = _low(40.0, HALF, 0.11)                           # 6 cm above its rail head: an object on it
    assert [c is fixture for c in rail_reference_check([fixture, box], X, dy, h, cfg, 1.59)] == [True]
    assert rail_reference_check([fixture, box], X, dy, h, LowObjectConfig(local_rail_margin=0.0), 1.59) == []   # off


def test_rail_band_line_marks_a_rail_fitting_far_out():
    cfg = LowObjectConfig(local_rail_margin=0.0, rail_band_range=60.0, rail_band_margin=0.05)
    xs = np.arange(30.0, 50.0, 0.05)
    X = np.repeat(xs, 2)
    dy = np.tile([HALF - 0.05, HALF + 0.05], xs.size)
    h = np.full(X.size, 0.04)
    own = np.flatnonzero((X > 40.0) & (X < 40.3))
    fitting = _low(40.0, HALF, 0.07, width=0.12, idx=own)      # 3 cm above the band's own line
    tall = _low(40.0, HALF, 0.13, width=0.12, idx=own)         # 9 cm above it
    out = rail_reference_check([fitting, tall], X, dy, h, cfg, 1.59)
    assert len(out) == 1 and out[0] is fitting


def _scene(specs, seed=5):
    frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(seed), specs=specs)
    return frame


def _run(frame, n, cfg):
    det = Detector(cfg)
    res = None
    for k in range(n):
        res = det.process(Frame(xyz=frame.xyz, intensity=frame.intensity, stamp=0.1 * k))
    return res


@pytest.mark.parametrize("margin", [0.02, 0.03, 0.04])
@pytest.mark.parametrize("distance,lateral", [(10.0, -0.8), (25.0, -0.8), (45.0, 0.8), (50.0, 0.8)])
@pytest.mark.synthetic
def test_organizers_box_on_a_rail_survives_the_local_reference(distance, lateral, margin):
    """The organizers' 30 x 30 x 10 cm object on a rail head in the ray-cast tunnel (as test_envelope)
    is still a STOP with each registered margin of the local rail reference."""
    spec = ObstacleSpec(kind="box", size=(0.3, 0.3, 0.1), distance=distance, lateral=lateral, base_z=RAIL_HEAD_Z)
    cfg = DetectorConfig()
    cfg.lowobj.local_rail_margin = margin
    res = _run(_scene([spec]), 6, cfg)
    assert res.obstacle, [(c.kind, c.distance, c.height_max) for c in res.candidates]
    d = res.detections[0]
    assert abs(d.distance - distance) < 0.6 and abs(d.lateral - lateral) < 0.3


def test_no_rail_low_is_advisory_beyond_its_range():
    near, far, corridor = _low(10.0, 0.0, 0.08), _low(28.0, 0.0, 0.08), _corridor(range(5), 28.0)
    no_rail_advisory([near, far, corridor], 15.0)
    assert near.zone == "gauge" and far.zone == "warning" and far.demoted and far.reason == "no_rail_low"
    assert corridor.zone == "gauge" and not corridor.reason


def _corridor(points_idx, x, top=0.3):
    n = len(points_idx)
    return Cluster(points_idx=np.asarray(points_idx), n=n, n_raw=n, centroid=np.array([x, 0.0, 0.0]),
                   bbox_min=np.array([x, -1.0, 0.0]), bbox_max=np.array([x + 1.0, 1.0, top]), distance=x,
                   lateral=0.0, height_min=0.15, height_max=top, intensity=10.0, n_expected=50.0, score=1.0,
                   zone="gauge", n_gauge=n)


def test_mount_cross_check_demotes_only_what_the_mount_puts_outside():
    cfg = DetectorConfig()
    cfg.cluster.mount_cross_tol = 0.5
    det = Detector(cfg)
    det.calib.state.height, det.calib.state.status = 1.77, "ok"
    # a broken model: the "rail head" at 9.4 m is at z = +2.19 (the Falcon floor fit on the ceiling)
    det.track = TrackModel(floor_coef=np.array([0.0, 0.0439, 1.4382]), floor_range=(12.0, 112.5), center=0.0,
                           yaw=0.0, curvature=0.0, rail_offset=0.34)
    xyz = np.array([[9.5, 0.0, 2.45]] * 5 + [[6.0, -0.3, -0.3]] * 5, dtype=np.float32)
    ceiling, person = _corridor(range(5), 9.4), _corridor(range(5, 10), 6.0)
    det._mount_cross_check([ceiling, person], xyz)
    assert ceiling.zone == "warning" and ceiling.reason == "height_conflict" and ceiling.demoted
    assert person.zone == "gauge" and not person.reason        # 1.5 m above the mount's rail head: inside
    # amendment 6 (H'): a cluster the mount puts below the rail head is never demoted (a wrong mount height
    # must not hide a low near object); without mount_cross_above_only it would be
    below_xyz = np.array([[9.5, 0.0, -2.3]] * 5, dtype=np.float32)
    below = _corridor(range(5), 9.4)
    det._mount_cross_check([below], below_xyz)
    assert below.zone == "gauge" and not below.reason
    det.cfg.cluster.mount_cross_above_only = False
    below2 = _corridor(range(5), 9.4)
    det._mount_cross_check([below2], below_xyz)
    assert below2.zone == "warning" and below2.reason == "height_conflict"
    det.cfg.cluster.mount_cross_above_only = True
    # a model that agrees with the mount: nothing changes, wherever the points are
    det.track = TrackModel(floor_coef=np.array([0.0, 0.0, -1.98]), floor_range=(10.0, 40.0), center=0.0,
                           yaw=0.0, curvature=0.0, rail_offset=0.22)
    other = _corridor(range(5), 9.4)
    det._mount_cross_check([other], xyz)
    assert other.zone == "gauge" and not other.reason
    # no final calibration: no reference, nothing changes
    det.calib.state.status = "pending"
    det.track = TrackModel(floor_coef=np.array([0.0, 0.0439, 1.4382]), floor_range=(12.0, 112.5), center=0.0,
                           yaw=0.0, curvature=0.0, rail_offset=0.34)
    pending = _corridor(range(5), 9.4)
    det._mount_cross_check([pending], xyz)
    assert pending.zone == "gauge"


def _static(i, gauge, x=115.2, drift=0.0):
    c = _corridor(np.arange(8), x + drift * i)
    c.centroid = np.array([x + drift * i, 1.78, -0.7])
    c.lateral = 0.95
    c.zone = "gauge" if gauge else "warning"
    c.reason = "" if gauge else "beyond_axis"
    c.n_gauge = 4 if gauge else 0
    return c


def _votes(cfg, pattern, drift=0.0):
    tr = Tracker(cfg)
    zones = []
    for i, g in enumerate(pattern):
        tr.update([_static(i, g, drift=drift)], frame_dt=0.1)
        t = tr.tracks[0]
        zones.append(t.reported and t.zone == "gauge")
    return zones


def test_settled_static_track_needs_a_long_majority():
    """The Falcon 115 m support: inside the gauge 1 hit in 10, then 6 of 10 by chance."""
    pattern = ([False] * 9 + [True]) * 10 + [True, False, True, True, False, True, False, True, True, False]
    off = TrackingConfig(settle_min_hits=0)
    base = _votes(off, pattern)
    assert any(base[-10:])                                     # the base STOPs on the burst
    cfg = TrackingConfig(settle_min_hits=50, settle_check_z=False)
    assert not any(_votes(cfg, pattern)[-10:])                 # settled: advisory
    moving = _votes(cfg, pattern, drift=-0.5)                  # an approaching object (or a moving train)
    assert moving[-10:] == _votes(off, pattern, drift=-0.5)[-10:]
    inside = _votes(cfg, [True] * 110)                         # a static object inside the gauge stays a STOP
    assert all(inside[10:])


def test_candidate_values_in_the_class_and_the_yaml():
    """Integration of 19.10: every F1 switch off (F1a margin 0, H' tolerance 0; review B1 open, H' awaits its
    confirming run), the aec88d2 behaviour (proved on the full gate and the whole Falcon recording,
    docs/evidence/f1_false_alarms_2026-10-19). The candidate values stay as the sub-options: cross-rail 0.04, H'
    above the envelope only; S2, F1b and F1c opt-in (0)."""
    y = DetectorConfig()
    assert y.lowobj.local_rail_margin == 0 and not y.lowobj.local_rail_exclude_low
    assert y.lowobj.local_rail_cross_tol == pytest.approx(0.04)
    assert not y.lowobj.local_rail_advisory and y.cluster.mount_cross_tol == 0
    assert y.cluster.mount_cross_above_only
    assert y.tracking.settle_min_hits == 0
    assert y.lowobj.rail_band_range == 0 and y.lowobj.no_rail_low_within == 0
    assert DetectorConfig.from_yaml("configs/default.yaml").to_dict() == y.to_dict()


def _long_object_on_the_left_rail():
    """Rail-head returns on both rails at the model's plane, one ring crossing every 3 m (as at 40-50 m), and a
    long 8 cm object lying along the left rail at 35-41 m that the clustering split into six 0.6 m pieces 1 m
    apart (independent review 1, B1)."""
    X, dy, h = _rails(25.0, 55.0, step=3.0)
    pieces, xs, ds, hs = [], [], [], []
    n0 = X.size
    for k in range(6):
        x0 = 35.0 + k * 1.0
        px = np.arange(x0, x0 + 0.6, 0.1)
        idx = np.arange(n0 + len(xs), n0 + len(xs) + px.size)
        xs += list(px)
        ds += [HALF] * px.size
        hs += [0.08] * px.size
        pieces.append(_low(x0, HALF, 0.08, length=0.6, idx=idx))
    return (np.concatenate([X, xs]), np.concatenate([dy, ds]), np.concatenate([h, hs])), pieces


def test_pieces_of_a_long_object_on_a_rail_keep_their_reference():
    (X, dy, h), pieces = _long_object_on_the_left_rail()
    cfg = LowObjectConfig(local_rail_margin=0.01, local_rail_cross_tol=0.0)
    # the first measured version (every return counts): the other pieces raise each piece's line -> all flagged
    assert len(rail_reference_check(pieces, X, dy, h, cfg, 1.59)) == 6
    # amendment 6 option: the lines leave out every low cluster's returns -> none flagged
    free = low_free_mask(X.size, pieces)
    assert rail_reference_check(pieces, X, dy, h, cfg, 1.59, free) == []
    assert all(local_rail_reference(c, X[free], dy[free], h[free], cfg, 1.59) == pytest.approx(0.0) for c in pieces)
    # amendment 7 (the candidate): no exclusion; the left line (raised by the pieces) disagrees with the right
    # one by more than 0.04 m -> the lower line -> none flagged
    cross = LowObjectConfig(local_rail_margin=0.01, local_rail_cross_tol=0.04)
    assert rail_reference_check(pieces, X, dy, h, cross, 1.59) == []
    assert all(local_rail_reference(c, X, dy, h, cross, 1.59) == pytest.approx(0.0) for c in pieces)


def test_both_rails_raised_together_still_reject_a_rail_fragment():
    """The ride's false STOPs (frames 2666-2676): the model's plane is ~0.1 m low, both rails read high together;
    a rail-head fragment does not rise above them, with or without the cross-rail check."""
    X, dy, h = _rails(30.0, 50.0, left=0.11, right=0.10)
    frag = _low(40.0, HALF - 0.08, 0.108, idx=np.array([0]))
    for cfg in (LowObjectConfig(local_rail_margin=0.01, local_rail_cross_tol=0.04), LowObjectConfig(local_rail_margin=0.01)):
        assert rail_reference_check([frag], X, dy, h, cfg, 1.59) == [frag]


def test_a_cluster_failing_the_reference_is_advisory_not_silent():
    X, dy, h = _rails(30.0, 50.0, left=0.05, right=0.05)
    xyz = np.stack([X, dy, h], axis=1).astype(np.float32)
    for advisory in (True, False):
        cfg = DetectorConfig()
        cfg.lowobj.local_rail_margin = 0.01           # the F1a candidate (off by default since the 19.10 integration)
        cfg.lowobj.local_rail_advisory = advisory
        det = Detector(cfg)
        det._low_height = []
        fixture, box = _low(40.0, 0.0, 0.06, idx=np.array([0])), _low(40.0, HALF, 0.11, idx=np.array([1]))
        out = det._rail_reference([fixture, box], xyz, dy, h)
        if advisory:
            assert out == [fixture, box] and fixture.zone == "warning" and fixture.reason == "below_rail_ref"
            assert fixture.demoted and box.zone == "gauge" and not box.reason
        else:
            assert out == [box] and fixture.low_height_weak and det._low_height == [fixture]
