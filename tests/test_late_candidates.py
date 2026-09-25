"""Late detector candidates behind default-off flags (captain action 11, go / no-go 26.09).

* ``cluster.short_signature_max_length`` (P3 / P4 candidate of 24.09): the ``elevated`` and
  ``floating`` signatures do not demote a cluster as short and as near as the organizers' test
  objects. Off by default; the default output must not change.
* ``cluster.floating_long_min_length`` (25.09, station false STOPs): the ``floating`` shape also
  demotes a cluster near the axis when it is long along the track (an overhead duct / tray / beam
  along the track, ~104 m ahead of the standing train in ``squareT_platform_squareT_switch``).
  On (3.0 m) since 25.09: decided on the ride with the regression gate
  (docs/evidence/results/rules_decision_2026-09-25.json); the short-signature rule stays off.
* ``cluster.floating_long_min_bottom`` (review 25.09): that along-track branch skipped the
  ``signature_min_lateral`` guard, so a tray / duct / pipe fallen onto the axis and hanging 0.7-1.9 m
  above the rail was demoted to advisory; the branch now needs the lowest point above this height
  (overhead infrastructure: the station structure has its bottom at ~2.2 m).
* the rail shadow of a large near object (P3, 25.09; set O #1): ``track.floor_shadow_height``
  (the bed and the rail pair are fitted in front of the object's shadow or held),
  ``cluster.oversize_split_max_length`` (an object touching a long line at the corridor edge is
  not dropped with it) and ``cluster.gauge_distance`` (the distance is that of the part inside
  the envelope); docs/evidence/results/p3_rail_shadow_2026-09-25.json. The safety review of 25.09
  (docs/evidence/results/p3_review_fixes_2026-09-25.json): the distance on the envelope widened by
  the axis-uncertainty margin (never beyond the entry), ``track.floor_shadow_max_hold`` (a hold
  cannot lock), adjacent shadow bins and the face nearest the shadow.
* ``cluster.far_axis_both_sides`` (25.09, far_switch; 0 = off): beyond the height reference a far
  obstacle needs both fitted tunnel boundaries to support the axis (mode 1 on every frame, the
  corridor ends there; mode 2 on bent frames only, would-be obstacles demoted); at the 147.5 m
  switch parts of ``squareT_platform_squareT_switch`` the curvature came from a hall wall seen only
  to 72-92 m.
* ``track.walls_min_far_support`` (25.09, platform_end; 0 = off) and ``track.floor_far_min_width``
  (25.09, bed_bin; 0 = off): tried, not shipped; the default output must not change.
"""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import numpy as np
import pytest

from resense.clustering import _advisory_reason, _Blob, find_clusters
from resense.config import ClusterConfig, DetectorConfig
from resense.detector import Detector
from resense.frame import Frame

ROOT = Path(__file__).resolve().parents[1]


def _box(x0: float, length: float, lateral: float, bottom: float, height: float, width: float):
    """A cluster of points filling a box: (blob, dy, h) with the track axis at y = 0, rail head at z = 0."""
    g = np.stack(np.meshgrid(np.linspace(0, length, 6), np.linspace(-width / 2, width / 2, 4),
                             np.linspace(0, height, 4), indexing="ij"), axis=-1).reshape(-1, 3)
    xyz = (g + np.array([x0, lateral, bottom])).astype(np.float32)
    idx = np.arange(xyz.shape[0])
    return _Blob.of(xyz, idx, xyz.shape[0]), xyz[:, 1].astype(np.float64), xyz[:, 2].astype(np.float64)


def _reason(cfg, x0, length, lateral, bottom, height, width):
    b, dy, h = _box(x0, length, lateral, bottom, height, width)
    return _advisory_reason(b, x0, float(dy.mean()), "gauge", dy, h, cfg, 1e9, None)


def test_short_signature_rule_is_off_by_default():
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        assert cfg.cluster.short_signature_max_length == 0.0
    cfg = ClusterConfig()
    # the organizers' 0.3 m cube floating mid-envelope off the centre, their 2 x 2 m box at the top
    assert _reason(cfg, 50.0, 0.3, 0.75, 1.0, 0.3, 0.3) == "floating"
    assert _reason(cfg, 40.0, 2.0, 0.0, 2.3, 0.7, 2.2) == "elevated"


def test_short_signature_rule_when_on():
    cfg = replace(ClusterConfig(), short_signature_max_length=3.0, short_signature_max_distance=100.0)
    assert _reason(cfg, 50.0, 0.3, 0.75, 1.0, 0.3, 0.3) == ""               # short, near: an obstacle
    assert _reason(cfg, 40.0, 2.0, 0.0, 2.3, 0.7, 2.2) == ""
    assert _reason(cfg, 104.0, 0.3, 0.75, 1.0, 0.3, 0.3) == "floating"      # beyond 100 m: demoted as before
    assert _reason(cfg, 60.0, 5.5, 0.75, 2.0, 0.6, 0.2) == "floating"       # 5.5 m long structure: demoted
    assert _reason(cfg, 40.0, 4.0, 0.0, 2.3, 0.7, 2.2) == "elevated"
    assert _reason(cfg, 50.0, 0.3, 0.2, 1.0, 0.3, 0.3) == ""                # near the axis: never floating


def test_long_floating_rule():
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        assert cfg.cluster.floating_long_min_length == 3.0                     # shipped on since 25.09
    # the 104 m structure: 5.5 m along the track, 0.2 m wide, 0.65 m tall, bottom 2.2 m, 0.5 m off the axis
    off = replace(ClusterConfig(), floating_long_min_length=0.0)
    assert _reason(off, 104.0, 5.5, 0.5, 2.2, 0.65, 0.2) == ""               # rule off: an obstacle
    on = ClusterConfig()                                                     # the shipped default (3.0)
    assert _reason(on, 104.0, 5.5, 0.5, 2.2, 0.65, 0.2) == "floating"
    assert _reason(on, 50.0, 0.3, 0.0, 1.0, 0.3, 0.3) == ""                  # the organizers' floating cube
    assert _reason(on, 30.0, 0.1, 0.0, 1.0, 1.1, 0.05) == ""                 # a cable hanging near the axis
    assert _reason(on, 104.0, 5.5, 0.5, 1.0, 1.6, 0.2) == ""                 # taller than a floating shape
    both = replace(on, short_signature_max_length=3.0)
    assert _reason(both, 104.0, 5.5, 0.5, 2.2, 0.65, 0.2) == "floating"     # long: not exempt as short


LONG_MIN_BOTTOM = 1.6     # the shipped cluster.floating_long_min_bottom (m above the rail head, 25.09)


def test_long_floating_rule_needs_an_overhead_bottom():
    """Review 25.09: the along-track branch applies only to a cluster whose lowest point is as high
    as overhead infrastructure; the off-centre floating path is unchanged."""
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        assert cfg.cluster.floating_long_min_bottom == LONG_MIN_BOTTOM
    on = ClusterConfig()
    old = replace(on, floating_long_min_bottom=0.0)                          # the 25.09 rule
    for bottom in (1.0, 1.5):
        # the finding: a 4.0 x 0.3 x 0.5 m tray / duct / pipe on the axis hanging in the envelope
        assert _reason(old, 60.0, 4.0, 0.0, bottom, 0.5, 0.3) == "floating"
        assert _reason(on, 60.0, 4.0, 0.0, bottom, 0.5, 0.3) == ""           # now an obstacle
        assert _reason(on, 45.0, 4.0, 0.3, bottom, 0.5, 0.3) == ""
    # just below / above the threshold
    assert _reason(on, 60.0, 4.0, 0.0, LONG_MIN_BOTTOM - 0.05, 0.5, 0.3) == ""
    assert _reason(on, 60.0, 4.0, 0.0, LONG_MIN_BOTTOM + 0.05, 0.5, 0.3) == "floating"
    # the station structure (~104 m in squareT_platform_squareT_switch): bottom 2.2 m, still demoted
    assert _reason(on, 104.0, 5.5, 0.5, 2.2, 0.65, 0.2) == "floating"
    assert _reason(on, 104.0, 3.9, 0.0, 2.2, 0.65, 0.3) == "floating"
    # off the centre the floating shape needs neither the length nor the bottom height
    assert _reason(on, 50.0, 4.0, 0.75, 1.0, 0.5, 0.3) == "floating"
    assert _reason(on, 50.0, 0.3, 0.75, 1.0, 0.3, 0.3) == "floating"


AXIS_Y = 0.25                   # synthetic_tunnel_frame: the track axis
RAIL_HEAD_Z = -1.5 + 0.18       # the bed at -1.5, rails 0.18 m tall


def _box_surface(x0: float, length: float, lateral: float, bottom: float, height: float, width: float,
                 step: float = 0.1) -> np.ndarray:
    """Points on the faces of a box (front, both sides, top, bottom) every ``step`` m, in the
    vehicle frame of ``synthetic_tunnel_frame``; ``bottom`` is above the rail head. A single
    ray-cast frame at 40-60 m returns only the 0.3 x 0.5 m front face of a box hanging near the
    sensor height, which the long rule never sees as long; the injected faces are the whole box
    as the approach (or a sensor above or below it) sees it."""
    xs = np.arange(0.0, length + 1e-6, step)
    ys = np.linspace(-width / 2, width / 2, max(int(round(width / step)) + 1, 2))
    zs = np.linspace(0.0, height, max(int(round(height / step)) + 1, 2))
    faces = []
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    faces += [np.stack([X.ravel(), np.full(X.size, y), Z.ravel()], 1) for y in (ys[0], ys[-1])]
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    faces += [np.stack([X.ravel(), Y.ravel(), np.full(X.size, z)], 1) for z in (zs[0], zs[-1])]
    Y, Z = np.meshgrid(ys, zs, indexing="ij")
    faces.append(np.stack([np.zeros(Y.size), Y.ravel(), Z.ravel()], 1))
    return (np.concatenate(faces) + np.array([x0, AXIS_Y + lateral, RAIL_HEAD_Z + bottom])).astype(np.float32)


def _run_with(tunnel_frame: Frame, pts: np.ndarray, cfg: DetectorConfig, n: int = 6):
    frame = Frame(xyz=np.concatenate([tunnel_frame.xyz, pts]),
                  intensity=np.concatenate([tunnel_frame.intensity, np.full(len(pts), 30.0, np.float32)]))
    det = Detector(cfg)
    res = None
    for k in range(n):
        res = det.process(Frame(xyz=frame.xyz, intensity=frame.intensity, stamp=0.1 * k))
    return res


def test_long_box_hanging_on_the_axis_is_a_stop(tunnel):
    """End to end on the ray-cast tunnel: an on-axis 4.0 x 0.3 x 0.5 m box (a fallen cable tray /
    duct / pipe) with its bottom 1.0 or 1.5 m above the rail head at 40-60 m is a STOP with the
    shipped defaults; the 25.09 rule (no bottom condition) demoted it to advisory ``floating``.
    The station-like structure with its bottom at 2.2 m stays advisory."""
    frame, _, _ = tunnel
    old = DetectorConfig()
    old.cluster = replace(old.cluster, floating_long_min_bottom=0.0)
    for dist, bottom in ((60.0, 1.0), (45.0, 1.5), (40.0, 1.0)):
        pts = _box_surface(dist, 4.0, 0.0, bottom, 0.5, 0.3)
        res = _run_with(frame, pts, DetectorConfig())
        assert res.obstacle, [(c.distance, c.zone, c.reason, c.size.round(2).tolist()) for c in res.candidates]
        d = res.detections[0]
        assert d.zone == "gauge" and d.reason == "" and abs(d.distance - dist) < 0.5
        assert d.size[0] > 3.0 and abs(d.height_min - bottom) < 0.1           # seen whole, not a fragment
        res = _run_with(frame, pts, old)
        assert not res.obstacle and res.warning and res.warnings[0].reason == "floating"
    res = _run_with(frame, _box_surface(60.0, 5.5, 0.5, 2.2, 0.65, 0.2), DetectorConfig())
    assert not res.obstacle and res.warning and res.warnings[0].reason == "floating"


def _first_stop(tunnel_frame: Frame, seq, cfg: DetectorConfig):
    """Index of the first STOP frame of a sequence of injected point sets (10 Hz), or None."""
    det = Detector(cfg)
    for k, pts in enumerate(seq):
        res = det.process(Frame(xyz=np.concatenate([tunnel_frame.xyz, pts]),
                                intensity=np.concatenate([tunnel_frame.intensity, np.full(len(pts), 30.0, np.float32)]),
                                stamp=0.1 * k))
        if res.obstacle:
            return k
    return None


def test_column_hold_person_beside_a_column_is_a_stop(tunnel):
    """End to end on the ray-cast tunnel with the shipped tracking.column_hold (25.09, EXPERIMENTS
    3a): a person-size box (0.3 x 0.5 x 1.8 m) on the axis at 40-80 m with a column (0.3 x 0.3 m,
    2.8 m tall) straddling the envelope edge at the same distance is a STOP on the frame that
    confirms the person alone; the column alone is advisory ``column``. A person who stood in
    front of the column (one narrow 'column' cluster) and steps onto the axis: fewer than
    column_hold such frames cost nothing; column_hold or more hold the STOP back until those hits
    leave the 10-hit zone window, zone_window - column_hold frames after the step at the latest
    (the shipped 2: 8 frames after the step instead of 4, +0.4 s; 1 would hold it back after a single
    such frame)."""
    frame, _, _ = tunnel
    cfg = DetectorConfig()
    hold, zw = cfg.tracking.column_hold, cfg.tracking.zone_window
    assert hold >= 1
    off = DetectorConfig()
    off.tracking = replace(off.tracking, column_hold=0)
    confirm = cfg.tracking.frames_to_confirm() - 1                  # frame index of the first STOP: 4
    for dist in (40.0, 60.0, 80.0):
        column = _box_surface(dist, 0.3, 0.95, 0.0, 2.8, 0.3)
        person = _box_surface(dist, 0.3, 0.0, 0.0, 1.8, 0.5)
        det = Detector(cfg)
        for k in range(8):
            res = det.process(Frame(xyz=np.concatenate([frame.xyz, column]), stamp=0.1 * k,
                                    intensity=np.concatenate([frame.intensity, np.full(len(column), 30.0, np.float32)])))
            assert not res.obstacle
        assert res.warning and res.warnings[0].reason == "column"
        assert _first_stop(frame, [person] * 8, cfg) == confirm
        assert _first_stop(frame, [np.concatenate([column, person])] * 8, cfg) == confirm, dist
    column = _box_surface(60.0, 0.3, 0.95, 0.0, 2.8, 0.3)
    front = np.concatenate([column, _box_surface(59.65, 0.3, 0.95, 0.0, 1.8, 0.5)])   # the person in front of it
    stepped = np.concatenate([column, _box_surface(60.0, 0.3, 0.0, 0.0, 1.8, 0.5)])
    for m in sorted({max(hold - 1, 1), hold}):
        seq = [front] * m + [stepped] * (zw + 2)
        base = _first_stop(frame, seq, off) - m                          # without the hold: 3-5 frames after the step
        got = _first_stop(frame, seq, cfg) - m
        assert base <= confirm
        if m < hold:
            assert got == base, (m, got, base)
        else:
            assert base < got <= zw - hold, (m, got, base)


# --- the rail shadow of a large near object (P3, 25.09) ------------------------------------------

def _rail_shadow_cfg(on: bool) -> DetectorConfig:
    """The shipped config (the three rail-shadow rules on since 25.09, candidate B2) or the same
    with the three rules off (the behaviour before 25.09)."""
    cfg = DetectorConfig()
    if not on:
        cfg.track = replace(cfg.track, floor_shadow_height=0.0)
        cfg.cluster = replace(cfg.cluster, oversize_split_max_length=0.0, gauge_distance=False)
    return cfg


def _edge_line(x0: float, x1: float, dy: float = 1.37, h: float = 0.2) -> np.ndarray:
    """A line of points along the corridor edge (a conductor rail: set O, dy 1.35-1.40 m, 0.16-0.38 m
    above the rail head), every 5 cm, in the vehicle frame of ``synthetic_tunnel_frame``."""
    xs = np.arange(x0, x1, 0.05)
    return np.stack([xs, np.full(xs.size, AXIS_Y + dy), np.full(xs.size, RAIL_HEAD_Z + h)], 1).astype(np.float32)


def _face(x: float, lateral: float = 0.2, width: float = 2.0, bottom: float = 0.05, height: float = 1.8,
          step: float = 0.05) -> np.ndarray:
    """The front face of the organizers' 2 x 2 m box (set O keeps only the face), in the tunnel frame."""
    Y, Z = np.meshgrid(np.arange(-width / 2, width / 2 + 1e-6, step), np.arange(0.0, height + 1e-6, step), indexing="ij")
    return (np.stack([np.full(Y.size, x), Y.ravel(), Z.ravel()], 1)
            + np.array([0.0, AXIS_Y + lateral, RAIL_HEAD_Z + bottom])).astype(np.float32)


def test_rail_shadow_rules_shipped():
    """On since 25.09 with the values of candidate B2 (docs/evidence/results/p3_rail_shadow_2026-09-25.json):
    a shadow start beyond 30 m (40 m fired on doubleT_platform) and a split beyond 30 m (the far
    corridor's long sparse clusters) each added a false alarm in round 1."""
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        t, c = cfg.track, cfg.cluster
        assert (t.floor_shadow_height, t.floor_shadow_range, t.floor_shadow_min_bins) == (1.0, 30.0, 5)
        assert t.floor_shadow_max_hold == 20                              # review 25.09: set O #1 holds 14 in a row
        assert (c.oversize_split_max_length, c.oversize_split_max_distance, c.gauge_distance) == (3.0, 30.0, True)


def test_oversize_split_and_gauge_distance():
    """Clustering only: the set O box face at 15 m touching a 12 m line at the corridor edge forms
    one cluster longer than max_extent (8 m): dropped whole when off; with the split it is the
    face, 2 m wide, at 15 m; beyond oversize_split_max_distance (30 m) it stays dropped. With the
    line shorter than max_extent the cluster is kept either way, but it starts at the line's near
    end (3 m) unless gauge_distance is on (it needs the gauge profile: without it the distance
    stays the cluster's nearest point)."""
    from resense.gauge import corridor_coordinates, corridor_mask, gauge_core_mask
    from resense.track import TrackModel
    tm = TrackModel(floor_coef=np.array([0.0, 0.0, -1.5]), floor_range=(0.0, 250.0), center=AXIS_Y,
                    yaw=0.0, curvature=0.0, rail_offset=0.18)
    base = DetectorConfig()

    def clusters(pts, split, gd, reach=30.0, gauge=base.gauge):
        cfg = replace(base.cluster, oversize_split_max_length=split, gauge_distance=gd,
                      oversize_split_max_distance=reach)
        dy, h = corridor_coordinates(pts, tm)
        m, strict = corridor_mask(pts, tm, base.gauge, dy, h)
        strict = strict & gauge_core_mask(dy, h, pts[:, 0], base.gauge)
        return find_clusters(pts[m], np.full(int(m.sum()), 10.0, np.float32), dy[m], h[m], strict[m], cfg,
                             gauge=gauge)

    long_line = np.concatenate([_face(15.0), _edge_line(3.0, 15.0)])
    assert clusters(long_line, 0.0, False) == []
    for gd in (False, True):
        (c,) = clusters(long_line, 3.0, gd)
        assert c.zone == "gauge" and abs(c.distance - 15.0) < 0.01 and c.size[0] < 0.1 and c.size[1] > 1.5
    far = np.concatenate([_face(45.0), _edge_line(33.0, 45.0)])
    assert clusters(far, 3.0, True) == []                               # beyond 30 m: dropped as before
    (c,) = clusters(far, 3.0, True, reach=60.0)
    assert abs(c.distance - 45.0) < 0.01
    short_line = np.concatenate([_face(9.0), _edge_line(3.0, 9.0)])
    (c,) = clusters(short_line, 3.0, False)
    assert c.zone == "gauge" and abs(c.distance - 3.0) < 0.01          # the line's near end
    (c,) = clusters(short_line, 3.0, True)
    assert c.zone == "gauge" and abs(c.distance - 9.0) < 0.01          # the face
    (c,) = clusters(short_line, 3.0, True, gauge=None)
    assert abs(c.distance - 3.0) < 0.01                                 # no profile: the nearest point
    clear = _edge_line(3.0, 30.0)                                       # the line alone: nothing either way
    assert clusters(clear, 3.0, True) == clusters(clear, 0.0, False) == []


@lru_cache(maxsize=1)
def _box_approach():
    """Ray-cast frames of a 0.5 x 2 x 2 m box standing on the axis, approaching from 36 to 6 m at
    2 m per frame (20 m/s): it hides the bed band behind it (the roof is all the fit sees there),
    as the organizers' 2 x 2 m box of set O does at 10-20 m."""
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
    out = []
    for k, d in enumerate(np.arange(36.0, 5.0, -2.0)):
        f, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(100 + k),
                                         specs=[ObstacleSpec(kind="box", size=(0.5, 2.0, 2.0), distance=float(d))])
        out.append((float(d), f))
    return out


def _drive(tunnel_frame: Frame, seq, cfg: DetectorConfig):
    """Warm the detector up on the clear tunnel (8 frames), then play ``seq``; returns the results."""
    det = Detector(cfg)
    for k in range(8):
        det.process(Frame(xyz=tunnel_frame.xyz, intensity=tunnel_frame.intensity, stamp=0.1 * k))
    return [det.process(Frame(xyz=f.xyz, intensity=f.intensity, stamp=0.1 * (k + 8))) for k, (_, f) in enumerate(seq)]


def test_rail_shadow_bed_and_distance(tunnel):
    """End to end on the ray-cast tunnel: without the rules the roof behind the box tilts the bed
    fit (the rail head at 20 m metres off) and the bed a few metres ahead becomes the reported
    obstacle; with them the rail head is never further off than without them, within 0.1 m from
    the frame the shadow is found (its start within floor_shadow_range, 30 m: the box at 22 m;
    before, the drift is the same 0.04-0.15 m as without), the bed is held once too little of it
    is left in front of the box, and every STOP reports the box's own distance. The first STOP
    comes on the same frame."""
    frame, _, _ = tunnel
    seq = _box_approach()
    off = _drive(frame, seq, _rail_shadow_cfg(False))
    on = _drive(frame, seq, _rail_shadow_cfg(True))
    dist = [d for d, _ in seq]
    err_off = [abs(float(r.track.rail_z(20.0)) - RAIL_HEAD_Z) for r in off]
    assert max(err_off) > 1.0
    assert any(r.obstacle and r.nearest_distance < d - 3.0 for d, r in zip(dist, off))
    first = [next(i for i, r in enumerate(rs) if r.obstacle) for rs in (off, on)]
    assert first[1] == first[0]
    for d, r in zip(dist[first[1]:], on[first[1]:]):
        assert r.obstacle and abs(r.nearest_distance - d) < 0.5, (d, r.nearest_distance)
    err_on = [abs(float(r.track.rail_z(20.0)) - RAIL_HEAD_Z) for r in on]
    assert all(e_on <= e_off + 0.01 for e_on, e_off in zip(err_on, err_off))
    found = next(i for i, r in enumerate(on) if r.track.floor_shadow > 0)
    assert max(err_on[found:]) < 0.1 and max(err_on) < 0.2
    assert on[-1].track.floor_held


def test_rail_shadow_person_in_front_of_the_box_stops(tunnel):
    """Safety: with the rules on, a person (0.4 x 0.5 x 1.7 m) standing on the axis 6 m in front
    of the approaching box is a STOP at the person's distance in every frame from the frame the
    rules off confirm it; so is the person next to a long line at the corridor edge, which the
    rules off drop with the line (one cluster longer than max_extent)."""
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
    frame, _, _ = tunnel
    seq = []
    for k, d in enumerate(np.arange(36.0, 11.0, -2.0)):
        f, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(200 + k), specs=[
            ObstacleSpec(kind="box", size=(0.5, 2.0, 2.0), distance=float(d), base=0.1),
            ObstacleSpec(kind="person", size=(0.4, 0.5, 1.7), distance=float(d) - 6.0, lateral=0.3)])
        seq.append((float(d) - 6.0, f))
    off = _drive(frame, seq, _rail_shadow_cfg(False))
    on = _drive(frame, seq, _rail_shadow_cfg(True))
    first = next(i for i, r in enumerate(off) if r.obstacle)
    assert next(i for i, r in enumerate(on) if r.obstacle) <= first
    for (d, _), r in zip(seq[first:], on[first:]):
        assert r.obstacle and abs(r.nearest_distance - d) < 0.5, (d, r.nearest_distance)
    # the person at the corridor edge next to a 12 m line (clear tunnel, no shadow)
    person = _box_surface(20.0, 0.4, 0.85, 0.0, 1.7, 0.5)
    line = _edge_line(8.0, 20.4)
    both = np.concatenate([person, line])
    assert not _run_with(frame, both, _rail_shadow_cfg(False)).obstacle
    res = _run_with(frame, both, _rail_shadow_cfg(True))
    assert res.obstacle and abs(res.nearest_distance - 20.0) < 0.5
    assert _run_with(frame, person, _rail_shadow_cfg(True)).obstacle


# --- review of 25.09: the safety fixes of the rail-shadow rules ----------------------------------

def _oblique_bar(x_entry: float, slope: float = 0.15, before: float = 2.0, after: float = 4.0,
                 side: float = 1.0) -> np.ndarray:
    """A 1.2 m tall bar (0.2-1.4 m above the rail head) lying obliquely across the corridor edge:
    it starts ``before`` m ahead of its entry in the advisory margin (|dy| 1.35 m) and crosses the
    1.05 m envelope edge at exactly ``x_entry``, ``slope`` m of |dy| per m of X (a fallen pole or
    plank), points every 2 cm along the track, in the tunnel frame of ``synthetic_tunnel_frame``."""
    X, Z = np.meshgrid(np.arange(x_entry - before, x_entry + after + 1e-9, 0.02), np.arange(0.0, 1.2 + 1e-9, 0.05),
                       indexing="ij")
    dy = 1.05 - slope * (X - x_entry)
    return np.stack([X.ravel(), AXIS_Y + side * dy.ravel(), RAIL_HEAD_Z + 0.2 + Z.ravel()], 1).astype(np.float32)


@pytest.mark.parametrize("x_entry", [40.0, 80.0, 120.0])
def test_gauge_distance_is_never_beyond_the_envelope_entry(tunnel, x_entry):
    """Review of 25.09 (safety): cluster.gauge_distance took the nearest point of the strict-gauge
    mask, which is the envelope SHRUNK by the axis-uncertainty edge margin (0.15 m per 100 m): an
    object entering the envelope obliquely was reported 0.4 / 0.8 / 1.2 m beyond its entry at
    40 / 80 / 120 m (a too-long distance). The distance is now measured on the envelope widened
    by that margin: never beyond the entry (+ 5 cm, the point spacing), never before the bar."""
    frame, _, _ = tunnel
    for side in (1.0, -1.0):
        res = _run_with(frame, _oblique_bar(x_entry, side=side), DetectorConfig())
        assert res.obstacle, (x_entry, side)
        assert x_entry - 2.05 <= res.nearest_distance <= x_entry + 0.05, (x_entry, side, res.nearest_distance)


def _pitched(tunnel_frame: Frame, grade: float) -> Frame:
    """The frame seen by a sensor pitched down by ``atan(grade)``: the bed ahead rises by ``grade``."""
    a = np.arctan(grade)
    rot = np.array([[np.cos(a), 0.0, -np.sin(a)], [0.0, 1.0, 0.0], [np.sin(a), 0.0, np.cos(a)]])
    return Frame(xyz=(tunnel_frame.xyz.astype(np.float64) @ rot.T).astype(np.float32), intensity=tunnel_frame.intensity)


def _pitch_step(tunnel_frame: Frame, cfg: DetectorConfig, grade: float = 0.06, n: int = 45):
    """10 frames of the clear tunnel, then ``n`` frames after a relative pitch step (grade 0 -> ``grade``)."""
    det = Detector(cfg)
    step = _pitched(tunnel_frame, grade)
    for k in range(10):
        det.process(Frame(xyz=tunnel_frame.xyz, intensity=tunnel_frame.intensity, stamp=0.1 * k))
    return [det.process(Frame(xyz=step.xyz, intensity=step.intensity, stamp=0.1 * (k + 10))) for k in range(n)]


def test_floor_shadow_hold_is_released_after_the_cap(tunnel):
    """Review of 25.09: a held bed is the next frame's reference, so a relative pitch step of 3.4 deg
    (grade 0 -> 6 %) after the warm-up looked like a shadow at 17 m and held the flat bed for good
    (the lasting false STOP at ~4.4 m of the rising bed). With track.floor_shadow_max_hold (20
    frames) the hold ends after 20 frames, the bed follows the pitch and the STOP clears for good;
    the status counts the frames (health floor_shadow_frames / floor_held_frames /
    floor_released_frames). Without the cap the lock is still there."""
    frame, _, _ = tunnel
    cap = 20                                                          # the shipped floor_shadow_max_hold
    res = _pitch_step(frame, DetectorConfig())
    held = [r.track.floor_held for r in res]
    assert held[:cap] == [True] * cap and not any(held[cap:])
    assert not any(r.obstacle for r in res[cap + 3:])
    assert abs(float(res[-1].track.floor_z(20.0)) - (0.06 * 20.0 - 1.5 / np.cos(np.arctan(0.06)))) < 0.15
    h = res[-1].health
    assert h["floor_held_frames"] == cap and h["floor_released_frames"] >= 1
    assert h["floor_shadow_frames"] == h["floor_held_frames"] + h["floor_released_frames"]
    assert res[cap - 1].to_dict()["track"]["floor_hold_run"] == cap
    cfg = DetectorConfig()
    cfg.track = replace(cfg.track, floor_shadow_max_hold=0)
    locked = _pitch_step(frame, cfg)
    assert all(r.track.floor_held for r in locked) and locked[-1].obstacle


def _band_points(bins: dict) -> np.ndarray:
    """40 bed-band points per floor-profile bin centre (``{centre X: height above the bed}``), the
    bed at -1.5 m on a straight axis at y = 0."""
    rng = np.random.default_rng(7)
    parts = [np.stack([rng.uniform(x - 0.4, x + 0.4, 40), rng.uniform(-0.8, 0.8, 40), np.full(40, -1.5 + dz)], 1)
             for x, dz in bins.items()]
    return np.concatenate(parts).astype(np.float32)


def test_floor_shadow_needs_adjacent_bins_and_takes_the_face_nearest_the_shadow():
    """Review of 25.09, unit (track._fit_floor): (1) two bins high above the bed with empty bins
    between them (28 m and 62.5 m) are no shadow; two adjacent ones are (28 and 30 m: start 27 m).
    (2) the object's face is the first bin of the off-bed run nearest the shadow, not a nearer
    off-bed bin (a switch part or a low object at 8 m, which cut the rail search to 4-7 m and held
    the rail model): the face bin at 16 m -> 15 m; a face over two bins (14 and 16 m) -> 13 m."""
    from resense.config import TrackConfig
    from resense.track import TrackModel, _fit_floor
    cfg = TrackConfig()
    prev = TrackModel(floor_coef=np.array([0.0, 0.0, -1.5]), floor_range=(3.0, 120.0), center=0.0, yaw=0.0,
                      curvature=0.0, age=10)

    def shadow_info(bins):
        info = {}
        assert _fit_floor(_band_points(bins), cfg, prev, shadow_ref=prev, info=info) is not None
        return info

    bed = {float(x): 0.0 for x in range(4, 28, 2)}
    gap = shadow_info({**bed, 28.0: 2.5, 62.5: 2.5, **{x: 0.0 for x in (67.5, 72.5, 77.5, 82.5)}})
    assert gap["shadow"] == 0.0
    assert shadow_info({**bed, 28.0: 2.5, 30.0: 2.5})["shadow"] == 27.0
    box = {**{float(x): 0.0 for x in range(4, 16, 2)}, 8.0: 0.6, 16.0: 0.6, **{float(x): 3.0 for x in range(18, 32, 2)}}
    one = shadow_info(box)
    assert (one["shadow"], one["face"], one["hold"]) == (17.0, 15.0, False)
    two = shadow_info({**box, 14.0: 0.6})
    assert (two["shadow"], two["face"]) == (17.0, 13.0)


# ---------------------------------------------------------------------------
# track.walls_min_far_support (P3, 25.09): the 82.9 m platform end
# ---------------------------------------------------------------------------

FAR_SUPPORT = 0.5          # the preferred candidate of docs/evidence/results/p3_platform_end_2026-09-25.json


def _station_scene(curvature: float = 0.0, platform: bool = True, seed: int = 25) -> np.ndarray:
    """A track (straight or curved) with its bed, the near rails (4-30 m) and a right wall at
    -2.2 m; on the left, like ``squareT_platform_squareT_switch`` while the train stands at the
    platform (EXPERIMENTS 1h): a platform-side structure at +1.6 m (6-33 m), one pillar bin at
    44 m, the hall end diverging from +2.4 to +4.3 m at 74-88 m and the running tunnel's wall at
    +2.05 m at 92-110 m; ``platform=False``: a plain left wall at +2.2 m. Walls 0.4-1.5 m above
    the vehicle frame's origin (1.6-2.7 m above the rail head), bed at -1.5 m, rail head -1.16 m."""
    rng = np.random.default_rng(seed)

    def bend(x):
        return 0.5 * curvature * x * x

    def wall(x0, x1, y, n):
        x = rng.uniform(x0, x1, n)
        return np.stack([x, y(x) + bend(x) + rng.normal(0, 0.02, n), rng.uniform(0.4, 1.5, n)], 1)

    x = rng.uniform(3, 110, 26000)
    parts = [np.stack([x, rng.uniform(-1.1, 1.1, x.size) + bend(x), -1.5 + rng.normal(0, 0.01, x.size)], 1)]
    for side in (-1, 1):
        x = rng.uniform(4, 30, 15000)
        parts.append(np.stack([x, side * 0.795 + bend(x) + rng.normal(0, 0.015, x.size),
                               -1.16 + rng.normal(0, 0.005, x.size)], 1))
    parts.append(wall(6, 150, lambda x: -2.2 + 0 * x, 22000))
    if platform:
        parts += [wall(6, 33, lambda x: 1.6 + 0 * x, 8000), wall(42, 46, lambda x: 2.2 + 0 * x, 400),
                  wall(74, 88, lambda x: 2.4 + (x - 74) * (4.3 - 2.4) / 14, 1500),
                  wall(92, 110, lambda x: 2.05 + 0 * x, 1000)]
    else:
        parts.append(wall(6, 150, lambda x: 2.2 + 0 * x, 22000))
    return np.concatenate(parts).astype(np.float32)


def _far_support_cfg(value: float = FAR_SUPPORT, frames: int = 1) -> DetectorConfig:
    cfg = DetectorConfig()
    cfg.track = replace(cfg.track, walls_min_far_support=value, walls_far_support_frames=frames)
    return cfg


def _settled_track(cloud: np.ndarray, cfg: DetectorConfig, n: int = 30):
    from resense.track import estimate_track
    model = None
    for _ in range(n):
        model = estimate_track(cloud, cfg.track, prev=model)
    return model


def test_far_support_rule_default():
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        assert cfg.track.walls_min_far_support == 0.0           # tried 25.09, not shipped (EXPERIMENTS 1h)
        assert cfg.track.walls_far_support_max_curvature == 2.0e-4
        assert cfg.track.walls_far_support_frames == 1


def test_far_support_keeps_the_station_axis_on_the_supported_side():
    """The platform-side boundary (near structure + one hall-end bin) bends the default axis by
    metres at 83 m; with the rule the right wall, whose far bins follow its fit, sets the shape
    and the axis stays within 0.15 m of the track; with ``walls_far_support_frames`` N the
    first N - 1 frames are the default's. A real curve (R 1 000 / 350 m, both walls parallel)
    and a station on a curve (the supported side bends: never overruled) are identical with
    and without the rule."""
    station = _station_scene()
    off = _settled_track(station, DetectorConfig())
    on = _settled_track(station, _far_support_cfg())
    assert abs(float(off.center_y(83.0))) > 0.5, off.to_dict()
    assert abs(float(on.center_y(83.0))) < 0.15, on.to_dict()
    assert abs(on.curvature) < 1e-4 and on.axis_sides == 2
    # walls_far_support_frames N: the rule sets the shape from the N-th consecutive frame only
    from resense.track import estimate_axis_from_walls
    held = _far_support_cfg(frames=10).track
    tan = float(np.tan(on.yaw))
    first = estimate_axis_from_walls(station, on, _far_support_cfg().track, tan)
    average = estimate_axis_from_walls(station, on, DetectorConfig().track, tan)
    assert first[-1] == 1 and average[-1] == 0 and first[1] != average[1]      # the supported side vs the average
    assert estimate_axis_from_walls(station, on, held, tan, far_support_run=0)[:6] == average[:6]
    tenth = estimate_axis_from_walls(station, on, held, tan, far_support_run=9)
    assert tenth[-1] == 10 and tenth[:6] == first[:6]
    for curvature, platform in ((1 / 1000, False), (1 / 350, False), (-1 / 1000, False), (1 / 1000, True)):
        scene = _station_scene(curvature, platform)
        a = _settled_track(scene, DetectorConfig()).to_dict()
        b = _settled_track(scene, _far_support_cfg()).to_dict()
        assert a == b, (curvature, platform)
        if not platform:
            assert abs(a["curvature"] - curvature) < 0.1 * abs(curvature), a


def test_far_support_station_obstacle_still_stops():
    """End to end in the station scene with the rule: a person 0.5 x 0.4 x 1.7 m on the axis or
    0.6 m off it, at 83, 60 or 25 m, is a STOP; the platform-end structure (2.2 x 0.4 x 1.25 m at
    +1.9 m, bottom at the bed, as in squareT_platform_squareT_switch) is not. Without the rule
    the bent axis reads the person 0.6 m right of the track at 60 m at -1.3 m: advisory only."""
    station = _station_scene()
    bed = -1.5

    def last(extra, cfg, n=10):
        pts = np.concatenate([station, extra]).astype(np.float32)
        det = Detector(cfg)
        res = None
        for k in range(n):
            res = det.process(Frame(xyz=pts, intensity=np.full(len(pts), 30.0, np.float32), stamp=0.1 * k))
        return res

    def box(x0, y0, length, width, height, z0=bed):
        """``_box_surface`` placed in this scene: front at x0, centred at y0, bottom at z0."""
        return _box_surface(x0, length, y0 - AXIS_Y, z0 - RAIL_HEAD_Z, height, width)

    on = _far_support_cfg()
    end = box(82.9, 1.9, 2.2, 0.4, 1.25)
    res = last(end, on)
    assert not res.obstacle, [(c.distance, c.lateral, c.zone, c.reason) for c in res.candidates]
    off = _far_support_cfg(0.0)
    res = last(np.concatenate([end, box(60.0, -0.6, 0.4, 0.5, 1.7)]), off)
    assert not res.obstacle and res.warning
    for dist in (83.0, 60.0, 25.0):
        for lateral in (0.0, -0.6, 0.6):
            res = last(np.concatenate([end, box(dist, lateral, 0.4, 0.5, 1.7)]), on)
            assert res.obstacle and abs(res.nearest_distance - dist) < 1.0, (
                dist, lateral, res.track.to_dict(), [(c.distance, c.lateral, c.zone, c.reason) for c in res.candidates])


# --- cluster.far_axis_both_sides (25.09, far_switch; 0 = off) ---------------------------------

def _far_scene(tunnel_frame: Frame, hall: bool) -> Frame:
    """The ray-cast tunnel with the bed cut beyond 70 m and the low side structure beyond 100 m,
    so that the height reference ends at ~110 m as on the ride (fit end + 20 m, side-base
    verification); with ``hall`` the left lining is replaced by a boundary bent at 4e-4 /m and
    seen only to 76 m: the platform-hall wall whose curvature carried the corridor onto the
    147.5 m switch parts of ``squareT_platform_squareT_switch`` (EXPERIMENTS §1h)."""
    xyz = tunnel_frame.xyz
    X, dy, h = xyz[:, 0], xyz[:, 1] - AXIS_Y, xyz[:, 2] - RAIL_HEAD_Z
    drop = ((X > 70.0) & (np.abs(dy) < 1.6) & (h < 0.3)) | ((X > 100.0) & (np.abs(dy) >= 1.6) & (h < 1.5))
    if hall:
        drop |= (dy > 1.2) & (X > 4.0)
    pts = [xyz[~drop]]
    if hall:
        xs = np.arange(6.0, 76.0, 0.25)
        for z in np.arange(1.7, 2.75, 0.1):
            pts.append(np.stack([xs, AXIS_Y + 2.0 + 0.5 * 4e-4 * xs * xs, np.full(xs.size, RAIL_HEAD_Z + z)], 1))
    p = np.concatenate(pts).astype(np.float32)
    return Frame(xyz=p, intensity=np.full(len(p), 12.0, np.float32))


def _both_sides(mode: int) -> DetectorConfig:
    cfg = DetectorConfig()
    cfg.cluster = replace(cfg.cluster, far_axis_both_sides=mode)
    return cfg


def _height_ref(track, cfg: DetectorConfig) -> float:
    return max(track.floor_range[1] + cfg.track.floor_valid_margin, track.floor_verified)


def test_far_axis_both_sides_is_off_by_default():
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        assert cfg.cluster.far_axis_both_sides == 0


def test_far_axis_both_sides_range_of_the_track_model(tunnel):
    """Both tunnel boundaries fitted: on the bent hall axis both ranges are the shorter side's last
    bin + 15 m (no straight bonus: the short bent side sets the curvature), ``axis_valid`` is the
    longer side's; in the straight tunnel mode 1's range is within a few metres of ``axis_valid``
    and mode 2 sets no limit."""
    frame, _, _ = tunnel
    cfg = DetectorConfig()
    t = Detector(cfg).process(_far_scene(frame, hall=True)).track
    assert t.axis_sides == 2 and abs(t.curvature) > 1e-4
    short = 76.0 + cfg.track.axis_valid_margin
    assert short - 5.0 <= t.axis_valid_both <= short and t.axis_valid_bent == t.axis_valid_both
    assert t.axis_valid > 120.0 and _height_ref(t, cfg) < 120.0
    assert "axis_valid_both" not in t.to_dict() and "axis_valid_bent" not in t.to_dict()   # output unchanged
    t = Detector(cfg).process(_far_scene(frame, hall=False)).track
    assert t.axis_sides == 2 and t.axis_valid_both >= 170.0 and t.axis_valid - t.axis_valid_both <= 10.0
    assert t.axis_valid_bent == 1e9


def test_far_axis_both_sides_hall_curvature_no_longer_carries_a_far_stop(tunnel):
    """A 0.5 x 1.7 m face on the corridor the bent hall wall extrapolates to 125 m (beyond the height
    reference, inside axis_valid): a STOP through the far-field rule with the flag off; in either
    mode advisory ``beyond_axis``, and the verified-clear range ends at the height reference."""
    frame, _, _ = tunnel
    scene = _far_scene(frame, hall=True)
    t = Detector(DetectorConfig()).process(scene).track
    lat = float(t.center_y(np.array([125.0]))[0]) - AXIS_Y            # ~1 m left of the real track axis
    pts = _box_surface(125.0, 0.3, lat, 0.3, 1.7, 0.5)
    off = _run_with(scene, pts, DetectorConfig(), n=5)            # the 5th frame confirms it
    assert off.obstacle and off.detections[0].reason == "" and abs(off.detections[0].distance - 125.0) < 1.0
    for mode in (1, 2):
        on = _run_with(scene, pts, _both_sides(mode), n=5)
        assert not on.obstacle and on.warning and on.warnings[0].reason == "beyond_axis", mode
        assert on.health["monitored_range"] < off.health["monitored_range"]
        assert on.health["monitored_range"] >= _height_ref(on.track, DetectorConfig()) - 1e-6


def test_far_axis_both_sides_mode_2_keeps_other_reasons(tunnel):
    """Mode 2 demotes only would-be obstacles: a 2.6 m column-shaped cluster at 125 m on the bent
    hall corridor stays advisory ``column`` (a column hit for tracking.column_hold); mode 1 turned
    it into ``beyond_axis``, which hid a column from the hold on roundT_doubleT (EXPERIMENTS §1h)."""
    frame, _, _ = tunnel
    scene = _far_scene(frame, hall=True)
    t = Detector(DetectorConfig()).process(scene).track
    lat = float(t.center_y(np.array([125.0]))[0]) - AXIS_Y
    column = _box_surface(125.0, 0.3, lat + 0.8, 0.0, 2.6, 0.3)
    reasons = {}
    for mode in (0, 1, 2):
        res = _run_with(scene, column, _both_sides(mode))
        assert not res.obstacle
        reasons[mode] = [c.reason for c in res.candidates if abs(c.distance - 125.0) < 1.0]
    assert reasons[0] == ["column"] and reasons[2] == ["column"] and reasons[1] == ["beyond_axis"], reasons


def test_far_axis_both_sides_keeps_a_near_stop_and_the_straight_far_field(tunnel):
    """Safety, in either mode: a person-size box at 50 m in the same hall scene is a STOP on the
    same frame as with the flag off; in the straight tunnel (both boundaries to the end) a person
    at 140 m, beyond the height reference, is still a STOP through the far-field rule."""
    frame, _, _ = tunnel
    hall = _far_scene(frame, hall=True)
    t = Detector(DetectorConfig()).process(hall).track
    near = _box_surface(50.0, 0.3, float(t.center_y(np.array([50.0]))[0]) - AXIS_Y, 0.0, 1.7, 0.5)
    k_off = _first_stop(hall, [near] * 8, DetectorConfig())
    straight = _far_scene(frame, hall=False)
    far = _box_surface(140.0, 0.3, 0.0, 0.4, 1.7, 0.5)
    assert k_off is not None
    for mode in (0, 1, 2):
        cfg = _both_sides(mode)
        assert _first_stop(hall, [near] * 8, cfg) == k_off, mode
        res = _run_with(straight, far, cfg)
        assert _height_ref(res.track, cfg) < 139.0
        assert res.obstacle and abs(res.detections[0].distance - 140.0) < 1.0 and res.detections[0].reason == ""


# --- track.floor_far_min_width (P3 bed_bin, 25.09): a far bed bin that is the foot of an object -------
FAR_RULE = dict(floor_far_min_width=1.1, floor_far_from=90.0, floor_far_min_standing=2)


def test_bed_bin_rule_is_off_by_default():
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        assert cfg.track.floor_far_min_width == 0.0


def _far_bed_cloud(obj: bool = True, rail: bool = True) -> np.ndarray:
    """Bed at z = -1.9 across |dy| <= 0.9 from 3 to 90 m and a vault at z = +2.6 to 120 m; beyond
    90 m the bed does not return: one rail head (dy = 0.75, 0.3 m above the bed) at 100-104.5 m
    and the front face of a 1.0 x 1.0 m box standing on the bed at 105 m."""
    X, Y = np.meshgrid(np.arange(3.0, 90.0, 0.25), np.linspace(-0.9, 0.9, 7), indexing="ij")
    parts = [np.stack([X.ravel(), Y.ravel(), np.full(X.size, -1.9)], 1)]
    xv = np.arange(3.0, 120.0, 0.5)
    parts.append(np.stack([np.repeat(xv, 3), np.tile([-0.5, 0.0, 0.5], xv.size), np.full(3 * xv.size, 2.6)], 1))
    if rail:
        xr = np.linspace(100.0, 104.5, 20)
        parts.append(np.stack([xr, np.full(xr.size, 0.75), np.full(xr.size, -1.6)], 1))
    if obj:
        Yf, Zf = np.meshgrid(np.linspace(-0.2, 0.8, 6), np.linspace(-1.9, -0.9, 11), indexing="ij")
        parts.append(np.stack([np.full(Yf.size, 105.0), Yf.ravel(), Zf.ravel()], 1))
    return np.concatenate(parts).astype(np.float32)


def test_bed_bin_rule_drops_an_object_foot_not_a_rail_head():
    """The box's bin (1.0 m wide low points with its face standing on them) no longer extends the
    bed fit; the narrow rail-head bin with nothing on it is kept (dropped only by the plain width
    rule, floor_far_min_standing 0); the fit ends where the bed ends without the box. Both paths."""
    from resense import _native
    from resense.config import TrackConfig
    from resense.track import _fit_floor, default_track_model
    base = replace(TrackConfig(), lateral_center=0.0)
    prior = default_track_model(base)
    was = _native.enabled()
    try:
        for native in (True, False):
            _native.set_enabled(native)
            for obj, off_end, on_end, width_only_end in ((True, 107.5, 102.5, 87.5), (False, 102.5, 102.5, 87.5)):
                xyz = _far_bed_cloud(obj=obj)
                assert _fit_floor(xyz, base, prior)[1][1] == off_end
                assert _fit_floor(xyz, replace(base, **FAR_RULE), prior)[1][1] == on_end
                width_only = replace(base, **dict(FAR_RULE, floor_far_min_standing=0))
                assert _fit_floor(xyz, width_only, prior)[1][1] == width_only_end
            # beyond floor_far_from only: the same box at 105 m with the check from 110 m extends the fit
            later = replace(base, **dict(FAR_RULE, floor_far_from=110.0))
            assert _fit_floor(_far_bed_cloud(), later, prior)[1][1] == 107.5
    finally:
        _native.set_enabled(was)


def _trim_far_bed(frame: Frame, beyond: float = 90.0) -> Frame:
    """The ray-cast tunnel with the bed and rail returns beyond ``beyond`` removed near the axis,
    as the real bed stops returning beyond ~90 m (EXPERIMENTS §2d)."""
    x, y, z = frame.xyz[:, 0], frame.xyz[:, 1], frame.xyz[:, 2]
    keep = ~((x > beyond) & (np.abs(y - AXIS_Y) < 1.2) & (z < RAIL_HEAD_Z + 0.3))
    return Frame(xyz=frame.xyz[keep], intensity=frame.intensity[keep])


def test_bed_bin_rule_keeps_the_stop(tunnel):
    """Safety, end to end on the ray-cast tunnel with the rule on: a person-size box (0.3 x 0.5 x
    1.8 m) standing on the bed on the axis at 60 m (bed visible) and at 105 m (bed trimmed beyond
    90 m, the box's foot alone fills the bin) is a STOP on the same frame as with the rule off; at
    105 m the box's foot extends the bed fit from 82.5 to 107.5 m with the rule off and not with
    it on."""
    frame, _, _ = tunnel
    far = _trim_far_bed(frame)
    off, on = DetectorConfig(), DetectorConfig()
    on.track = replace(on.track, **FAR_RULE)
    confirm = on.tracking.frames_to_confirm() - 1
    for bg, dist in ((frame, 60.0), (far, 105.0)):
        person = _box_surface(dist, 0.3, 0.0, -0.18, 1.8, 0.5)               # standing on the bed
        k_off, k_on = _first_stop(bg, [person] * 8, off), _first_stop(bg, [person] * 8, on)
        assert k_on is not None and k_on == k_off <= confirm + 1, (dist, k_off, k_on)
        res = _run_with(bg, person, on)
        assert res.obstacle and abs(res.detections[0].distance - dist) < 0.5
        if dist > 90.0:
            assert res.track.floor_range[1] < dist < _run_with(bg, person, off).track.floor_range[1]
