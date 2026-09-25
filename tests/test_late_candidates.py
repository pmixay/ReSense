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
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from resense.clustering import _advisory_reason, _Blob
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
