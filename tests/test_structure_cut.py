"""The structure cut of an oversize cluster (13.10, ``cluster.structure_cut_tol``; judge 13.10 problem 2).

On a curve the lagging far axis lays the tunnel wall diagonally across the envelope (roundT_pressureGate_roundT,
70-150 m). An object standing in front of the wall there touches it within the DBSCAN radius (no thin
bridge, no gap in x or height), the two form one cluster longer than ``max_extent`` and the oversize
split refuses it (its strict-gauge part is 23-40 m long and starts beyond 30 m): the whole cluster was
dropped, decision GO. The cut fits the smooth surface the cluster lies on (``y = a + b x + c x^2 + d h + e h^2``,
robust) and describes on their own the compact parts standing at least ``structure_cut_tol`` in front of
it as seen from the sensor.

The judge's required changes of 13.10 (14.10): a part needs ``structure_cut_min_points`` (8) voxels (every
false part on the empty recordings had 3-7); the cut runs only for a cluster the 25.09 split refused (a
part the split accepted and the rules then dropped gets no second chance); a cluster without a
strict-gauge point is not fitted; a degenerate fit (too few points, non-finite input) or a surface steeper
than 45 deg to the track cuts nothing.

The review of 14.10: at 0.8 m an object standing 0.95-1.2 m in front of the outer wall of C - outside the
envelope, in its advisory band, where the detector's trusted near axis puts it - was carved out and placed in the
envelope by the lagging axis (false STOPs at 70-100 m). The tolerance is 1.3 m: more than the wall equipment
(0.8-1.2 m) and more than C's wall stands outside the strict envelope (2.25-2.3 m from the axis, 1.05 m half
width).
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np

from resense import clustering
from resense.clustering import _surface_fit, find_clusters
from resense.config import ClusterConfig, DetectorConfig

ROOT = Path(__file__).resolve().parents[1]


def _wall(y100: float = 1.0, slope: float = -0.09, x0: float = 80.0, x1: float = 125.0, noise: float = 0.0):
    """A round-profile tunnel wall crossing the envelope diagonally (lateral y100 at 100 m, slope
    d(dy)/dx, the profile leaning in with height as on roundT C), sampled every 0.25 m x 0.2 m."""
    X, H = np.meshgrid(np.arange(x0, x1, 0.25), np.arange(0.1, 2.95, 0.2), indexing="ij")
    Y = y100 + slope * (X - 100.0) + 0.4 * H - 0.15 * H * H
    if noise > 0:
        Y = Y + np.random.default_rng(3).normal(0.0, noise, Y.shape)
    return np.stack([X.ravel(), Y.ravel(), H.ravel()], 1)


def _face(x: float, y0: float, width: float = 0.5, height: float = 1.75):
    """The front face of a box standing on the rail-head plane (the judge's person-size box: 0.5 x 1.75 m)."""
    Y, H = np.meshgrid(np.arange(y0, y0 + width + 1e-6, 0.1), np.arange(0.1, height + 1e-6, 0.15), indexing="ij")
    return np.stack([np.full(Y.size, x), Y.ravel(), H.ravel()], 1)


def _clusters(pts: np.ndarray, cfg: ClusterConfig):
    """Clustering only, on a straight axis at y = 0 with the rail head at z = 0 (dy = y, h = z); the strict
    gauge is the 1.05 m half-width envelope up to 3 m."""
    pts = pts.astype(np.float32)
    dy, h = pts[:, 1].astype(np.float64), pts[:, 2].astype(np.float64)
    strict = (np.abs(dy) < 1.05) & (h > 0.0) & (h < 3.0)
    return find_clusters(pts, np.full(len(pts), 10.0, np.float32), dy, h, strict, cfg)


def test_structure_cut_shipped():
    """On in the shipped configuration, identical in the three sources: 1.3 m (14.10; 0.8 m on 13.10) in front of
    a surface with a robust spread of at most 0.12 m holding at least 80 % of the cluster, parts of at least 8
    voxels."""
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        c = cfg.cluster
        assert (c.structure_cut_tol, c.structure_cut_max_spread, c.structure_cut_min_fit,
                c.structure_cut_min_points) == (1.3, 0.12, 0.8, 8)


def _wall_y(x: float, h: float, y100: float = 1.0, slope: float = -0.09) -> float:
    """The lateral of :func:`_wall` at ``x``, ``h``."""
    return y100 + slope * (x - 100.0) + 0.4 * h - 0.15 * h * h


def test_object_in_front_of_wall_is_cut_out():
    """A person-size box face 0.6 m wide standing 1.0-1.6 m in front of the diagonal wall at 95 m and at 100 m
    (where the wall itself crosses into the strict envelope): one cluster with the wall (dropped whole) without
    the cut; with it the part of the face at least 1.3 m in front, a gauge obstacle."""
    on = ClusterConfig()
    off = replace(on, structure_cut_tol=0.0)
    scene = np.concatenate([_wall(), _face(95.0, _wall_y(95.0, 0.5) - 1.6, width=0.6)])
    assert _clusters(scene, off) == []
    (c,) = _clusters(scene, on)
    assert c.cut and c.zone == "gauge" and not c.reason and abs(c.distance - 95.0) < 0.05
    assert c.size[0] < 0.05 and 1.5 < c.size[2] < 1.8 and c.n_gauge >= on.gauge_min_points
    # the cut is independent of the surface's side of the axis and of the direction it crosses
    (c,) = _clusters(scene * np.array([1.0, -1.0, 1.0]), on)
    assert c.cut and c.zone == "gauge" and abs(c.distance - 95.0) < 0.05
    at100 = np.concatenate([_wall(), _face(100.0, _wall_y(100.0, 0.5) - 1.6, width=0.6)])
    assert _clusters(at100, off) == []
    (c,) = _clusters(at100, on)
    assert c.cut and c.zone == "gauge" and not c.reason and abs(c.distance - 100.0) < 0.05


def test_object_in_the_advisory_band_of_the_wall_stays_dropped():
    """The review of 14.10 (roundT_pressureGate_roundT, wall-anchored ray-cast boxes): a 0.5 m deep box whose
    face nearest the track stands 1.0-1.2 m in front of the wall stands outside the envelope (C's wall is 2.25-2.3 m
    from the axis where the axis is trusted), yet where the far axis lags it lies inside it. At 0.8 m (13.10)
    the cut carved it out as a gauge obstacle (false STOPs at 70-100 m: a person-size box 0 -> 21 frames, a sign
    post 0 -> 7, a mast 0 -> 9); at the shipped 1.3 m it stays dropped with the wall; 1.5 m in front it is cut out."""
    on = ClusterConfig()
    for d in (1.0, 1.1, 1.2):
        scene = np.concatenate([_wall(), _face(95.0, _wall_y(95.0, 0.5) - d)])
        assert _clusters(scene, on) == [], d
        (c,) = _clusters(scene, replace(on, structure_cut_tol=0.8))
        assert c.cut and c.zone == "gauge" and not c.reason, d
    (c,) = _clusters(np.concatenate([_wall(), _face(95.0, _wall_y(95.0, 0.5) - 1.5)]), on)
    assert c.cut and c.zone == "gauge" and not c.reason


def test_structure_alone_and_what_stays_dropped():
    """What the cut must not take out of a long structure: the wall alone, equipment fixed to it (less than
    structure_cut_tol in front of it), a box behind it (a niche: not in front as seen from the sensor),
    and anything on a cluster that is not one smooth surface (the robust spread above
    structure_cut_max_spread)."""
    on = ClusterConfig()
    tol = on.structure_cut_tol
    assert _clusters(_wall(), on) == []
    # a 0.5 x 1.2 m cabinet on the wall at 100 m, protruding tol - 0.6 .. tol - 0.1 m from the fitted wall: 28
    # voxels, well above structure_cut_min_points, so the tolerance keeps it with the wall, not the part bar
    # (14.10, review: the 13.10 fixture had 4 voxels and passed at any tolerance)
    fixture = _face(100.0, _wall_y(100.0, 0.5) - (tol - 0.1), width=0.5, height=1.5)
    fixture = fixture[fixture[:, 2] >= 0.3]
    scene = np.concatenate([_wall(), fixture])
    assert _clusters(scene, on) == [] and _clusters(scene, replace(on, structure_cut_min_points=0)) == []
    (c,) = _clusters(scene, replace(on, structure_cut_tol=tol - 0.7))       # all of it in front: carved out
    assert c.cut and c.n >= 3 * on.structure_cut_min_points
    # behind the wall: the wall at -0.8 m at 100 m (it falls to the right with x, so the sensor sees its
    # -y side), a box 1.0-1.5 m on its +y side, in the strict gauge
    behind = np.concatenate([_wall(y100=-0.8), _face(100.0, 0.3)])
    assert _clusters(behind, on) == _clusters(behind, replace(on, structure_cut_tol=0.0)) == []
    # a thick, irregular structure: no surface, no cut
    rough = np.concatenate([_wall(noise=0.35), _face(100.0, -0.5)])
    assert _clusters(rough, on) == []


def _column(x: float, y: float, k: int):
    """``k`` returns one above the other (0.25 m apart from 0.3 m up: ``k`` voxels at 100 m), a few
    returns of a small object or of a fixture."""
    return np.stack([np.full(k, x), np.full(k, y), 0.3 + 0.25 * np.arange(k)], 1)


def test_small_part_in_front_of_wall_stays_dropped():
    """3-7 voxels 1.4 m in front of a wall along the track at 1.9 m, at 120 m (the DBSCAN radius links them to
    it there), in the strict gauge, beyond far_range (3 voxels pass the point-count bar there): without the
    part-size bar each is carved out as a gauge obstacle; with structure_cut_min_points 8 they stay dropped with
    the wall, and 8 voxels pass."""
    on = ClusterConfig()
    assert on.structure_cut_min_points == 8 and on.min_points_far <= 3
    nobar = replace(on, structure_cut_min_points=0)
    wall = _straight_wall(y=1.9, x0=105.0, x1=150.0)
    for k in range(3, 8):
        scene = np.concatenate([wall, _column(120.0, 0.5, k)])
        assert _clusters(scene, on) == [] and _clusters(scene, replace(on, structure_cut_tol=0.0)) == [], k
        (c,) = _clusters(scene, nobar)
        assert c.cut and c.n == k and c.zone == "gauge" and not c.reason and abs(c.distance - 120.0) < 0.05
    (c,) = _clusters(np.concatenate([wall, _column(120.0, 0.5, 8)]), on)
    assert c.cut and c.n == 8 and c.zone == "gauge" and not c.reason


def test_eight_voxels_on_one_azimuth_column_are_not_a_resolved_cut_body():
    """H2: voxel count alone cannot corroborate a single vertical scan line.

    Reflection, input order and duplicate echoes must not manufacture a second
    azimuth column. This is a cut-only guard; a resolved face must still pass.
    """
    cfg = ClusterConfig()
    wall = _straight_wall(y=1.9, x0=105.0, x1=150.0)
    line = _column(120.0, 0.5, 8)
    for echoes in (1, 2):
        scene = np.concatenate([wall, np.repeat(line, echoes, axis=0)])
        for sign in (-1, 1):
            reflected = scene * np.array([1.0, sign, 1.0])
            assert _clusters(reflected, cfg) == [], (echoes, sign)
            assert _clusters(reflected[::-1].copy(), cfg) == [], (echoes, sign, "reversed")


def test_resolved_cut_face_keeps_its_corridor_verdict_with_duplicate_echoes():
    """H2: a face with horizontal and vertical support retains its gauge verdict."""
    cfg = ClusterConfig()
    wall = _wall()
    face = _face(95.0, _wall_y(95.0, 0.5) - 1.6, width=0.6)
    for echoes in (1, 2):
        scene = np.concatenate([wall, np.repeat(face, echoes, axis=0)])
        for sign in (-1, 1):
            (c,) = _clusters(scene * np.array([1.0, sign, 1.0]), cfg)
            assert c.cut and c.zone == "gauge" and not c.reason
            assert abs(c.distance - 95.0) < 0.05


def _straight_wall(y: float = 2.6, x0: float = 10.0, x1: float = 40.0):
    """A vertical wall along the track at lateral ``y``, outside the strict gauge, sampled 0.25 x 0.2 m."""
    X, H = np.meshgrid(np.arange(x0, x1, 0.25), np.arange(0.1, 2.95, 0.2), indexing="ij")
    return np.stack([X.ravel(), np.full(X.size, y), H.ravel()], 1)


def test_cut_only_where_the_split_refused(monkeypatch):
    """A face 1.4 m wide at 20 m reaching from the wall at 2.6 m into the strict gauge (1.02-2.42 m): one
    oversize cluster with the wall. The 25.09 split accepts its strict-gauge part (4 voxels, starting
    within 30 m) and the point-count bar drops it: the split's verdict stands, the cut is not tried.
    Were the split to refuse the cluster, the cut would carve the face out as a gauge obstacle."""
    on = ClusterConfig()
    Y, H = np.meshgrid(np.arange(1.02, 2.43, 0.1), np.arange(0.3, 1.6, 0.4), indexing="ij")
    face = np.stack([np.full(Y.size, 20.0), Y.ravel(), H.ravel()], 1)
    scene = np.concatenate([_straight_wall(), face])
    calls = []
    cut = clustering._off_structure_parts
    monkeypatch.setattr(clustering, "_off_structure_parts", lambda *a: calls.append(1) or cut(*a))
    assert _clusters(scene, on) == [] and calls == []
    monkeypatch.setattr(clustering, "_split_part", lambda *a: None)
    (c,) = _clusters(scene, on)
    assert calls == [1] and c.zone == "gauge" and c.n_gauge == 4 and abs(c.distance - 20.0) < 0.05


def test_no_fit_without_strict_gauge_points(monkeypatch):
    """An oversize wall wholly outside the strict gauge is not fitted (no part could have a strict-gauge
    point; most oversize clusters of the ride are such walls); the diagonal wall that crosses the
    envelope is."""
    fits = []
    monkeypatch.setattr(clustering, "_surface_fit", lambda *a: fits.append(1) or _surface_fit(*a))
    on = ClusterConfig()
    assert _clusters(_straight_wall(), on) == [] and fits == []
    assert _clusters(_wall(), on) == [] and fits == [1]


def test_degenerate_surface_fits():
    """Too few points or a non-finite input: no fit (and no cut). A constant height (a strip along the
    track: rank-deficient columns) fits with finite coefficients; a face across the track is no function
    of (x, h): its spread is far above structure_cut_max_spread. A NaN height in a cluster cuts nothing
    and raises nothing."""
    rng = np.random.default_rng(0)
    u = rng.uniform(-2.0, 2.0, 200)
    h = np.full(200, 0.5)
    y = 1.0 + 0.1 * u
    assert _surface_fit(u[:19], h[:19], y[:19], 0.4) is None
    for bad in (u, h, y):
        b = bad.copy()
        b[3] = np.nan
        args = [b if a is bad else a for a in (u, h, y)]
        assert _surface_fit(*args, 0.4) is None
    coef, res, spread, on = _surface_fit(u, h, y, 0.4)
    assert np.isfinite(coef).all() and spread < 1e-6 and on.all()
    Y, H = np.meshgrid(np.arange(-2.0, 2.0, 0.1), np.arange(0.1, 3.0, 0.1), indexing="ij")
    flat = _surface_fit(rng.normal(0.0, 1e-3, Y.size), H.ravel(), Y.ravel(), 0.4)
    assert flat is not None and flat[2] > 10 * ClusterConfig().structure_cut_max_spread
    pts = np.concatenate([_wall(), _face(100.0, -0.5)]).astype(np.float32)
    dy, hh = pts[:, 1].astype(np.float64), pts[:, 2].astype(np.float64)
    hh[5] = np.nan
    strict = (np.abs(dy) < 1.05) & (hh > 0.0) & (hh < 3.0)
    assert find_clusters(pts, np.full(len(pts), 10.0, np.float32), dy, hh, strict, ClusterConfig()) == []


def test_no_cut_along_a_face_across_the_track(monkeypatch):
    """A plane face seen obliquely across the track (79 deg to it: y = 5 (x - 100), 10 m wide, through the
    envelope at 100 m) fits y(x, h) exactly, but its lateral residual overstates the distance in front of
    it five times: a 0.5 x 1.75 m face 0.25-0.35 m in front of it (lateral residual 1.25-1.75 m) would pass the
    1.3 m tolerance. A surface steeper than _SURFACE_MAX_SLOPE (45 deg) is not cut; without that bound the face
    would be carved out."""
    Y, H = np.meshgrid(np.arange(-5.0, 5.01, 0.1), np.arange(0.1, 2.95, 0.2), indexing="ij")
    oblique = np.stack([100.0 + Y.ravel() / 5.0, Y.ravel(), H.ravel()], 1)
    Yo, Ho = np.meshgrid(np.arange(-0.25, 0.26, 0.1), np.arange(0.1, 1.76, 0.15), indexing="ij")
    obj = np.stack([np.full(Yo.size, 99.7), Yo.ravel(), Ho.ravel()], 1)
    scene = np.concatenate([oblique, obj])
    on = ClusterConfig()
    assert clustering._SURFACE_MAX_SLOPE == 1.0
    assert _clusters(scene, on) == []
    monkeypatch.setattr(clustering, "_SURFACE_MAX_SLOPE", 1e9)
    (c,) = _clusters(scene, on)
    assert c.zone == "gauge" and abs(c.distance - 99.7) < 0.05


def _post(x: float, y0: float, width: float = 0.3, top: float = 2.6):
    """The front face of a post standing on the rail-head plane, ``width`` across the track."""
    Y, H = np.meshgrid(np.arange(y0, y0 + width + 1e-6, 0.1), np.arange(0.1, top + 1e-6, 0.15), indexing="ij")
    return np.stack([np.full(Y.size, x), Y.ravel(), H.ravel()], 1)


def test_a_cut_part_meets_the_column_rule_and_its_free_top_test(monkeypatch):
    """14.10 (review): a cut part goes through the same rules as any corridor cluster, the column signature's
    free-top test included (the frame's cloud is handed on to the parts). A 0.3 m post, 2.6 m tall, 0.8-1.1 m
    in front of a straight wall at 1.7 m at 60 m (one oversize cluster with it, the split refuses it beyond
    30 m): its part is asked whether its top is seen free - free, an obstacle; not free, a column."""
    cfg = replace(ClusterConfig(), structure_cut_tol=0.8)
    scene = np.concatenate([_straight_wall(y=1.7, x0=50.0, x1=72.0), _post(60.0, 0.6)]).astype(np.float32)
    dy, h = scene[:, 1].astype(np.float64), scene[:, 2].astype(np.float64)
    strict = (np.abs(dy) < 1.05) & (h > 0.0) & (h < 3.0)

    def run(answer, c=cfg):
        calls = []
        monkeypatch.setattr(clustering, "top_is_free", lambda *a, **k: calls.append(1) or answer)
        out = find_clusters(scene, np.full(len(scene), 10.0, np.float32), dy, h, strict, c, frame_xyz=scene)
        return out, calls

    (c,), calls = run(True)
    assert calls == [1] and c.cut and c.spared and (c.zone, c.reason) == ("gauge", "") and abs(c.distance - 60.0) < 0.05
    (c,), calls = run(False)
    assert calls == [1] and c.cut and not c.spared and (c.zone, c.reason) == ("warning", "column")
    assert run(True, replace(cfg, structure_cut_tol=0.0)) == ([], [])          # no cut: dropped with the wall


def test_a_demoted_cut_part_does_not_remove_a_low_object():
    """14.10 (review): a low cluster overlapping a corridor cluster is that object's lower part and is dropped
    (one detection) - but a part the structure cut carved out of an oversize cluster counts only when it is
    itself an obstacle, as a straddling or a wall-kept cluster (the sealed detector dropped the oversize
    cluster whole and removed nothing). A low box on the bed at 40 m under a demoted cut part stays."""
    from resense.clustering import Cluster
    from resense.detector import Candidates, Detector

    def corridor(cut: bool, reason: str):
        c = np.array([40.15, 0.3, 0.9])
        return Cluster(points_idx=np.arange(3), n=12, n_raw=24, centroid=c, bbox_min=c - [0.15, 0.2, 0.9],
                       bbox_max=c + [0.15, 0.2, 0.9], distance=40.0, lateral=0.3, height_min=0.0, height_max=1.8,
                       intensity=10.0, n_expected=12.0, score=1.0, zone="warning" if reason else "gauge",
                       n_gauge=12, reason=reason, cut=cut)

    c = np.array([40.15, 0.3, 0.1])
    low = Cluster(points_idx=np.arange(3), n=8, n_raw=12, centroid=c, bbox_min=c - [0.15, 0.15, 0.05],
                  bbox_max=c + [0.15, 0.15, 0.05], distance=40.0, lateral=0.3, height_min=0.05, height_max=0.15,
                  intensity=10.0, n_expected=8.0, score=1.0, zone="gauge", n_gauge=8, kind="low")
    det = Detector(DetectorConfig())
    empty = Candidates(xyz=np.zeros((0, 3), np.float32), dy=np.zeros(0), h=np.zeros(0),
                       in_gauge=np.zeros(0, bool), intensity=np.zeros(0, np.float32),
                       idx=np.zeros(0, np.int64), low=np.zeros(0, bool))
    for reason in ("beyond_axis", "floating", "column"):
        assert det._not_part_of_corridor_objects([low], [], [corridor(True, reason)], empty) == [low], reason
        assert det._not_part_of_corridor_objects([low], [], [corridor(False, reason)], empty) == [], reason
    assert det._not_part_of_corridor_objects([low], [], [corridor(True, "")], empty) == []
