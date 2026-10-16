"""13.10 (``cluster.column_free_max_top``): the column signature does not demote a column-shaped cluster
standing in the envelope whose top is seen free - the ring above its top passes over it - while a column
that continues up to the vault, a top occluded from above, a top at the envelope top and a structure at
the envelope edge stay columns (the judge's 0.3 x 0.3 x 2.8 m pole of 13.10: never a STOP 0.7 m off the
axis). Pure numpy: the sensor's own grid (sensor.RING_ELEVATION_DEG x 0.1 deg azimuth) is cast against
boxes, the bed, a vault at a constant height above the rails and a far wall, each return written twice
as in the recordings."""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from resense.clustering import Cluster, FrameRays, _ids_in_elevation_order, _local_vault, find_clusters, top_is_free
from resense.config import DetectorConfig
from resense.gauge import point_in_polygon, widened_profile
from resense.sensor import RING_ELEVATION_DEG
from resense.tracking import Tracker

H0 = 1.8          # sensor height above the rail head (m); the vehicle frame has the sensor at the origin


def _cast(boxes, vault=4.2, grade=0.0, wall=220.0, az=(-3.0, 3.0), max_range=210.0, pitch=0.0, side=None,
          elev=None, ids=None):
    """(xyz in the corrected vehicle frame, h above the rails, label: 0 = background, k = boxes[k - 1], channel id)
    of the rays of the window. The rails are at z = grade * x - H0; ``boxes``: (x0, x1, y0, y1, h0, h1) above them
    (the rail level at x0), a 7th element 'a' for a box that absorbs (the ray ends without a return: dark paint,
    glass); the vault at ``vault`` above the rails; a wall across the track at x = ``wall`` (beyond max_range);
    ``side``: side walls at y = +-side. ``pitch`` (deg, nose up): the sensor is mounted tilted, its rays are its
    rings rotated by it (the cloud as the mount calibration corrects it). ``elev`` / ``ids``: another sensor's ring
    elevations (deg) and the channel id of each (default the Pandar128's, 0 the highest)."""
    el = np.radians(RING_ELEVATION_DEG if elev is None else np.asarray(elev, dtype=np.float64))
    a = np.radians(np.arange(az[0], az[1] + 1e-9, 0.1))
    E, A = np.meshgrid(el, a, indexing="ij")
    rid = np.repeat(np.arange(el.size) if ids is None else np.asarray(ids), a.size)
    d = np.stack([np.cos(E) * np.cos(A), np.cos(E) * np.sin(A), np.sin(E)], axis=-1).reshape(-1, 3)
    p = np.radians(pitch)
    d = d @ np.array([[np.cos(p), 0.0, -np.sin(p)], [0.0, 1.0, 0.0], [np.sin(p), 0.0, np.cos(p)]]).T
    with np.errstate(divide="ignore", invalid="ignore"):
        rise = d[:, 2] - grade * d[:, 0]                        # the ray's climb over the rails per unit length
        t = np.minimum.reduce([np.where(d[:, 0] > 1e-9, wall / d[:, 0], np.inf),
                               np.where(rise > 1e-9, (vault - H0) / rise, np.inf),
                               np.where(rise < -1e-9, -H0 / rise, np.inf),
                               np.where(np.abs(d[:, 1]) > 1e-9, (side or np.inf) / np.abs(d[:, 1]), np.inf)])
        lab = np.zeros(len(d), dtype=int)
        dark = np.zeros(len(d), dtype=bool)
        for k, (x0, x1, y0, y1, h0, h1, *mode) in enumerate(boxes, start=1):
            rz = grade * x0 - H0
            lo, hi = np.array([x0, y0, rz + h0]), np.array([x1, y1, rz + h1])
            t0, t1 = lo / d, hi / d
            tn = np.nanmax(np.minimum(t0, t1), axis=1)
            tf = np.nanmin(np.maximum(t0, t1), axis=1)
            hit = (tn <= tf) & (tn > 0) & (tn < t)
            t = np.where(hit, tn, t)
            lab = np.where(hit, k, lab)
            dark = np.where(hit, mode == ["a"], dark)
    ok = (t < max_range) & ~dark
    xyz = (d[ok] * t[ok, None]).astype(np.float32)
    h = xyz[:, 2].astype(np.float64) + H0 - grade * xyz[:, 0]
    return np.repeat(xyz, 2, axis=0), np.repeat(h, 2), np.repeat(lab[ok], 2), np.repeat(rid[ok], 2).astype(np.uint16)


def _pole(x, lat, top=2.8, w=0.3, bottom=0.0, mode=""):
    return (x, x + w, lat - w / 2, lat + w / 2, bottom, top) + ((mode,) if mode else ())


def _free(boxes, ids=False, heights=False, window=0.0, tall_gap=0.0, **kw):
    """top_is_free for box 1's returns a corridor cluster can hold (up to the 3.0 m envelope top); ``ids``: with
    the frame's channel ids; ``heights``: with the frame's heights and laterals (the detector's; the axis at y = 0)
    and the given window / tall gap (15.10)."""
    xyz, h, lab, ring = _cast(boxes, **kw)
    idx = np.flatnonzero((lab == 1) & (h <= 3.0))
    assert idx.size >= 4
    if heights:
        rays = FrameRays(xyz, ring if ids else None, h, xyz[:, 1].astype(np.float64))
        return top_is_free(rays, idx, window=window, tall_gap=tall_gap)
    return top_is_free(xyz, idx, frame_ring=ring if ids else None)


def _clusters(boxes, cfg=None, with_frame=True, heights=False, **kw):
    """The corridor clusters of the cast; ``heights``: the frame's channel ids, heights and laterals handed over
    too, as the detector does (15.10)."""
    cfg = cfg or DetectorConfig()
    xyz, h, _, ring = _cast(boxes, **kw)
    dy = xyz[:, 1].astype(np.float64)
    idx = np.flatnonzero(point_in_polygon(dy, h, widened_profile(cfg.gauge, cfg.gauge.warning_margin)))
    ig = point_in_polygon(dy[idx], h[idx], cfg.gauge.profile)
    return find_clusters(xyz[idx], np.full(idx.size, 30.0, np.float32), dy[idx], h[idx], ig, cfg.cluster,
                         frame_idx=idx, frame_xyz=xyz if with_frame else None, frame_ring=ring if heights else None,
                         frame_h=h if heights else None, frame_dy=dy if heights else None)


def _the(cl, x):
    near = [c for c in cl if abs(c.distance - x) < 2.0]
    assert len(near) == 1, [(c.distance, c.reason) for c in cl]
    return near[0]


def test_ring_above_passes_over_a_free_top_and_meets_a_column():
    assert _free([_pole(60.0, 0.7)])                     # the ring above reaches the vault at ~130 m
    assert not _free([_pole(60.0, 0.7, top=4.2)])        # a column to the vault: the same range above
    # occluded from above: a beam across the track at 40 m takes the ring above the top (nearer, no evidence)
    assert not _free([_pole(60.0, 0.7), (40.0, 40.5, -1.0, 1.0, 2.5, 3.5)])
    xyz, h, lab, _ = _cast([_pole(60.0, 0.7)])
    assert not top_is_free(xyz, np.flatnonzero(lab == 1)[:1])                   # too few returns to tell


def test_far_top_the_rings_right_above_leave_the_range():
    """At 180 m the rings right above the top return nothing over the whole span, beside the object as over it
    (their rays meet the vault only beyond the sensor's range); the first ring that returns meets the vault in
    front of the object: still a free top - on a level track and on a 0.5 % down grade, where the top is below
    the sensor. A column there continues. 15.10: without channel ids the ring in between is one the frame shows
    beside the object (the tunnel's side walls return it 1.5 deg off the object's azimuth); in a frame with no
    side walls nothing shows it: no empty-ring evidence."""
    for grade in (0.0, -0.005):
        for ids, side in ((True, None), (False, 2.2)):
            assert _free([_pole(180.0, 0.7)], vault=3.6, grade=grade, ids=ids, side=side), grade
            assert not _free([_pole(180.0, 0.7, top=3.6)], vault=3.6, grade=grade, ids=ids, side=side), grade
        assert not _free([_pole(180.0, 0.7)], vault=3.6, grade=grade)


def test_channel_ids_find_the_ring_in_between_under_a_mount_tilt():
    """The ring in between is read from the frame's channel ids where it carries them: under a mount tilt the
    corrected frame moves the rings off the sensor's table, and with the table's ring nearest to the top put at
    the top (13.10 / 14.10 without ids) a pole occluded from above (a beam at 40 m takes the ring above its top)
    had an empty ring invented between them (0.11-0.17 deg nose down, 0.45-0.5 deg up at 60 m). 15.10: without
    ids the ring in between is one the frame itself shows beside the object - the tilted rings where they are -
    so the occluded pole stays a column without ids too. One id for every return (set O: all 0) is no ids."""
    beam = (40.0, 40.5, -1.0, 1.0, 2.5, 3.5)
    for x in (60.0, 90.0):
        for ids in (False, True):
            assert _free([_pole(x, 0.7)], ids=ids) and not _free([_pole(x, 0.7, top=4.2)], ids=ids)
    assert not _free([_pole(60.0, 0.7), beam], ids=True)
    for pitch in (-0.15, 0.47):
        for ids in (False, True):
            assert not _free([_pole(60.0, 0.7), beam], ids=ids, pitch=pitch), (pitch, ids)
            assert _free([_pole(60.0, 0.7)], ids=ids, pitch=pitch), (pitch, ids)
            assert not _free([_pole(60.0, 0.7, top=4.2)], ids=ids, pitch=pitch), (pitch, ids)
    for pitch in (0.1, 0.15):                                       # 90 m, nose up
        for ids in (False, True):
            assert not _free([_pole(90.0, 0.7), (60.0, 60.5, -1.0, 1.0, 2.5, 3.5)], ids=ids, pitch=pitch), pitch
    xyz, h, lab, ring = _cast([_pole(60.0, 0.7), beam], pitch=-0.15)
    idx = np.flatnonzero((lab == 1) & (h <= 3.0))
    assert top_is_free(xyz, idx, frame_ring=np.zeros_like(ring)) == top_is_free(xyz, idx)   # one id = no ids


def test_column_signature_spares_a_free_standing_pole_only():
    cfg = DetectorConfig()
    assert (cfg.cluster.column_free_max_top, cfg.cluster.column_free_min_core,
            cfg.cluster.column_free_min_returns) == (2.95, 0.5, 2)          # shipped 13.10
    pole = [_pole(60.0, 0.7)]
    c = _the(_clusters(pole), 60.0)
    assert c.size[2] > cfg.cluster.column_min_height and abs(c.lateral) > cfg.cluster.signature_min_lateral
    assert (c.reason, c.zone) == ("", "gauge")                 # the column shape, a free top: an obstacle
    assert _the(_clusters(pole, with_frame=False), 60.0).reason == "column"   # no frame: the shape alone
    off = DetectorConfig()
    off.cluster.column_free_max_top = 0.0
    assert _the(_clusters(pole, off), 60.0).reason == "column"                # 0 = off
    assert _the(_clusters([_pole(60.0, 0.7, top=4.2)]), 60.0).reason == "column"   # continues to the vault
    # reaching the envelope top: at 50 m a ring meets the 3.05 m post at 2.956 m, the next passes over it
    cut = [_pole(50.0, 0.7, top=3.05)]
    c = _the(_clusters(cut), 50.0)
    assert c.height_max > cfg.cluster.column_free_max_top and c.reason == "column"
    high = DetectorConfig()
    high.cluster.column_free_max_top = 3.0
    assert _the(_clusters(cut, high), 50.0).reason == ""
    # 15.10 (cluster.column_free_tall_gap, opt-in): with the frame's heights the post is followed above the cut to
    # its true top, 1.15 m under the vault, its own rays above it passing beyond it: an obstacle; 0 (shipped) = off
    tall_on = DetectorConfig()
    tall_on.cluster.column_free_tall_gap = 0.3
    assert _the(_clusters(cut, tall_on, heights=True), 50.0).reason == ""
    assert _the(_clusters(cut, heights=True), 50.0).reason == "column"
    assert _the(_clusters([_pole(50.0, 0.7, top=4.2)], tall_on, heights=True), 50.0).reason == "column"
    c = _the(_clusters([_pole(60.0, 1.12)]), 60.0)            # mostly outside the strict envelope (1.05 m)
    assert 0 < c.n_gauge < cfg.cluster.column_free_min_core * c.n and c.reason == "column"


def _hit(x, kind):
    """One hit of a track at ``x``: 'col' a cluster the column rule demoted, 'spare' the same cluster whose top
    the free-top test saw free (Cluster.spared: zone 'gauge', no reason), 'obj' a person-size obstacle, 'adv'
    the same advisory (beyond the trusted axis)."""
    tall = kind in ("col", "spare")
    return Cluster(points_idx=np.arange(3), n=12, n_raw=24, centroid=np.array([x + 0.15, 0.7, 1.3]),
                   bbox_min=np.array([x, 0.55, 0.0]), bbox_max=np.array([x + 0.3, 0.85, 2.6 if tall else 1.8]),
                   distance=x, lateral=0.7, height_min=0.0, height_max=2.6 if tall else 1.8, intensity=30.0,
                   n_expected=12.0, score=1.0, zone="warning" if kind in ("col", "adv") else "gauge", n_gauge=12,
                   reason={"col": "column", "adv": "beyond_axis"}.get(kind, ""), spared=kind == "spare")


def _zones(kinds, **tracking):
    """The track's reported zone after each hit (10 Hz, approaching at 1.5 m per frame)."""
    t = Tracker(replace(DetectorConfig().tracking, **tracking))
    out = []
    for k, kind in enumerate(kinds):
        t.update([_hit(60.0 - 1.5 * k, kind)], frame_dt=0.1)
        rep = t.confirmed()
        out.append(rep[0].zone if rep else None)
    return out


def test_one_spare_is_the_column_the_column_rule_made():
    """14.10 (review of 13.10; tracking.column_free_min_spares 2): a hit the free-top test spared is believed
    only when the track had another such hit among its last zone_window (10) hits; alone it is the column hit
    the column rule made of it (reason 'column', zone 'warning'), so the column hold, the zone vote and
    explained_run see what they saw before 13.10. The review's standing train (squareT_platform_squareT_switch,
    20-30 % point dropout): a platform-edge track had one hit spared and became a STOP for 2-11 frames; a mount
    pitch of -2 deg on roundT_doubleT did the same for one frame. The judge's pole, spared hit after hit, is
    believed from its second spared hit."""
    cfg = DetectorConfig().tracking
    assert (cfg.column_hold, cfg.column_free_min_spares, cfg.zone_window) == (2, 2, 10)        # shipped 14.10
    # one spare among column hits: as the column rule alone, held
    assert _zones(["col", "spare"] + ["obj"] * 6)[-1] == "warning"
    assert _zones(["col", "spare"] + ["obj"] * 6, column_free_min_spares=1)[-1] == "gauge"   # 13.10: released
    assert _zones(["col", "spare"] + ["obj"] * 6, column_free_min_spares=0)[-1] == "gauge"
    assert _zones(["col"] * 2 + ["obj"] * 6)[-1] == "warning"
    # the standing train's track: in and out of the envelope, then one spared hit - the column it would have
    # been (zone vote 2 of 5, explained_run: 5 clean hits before a STOP), not the hit that starts a STOP
    seq = ["obj", "adv", "obj", "adv", "adv", "obj", "spare"] + ["obj"] * 3
    z, z13 = _zones(seq), _zones(seq, column_free_min_spares=1)
    assert z == _zones([k if k != "spare" else "col" for k in seq]) and "gauge" not in z
    assert z13[:7] == z[:7] and z13[7:] == ["gauge"] * 3           # 13.10: the spare let a STOP start
    # a pole: column-shaped in every hit, its top seen free in every hit - believed from its second spare
    t = Tracker(DetectorConfig().tracking)
    for k in range(12):
        c = _hit(60.0 - 1.5 * k, "spare")
        t.update([c], frame_dt=0.1)
        assert (c.reason, c.zone) == (("column", "warning") if k == 0 else ("", "gauge")), k
    assert t.confirmed()[0].zone == "gauge"
    assert _zones(["spare"] * 12) == _zones(["col"] + ["obj"] * 11)


def test_detector_hands_the_frame_and_its_channel_ids_to_the_corridor_clustering(tunnel, monkeypatch):
    """14.10 (review): the free-top test reads the ring in between from the frame's channel ids, so the detector
    must hand the corridor clustering the processed cloud and the frame's ids, index for index (the
    clustering-level tests above cannot see that wiring; with ring=None every detector-level test runs the
    ring table). A frame without ids hands over None."""
    import resense.detector as det_mod
    from resense.detector import Detector
    from resense.frame import Frame

    frame, _, _ = tunnel
    seen = []
    orig = det_mod._clusters_of

    def spy(c, cfg, **kw):
        if "frame_xyz" in kw:
            seen.append((kw["frame_xyz"], kw["frame_ring"], kw["frame_h"], kw["frame_dy"]))
        return orig(c, cfg, **kw)

    monkeypatch.setattr(det_mod, "_clusters_of", spy)
    ring = (np.arange(len(frame.xyz)) % 128).astype(np.uint16)
    Detector(DetectorConfig()).process(Frame(xyz=frame.xyz, intensity=frame.intensity, ring=ring, stamp=0.0))
    ((fx, fr, fh, fd),) = seen
    assert fx is not None and fr is not None and len(fx) == len(fr) == len(ring) and np.array_equal(fr, ring)
    # 15.10: and every return's height above the rail head and lateral, index for index (the corridor's)
    assert fh is not None and fd is not None and len(fh) == len(fd) == len(fx)
    from resense.gauge import corridor_coordinates
    det = Detector(DetectorConfig())
    seen.clear()
    res = det.process(Frame(xyz=frame.xyz, intensity=frame.intensity, stamp=0.0))
    ((fx, fr, fh, fd),) = seen
    assert fx is not None and len(fx) == len(frame.xyz) and fr is None
    dy, h = corridor_coordinates(res.xyz, det.track)
    assert np.allclose(fh, h) and np.allclose(fd, dy)


def test_channel_ids_out_of_elevation_order_are_not_read_as_rings():
    """14.10 (review) / 15.10 (P2): ids are read as ring order only where the window's ids number its rings from
    the highest down (the mean elevation of each id's returns falls as the id rises). Ids numbered bottom-up are
    not: the ring in between is then one the frame shows beside the object, as without ids - the pole occluded
    from above under a mount tilt stays a column, a pole whose top is seen free stays free. One id for every
    return (set O) is no ids."""
    beam = (40.0, 40.5, -1.0, 1.0, 2.5, 3.5)
    n = RING_ELEVATION_DEG.size - 1
    xyz, h, lab, ring = _cast([_pole(60.0, 0.7), beam], pitch=-0.15)
    idx = np.flatnonzero((lab == 1) & (h <= 3.0))
    assert not top_is_free(xyz, idx)
    assert not top_is_free(xyz, idx, frame_ring=(n - ring).astype(np.uint16))
    xyz, h, lab, ring = _cast([_pole(60.0, 0.7)])
    idx = np.flatnonzero((lab == 1) & (h <= 3.0))
    assert top_is_free(xyz, idx, frame_ring=(n - ring).astype(np.uint16))
    assert top_is_free(xyz, idx, frame_ring=np.zeros_like(ring)) == top_is_free(xyz, idx)
    qe = np.degrees(np.arctan2(xyz[:, 2], np.hypot(xyz[:, 0], xyz[:, 1]))).astype(np.float64)
    rw = ring.astype(np.int64)
    assert _ids_in_elevation_order(rw, qe)
    assert not _ids_in_elevation_order(n - rw, qe)                                   # bottom-up
    perm = np.random.default_rng(3).permutation(n + 1)
    assert not _ids_in_elevation_order(perm[rw], qe)                                 # another order
    assert not _ids_in_elevation_order(np.minimum(rw, 1), qe)                        # two ids: not enough
    assert _ids_in_elevation_order(np.where(rw % 7 == 0, -1, rw), qe)                # unknown ids left out


def _dark_band(x, lat, lo, hi):
    """A column to the vault (4.2 m) whose face between ``lo`` and ``hi`` m above the rails returns nothing."""
    return [_pole(x, lat, top=lo), _pole(x, lat, top=hi, bottom=lo, mode="a"), _pole(x, lat, top=4.2, bottom=hi)]


def test_a_column_continuing_above_a_dark_band_is_a_column():
    """15.10 (review round 3, P1; cluster.column_free_window 1.2): a column whose face right above the cluster's
    top returns nothing (dark paint, glass, a black sign) while the rays beside it reach the tunnel behind read as
    free on 14.10, whose continuation was the first ring with returns only (the safety review's dark-band
    what-if: most real ride columns spared). Any return at the top's range over the window up to 1.2 m above the
    top is continuation now: a 0.6 m band right above a 2.6 m top at 30-140 m, a 1.0 m band to 100 m. The free
    pole stays free: the window stays 0.15 m under the local vault. Not told apart: a face dark up to the vault."""
    cfg = DetectorConfig().cluster
    assert (cfg.column_free_window, cfg.column_free_vault_margin) == (1.2, 0.3)       # shipped 15.10
    for x in (30.0, 60.0, 100.0, 140.0):
        for lat in (0.0, 0.7):
            if x <= 100.0:            # at 140 m the first ring above the band's top meets the face again
                assert _free(_dark_band(x, lat, 2.6, 3.2), ids=True), (x, lat)                 # 14.10
                assert _free(_dark_band(x, lat, 2.6, 3.2), ids=True, heights=True), (x, lat)   # window 0 = 14.10
            assert not _free(_dark_band(x, lat, 2.6, 3.2), ids=True, heights=True, window=1.2), (x, lat)
            assert _free([_pole(x, lat)], ids=True, heights=True, window=1.2), (x, lat)
            assert not _free([_pole(x, lat, top=4.2)], ids=True, heights=True, window=1.2), (x, lat)
            dark_to_vault = [_pole(x, lat, top=2.6), _pole(x, lat, top=4.2, bottom=2.6, mode="a")]
            assert _free(dark_to_vault, ids=True, heights=True, window=1.2), (x, lat)        # not told apart
            if x <= 100.0:
                assert not _free(_dark_band(x, lat, 2.6, 3.6), ids=True, heights=True, window=1.2), (x, lat)


def test_the_window_stays_under_the_local_vault():
    """15.10: the window never reaches what is over the object at its range: the vault, a ceiling, a beam or a
    lintel across the track, which the rays above a free top meet there too. The local vault is the lowest return
    over the object's lateral extent +- 0.5 m around it, measured in the frame; the object's own face is left
    out. A beam across the track over a free pole at its range, 0.5 m above its top, leaves it free; the same
    beam narrowed to the pole's own azimuth span (a lamp right above it) is read as its continuation."""
    for x in (30.0, 60.0, 100.0):
        xyz, h, lab, ring = _cast([_pole(x, 0.7)])
        idx = np.flatnonzero((lab == 1) & (h <= 3.0))
        rays = FrameRays(xyz, ring, h, xyz[:, 1].astype(np.float64))
        assert abs(_local_vault(rays, idx, 2.8, np.zeros(0, dtype=np.int64)) - 4.2) < 0.01
        beam = (x - 0.3, x + 0.6, -2.0, 2.0, 3.3, 3.5)
        assert _free([_pole(x, 0.7), beam], ids=True, heights=True, window=1.2), x
        lamp = (x - 0.1, x + 0.4, 0.6, 0.8, 3.3, 3.5)
        assert not _free([_pole(x, 0.7), lamp], ids=True, heights=True, window=1.2), x
        assert _free([_pole(x, 0.7), lamp], ids=True), x                                       # 14.10
    assert _local_vault(FrameRays(xyz, ring), idx, 2.8, np.zeros(0, dtype=np.int64)) is None
    # only what stands over free space: a post over the axis 4 m beyond the object (the ride's crossover posts
    # under the far axis) is not the vault; a beam across the track there is
    for extra, vault in (((64.0, 64.3, -0.15, 0.15, 0.0, 4.2), 4.2), ((63.0, 63.4, -2.0, 2.0, 3.4, 3.6), 3.4)):
        xyz, h, lab, ring = _cast([_pole(60.0, 0.7), extra])
        idx = np.flatnonzero((lab == 1) & (h <= 3.0))
        rays = FrameRays(xyz, ring, h, xyz[:, 1].astype(np.float64))
        assert abs(_local_vault(rays, idx, 2.8, np.zeros(0, dtype=np.int64)) - vault) < 0.02, extra


def test_a_64_ring_sensor_reads_no_invented_empty_ring():
    """15.10 (review round 3, P2): the 14.10 fallback read the Pandar128's ring table where the frame carried no
    ids, its ring nearest to the top put at the top; for another sensor that invented an empty ring above a
    column occluded from above (the safety review: a 64-ring sensor at 0.33 deg, free at 30, 60 and 100 m). Now,
    without ids in elevation order, the ring in between must be one the frame shows beside the object: a 64-ring
    sensor has none between its adjacent rings - with no ids, ids top-down and ids bottom-up the occluded column
    stays a column; a free pole stays free on the returns beyond its top."""
    el64 = np.linspace(-16.0, 5.0, 64)
    for x in (30.0, 60.0, 100.0, 140.0):
        xl = 0.6 * x
        hl = H0 + (2.85 - H0) * xl / x                      # the sight line to the column's top at 0.6 x
        beam = (xl, xl + 0.2, -2.0, 2.0, hl - 0.1, hl + 0.3)
        for ids in (None, np.arange(64)[::-1].copy(), np.arange(64)):
            xyz, h, lab, ring = _cast([(x, x + 0.4, 0.5, 0.9, 0.0, 4.2), beam], elev=el64, ids=ids)
            idx = np.flatnonzero((lab == 1) & (h <= 3.0))
            assert idx.size >= 4
            assert not top_is_free(xyz, idx, frame_ring=None if ids is None else ring), (x, ids)
            xyz, h, lab, ring = _cast([_pole(x, 0.7)], elev=el64, ids=ids)
            idx = np.flatnonzero((lab == 1) & (h <= 3.0))
            assert top_is_free(xyz, idx, frame_ring=None if ids is None else ring), (x, ids)


def test_frame_rays_index_the_frame_once_and_read_the_window_of_the_scan():
    """15.10 (review round 3, P3): 14.10 tested every return of the frame (~184 k) in floats in every test.
    FrameRays caches a bucket of each return's azimuth on its first window and reads each window through its
    buckets - the same returns as the scan, in the same order - and find_clusters makes one per call (once a
    frame)."""
    rng = np.random.default_rng(5)
    xyz = (rng.normal(0.0, 1.0, (20000, 3)) * np.array([60.0, 20.0, 3.0])).astype(np.float32)
    xyz[:50, 0] = 0.0
    xyz[50:60, 1] = 0.0
    rays = FrameRays(xyz)
    assert rays._keys is None                                   # nothing cached before the first window
    X, Y = xyz[:, 0], xyz[:, 1]
    for a0 in list(rng.uniform(-60.0, 60.0, 40)) + [-0.06, 0.0, 44.99]:
        a1 = a0 + float(rng.uniform(0.0, 5.0))
        t0, t1 = np.tan(np.radians(a0)), np.tan(np.radians(a1))
        scan = np.flatnonzero((X > 0) & (Y >= t0 * X) & (Y <= t1 * X))
        assert np.array_equal(rays.window(a0, a1), scan), (a0, a1)
    keys = rays._keys
    rays.window(1.0, 2.0)
    assert rays._keys is keys                                   # cached once
    # the test gives the same answers through the index as through the scan of 14.10
    for boxes in ([_pole(60.0, 0.7)], [_pole(60.0, 0.7, top=4.2)], [_pole(90.0, 0.7), (60.0, 60.5, -1.0, 1.0, 2.5, 3.5)]):
        xyz, h, lab, ring = _cast(boxes)
        idx = np.flatnonzero((lab == 1) & (h <= 3.0))
        assert top_is_free(FrameRays(xyz, ring), idx) == top_is_free(xyz, idx, frame_ring=ring)
    calls = []
    orig = FrameRays.window

    def count(self, a0, a1):
        calls.append(self._keys is None)
        return orig(self, a0, a1)

    import pytest
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(FrameRays, "window", count)
        cl = _clusters([_pole(40.0, 0.7), _pole(60.0, -0.7), _pole(80.0, 0.7)], heights=True)
    assert sum(c.reason == "" and c.size[2] > 2.2 for c in cl) == 3
    assert len(calls) >= 3 and calls[0] and not any(calls[1:])  # one index for the three tests of the frame


def test_a_pole_taller_than_the_envelope_is_followed_to_its_top():
    """15.10 (review round 3, P4; cluster.column_free_tall_gap, opt-in, 0 shipped): the candidates are cut at the 3.0 m envelope
    top, so a 3.2-3.8 m pole or ladder standing in the envelope read as a column (its ring above the cut meets
    itself). It is followed above the cut along its own returns at its range to its true top, which must lie at
    least 0.3 m under the local vault, every one of its own rays above it (up to 0.3 m under the vault, on at least
    two rings) passing beyond it. A column to the vault, a column whose face above the cut is dark (its own rays
    return nothing) and one whose face resumes above a dark band stay columns; a 3.6 m pole under a 4.2 m vault at
    100 m too (one ring of its own rays between its top and 3.9 m); without the frame's heights the test is not
    asked. Not shipped (0): no gain on the judge's 3.2 / 3.6 m poles on A, see config.py."""
    assert DetectorConfig().cluster.column_free_tall_gap == 0.0                      # 15.10: off
    for x in (20.0, 30.0, 60.0, 100.0):
        for lat in (0.0, 0.7):
            def tall(boxes, **kw):
                return _free(boxes, ids=True, heights=True, window=1.2, tall_gap=0.3, **kw)
            for top in (3.2, 3.4, 3.6):
                assert tall([_pole(x, lat, top=top)]) == (top < 3.5 or x < 100.0), (x, lat, top)
                assert not _free([_pole(x, lat, top=top)], ids=True, heights=True, window=1.2), (x, lat, top)
            assert not tall([_pole(x, lat, top=4.2)]), (x, lat)
            assert not tall([_pole(x, lat, top=3.0), _pole(x, lat, top=4.2, bottom=3.0, mode="a")]), (x, lat)
            assert not tall(_dark_band(x, lat, 3.0, 3.4)), (x, lat)
            assert not tall([_pole(x, lat, top=3.3), _pole(x, lat, top=4.2, bottom=3.3, mode="a")]), (x, lat)
            assert not tall([_pole(x, lat, top=3.75)], vault=3.8), (x, lat)            # not clearly under it
    xyz, h, lab, ring = _cast([_pole(30.0, 0.7, top=3.4)])
    idx = np.flatnonzero((lab == 1) & (h <= 3.0))
    assert not top_is_free(xyz, idx, frame_ring=ring, tall_gap=0.3)                  # no heights: not asked
