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

from resense.clustering import Cluster, find_clusters, top_is_free
from resense.config import DetectorConfig
from resense.gauge import point_in_polygon, widened_profile
from resense.sensor import RING_ELEVATION_DEG
from resense.tracking import Tracker

H0 = 1.8          # sensor height above the rail head (m); the vehicle frame has the sensor at the origin


def _cast(boxes, vault=4.2, grade=0.0, wall=220.0, az=(-3.0, 3.0), max_range=210.0, pitch=0.0):
    """(xyz in the corrected vehicle frame, h above the rails, label: 0 = background, k = boxes[k - 1], channel id)
    of the rays of the window. The rails are at z = grade * x - H0; ``boxes``: (x0, x1, y0, y1, h0, h1) above them
    (the rail level at x0); the vault at ``vault`` above the rails; a wall across the track at x = ``wall`` (beyond
    max_range). ``pitch`` (deg, nose up): the sensor is mounted tilted, its rays are its rings rotated by it
    (the cloud as the mount calibration corrects it)."""
    el = np.radians(RING_ELEVATION_DEG)
    a = np.radians(np.arange(az[0], az[1] + 1e-9, 0.1))
    E, A = np.meshgrid(el, a, indexing="ij")
    rid = np.repeat(np.arange(el.size), a.size)
    d = np.stack([np.cos(E) * np.cos(A), np.cos(E) * np.sin(A), np.sin(E)], axis=-1).reshape(-1, 3)
    p = np.radians(pitch)
    d = d @ np.array([[np.cos(p), 0.0, -np.sin(p)], [0.0, 1.0, 0.0], [np.sin(p), 0.0, np.cos(p)]]).T
    with np.errstate(divide="ignore", invalid="ignore"):
        rise = d[:, 2] - grade * d[:, 0]                        # the ray's climb over the rails per unit length
        t = np.minimum.reduce([np.where(d[:, 0] > 1e-9, wall / d[:, 0], np.inf),
                               np.where(rise > 1e-9, (vault - H0) / rise, np.inf),
                               np.where(rise < -1e-9, -H0 / rise, np.inf)])
        lab = np.zeros(len(d), dtype=int)
        for k, (x0, x1, y0, y1, h0, h1) in enumerate(boxes, start=1):
            rz = grade * x0 - H0
            lo, hi = np.array([x0, y0, rz + h0]), np.array([x1, y1, rz + h1])
            t0, t1 = lo / d, hi / d
            tn = np.nanmax(np.minimum(t0, t1), axis=1)
            tf = np.nanmin(np.maximum(t0, t1), axis=1)
            hit = (tn <= tf) & (tn > 0) & (tn < t)
            t = np.where(hit, tn, t)
            lab = np.where(hit, k, lab)
    ok = t < max_range
    xyz = (d[ok] * t[ok, None]).astype(np.float32)
    h = xyz[:, 2].astype(np.float64) + H0 - grade * xyz[:, 0]
    return np.repeat(xyz, 2, axis=0), np.repeat(h, 2), np.repeat(lab[ok], 2), np.repeat(rid[ok], 2).astype(np.uint16)


def _pole(x, lat, top=2.8, w=0.3):
    return (x, x + w, lat - w / 2, lat + w / 2, 0.0, top)


def _free(boxes, ids=False, **kw):
    """top_is_free for box 1's returns a corridor cluster can hold (up to the 3.0 m envelope top); ``ids``: with
    the frame's channel ids."""
    xyz, h, lab, ring = _cast(boxes, **kw)
    idx = np.flatnonzero((lab == 1) & (h <= 3.0))
    assert idx.size >= 4
    return top_is_free(xyz, idx, frame_ring=ring if ids else None)


def _clusters(boxes, cfg=None, with_frame=True):
    cfg = cfg or DetectorConfig()
    xyz, h, _, _ = _cast(boxes)
    dy = xyz[:, 1].astype(np.float64)
    idx = np.flatnonzero(point_in_polygon(dy, h, widened_profile(cfg.gauge, cfg.gauge.warning_margin)))
    ig = point_in_polygon(dy[idx], h[idx], cfg.gauge.profile)
    return find_clusters(xyz[idx], np.full(idx.size, 30.0, np.float32), dy[idx], h[idx], ig, cfg.cluster,
                         frame_idx=idx, frame_xyz=xyz if with_frame else None)


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
    the sensor. A column there continues."""
    for grade in (0.0, -0.005):
        assert _free([_pole(180.0, 0.7)], vault=3.6, grade=grade), grade
        assert not _free([_pole(180.0, 0.7, top=3.6)], vault=3.6, grade=grade), grade


def test_channel_ids_find_the_ring_in_between_under_a_mount_tilt():
    """The ring in between is read from the frame's channel ids where it carries them: under a mount tilt the
    corrected frame moves the rings off the sensor's table, and with the ring nearest to the top put at the top
    a pole occluded from above (a beam at 40 m takes the ring above its top) would have an empty ring invented
    between them (0.11-0.17 deg nose down, 0.45-0.5 deg up at 60 m). The ids agree with the table on a level
    mount; ids out of elevation order (set O: all 0) leave the table in charge."""
    beam = (40.0, 40.5, -1.0, 1.0, 2.5, 3.5)
    for x in (60.0, 90.0):
        for ids in (False, True):
            assert _free([_pole(x, 0.7)], ids=ids) and not _free([_pole(x, 0.7, top=4.2)], ids=ids)
    assert not _free([_pole(60.0, 0.7), beam], ids=True)
    for pitch in (-0.15, 0.47):
        assert _free([_pole(60.0, 0.7), beam], pitch=pitch)          # the table alone: the wrong ring
        assert not _free([_pole(60.0, 0.7), beam], ids=True, pitch=pitch), pitch
        assert _free([_pole(60.0, 0.7)], ids=True, pitch=pitch), pitch
        assert not _free([_pole(60.0, 0.7, top=4.2)], ids=True, pitch=pitch), pitch
    for pitch in (0.1, 0.15):                                       # 90 m, nose up
        assert _free([_pole(90.0, 0.7), (60.0, 60.5, -1.0, 1.0, 2.5, 3.5)], pitch=pitch)
        assert not _free([_pole(90.0, 0.7), (60.0, 60.5, -1.0, 1.0, 2.5, 3.5)], ids=True, pitch=pitch), pitch
    xyz, h, lab, ring = _cast([_pole(60.0, 0.7), beam], pitch=-0.15)
    idx = np.flatnonzero((lab == 1) & (h <= 3.0))
    assert top_is_free(xyz, idx, frame_ring=np.zeros_like(ring)) == top_is_free(xyz, idx)   # no ids: the table


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
            seen.append((kw["frame_xyz"], kw["frame_ring"]))
        return orig(c, cfg, **kw)

    monkeypatch.setattr(det_mod, "_clusters_of", spy)
    ring = (np.arange(len(frame.xyz)) % 128).astype(np.uint16)
    Detector(DetectorConfig()).process(Frame(xyz=frame.xyz, intensity=frame.intensity, ring=ring, stamp=0.0))
    ((fx, fr),) = seen
    assert fx is not None and fr is not None and len(fx) == len(fr) == len(ring) and np.array_equal(fr, ring)
    seen.clear()
    Detector(DetectorConfig()).process(Frame(xyz=frame.xyz, intensity=frame.intensity, stamp=0.0))
    ((fx, fr),) = seen
    assert fx is not None and len(fx) == len(frame.xyz) and fr is None


def test_channel_ids_out_of_the_tables_order_are_no_empty_ring_evidence():
    """14.10 (review): the ring table is the Pandar128's. Where the frame carries ids that are not in its order
    (a driver numbering the rings bottom-up, another sensor) the table is not read either: the pole occluded
    from above under a mount tilt, which the table alone reads as free, stays a column; a pole whose top is
    seen free on the rays beyond it stays free. One id for every return (set O) is no ids: the table."""
    beam = (40.0, 40.5, -1.0, 1.0, 2.5, 3.5)
    n = RING_ELEVATION_DEG.size - 1
    xyz, h, lab, ring = _cast([_pole(60.0, 0.7), beam], pitch=-0.15)
    idx = np.flatnonzero((lab == 1) & (h <= 3.0))
    assert top_is_free(xyz, idx)                                    # the table: an invented empty ring
    assert not top_is_free(xyz, idx, frame_ring=(n - ring).astype(np.uint16))
    xyz, h, lab, ring = _cast([_pole(60.0, 0.7)])
    idx = np.flatnonzero((lab == 1) & (h <= 3.0))
    assert top_is_free(xyz, idx, frame_ring=(n - ring).astype(np.uint16))
    assert top_is_free(xyz, idx, frame_ring=np.zeros_like(ring)) == top_is_free(xyz, idx)
