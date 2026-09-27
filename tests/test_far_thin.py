"""Far scan lines as track evidence, gated by a consistent approach (27.09, P5 range; on by default
since 27.09: ``tracking.thin_far_min_distance`` 60, ``cluster.weak_min_points`` 4; 0 = off).

Far away an object inside the envelope is often a single scan line there (the organizers' plank
across the rails at 85-100 m, the lower edge of the box at the envelope top at 100-120 m): flatter
than ``cluster.min_height``, it never made a track. With ``thin_far_min_distance`` > 0 such a scan
line (zone gauge, ``thin_far_min_voxels`` strict voxels, beyond the distance, overlapping no other
cluster of the frame) may start and continue a track, and a track with such a hit among its last
``zone_window`` hits is reported only while its distances lie on a line in sensor time that
approaches at ``approach_min_speed`` .. ``ego_speed_max`` with an RMS residual of at most
``approach_max_residual``. A scan line of the bed or the vault is fixed in the sensor frame (a
standing train: no approach) or jumps with the pitch (no line).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from resense.clustering import Cluster
from resense.config import DetectorConfig, TrackingConfig
from resense.tracking import Tracker

ROOT = Path(__file__).resolve().parents[1]


def _cl(x: float, thin: bool = True, n_gauge: int = 6, zone: str = "gauge", lateral: float = 0.0) -> Cluster:
    c = np.array([x, lateral, 0.3])
    return Cluster(points_idx=np.arange(3), n=n_gauge + 2, n_raw=n_gauge + 2, centroid=c,
                   bbox_min=c - np.array([0.2, 0.9, 0.0]), bbox_max=c + np.array([0.2, 0.9, 0.0]),
                   distance=x, lateral=lateral, height_min=0.3, height_max=0.3, intensity=10.0,
                   n_expected=10.0, score=1.0, zone=zone, n_gauge=n_gauge, thin=thin)


def _cfg(**kw) -> TrackingConfig:
    base = {"stop_keep_signature": False, "stop_keep_thin": 0, "thin_far_min_distance": 60.0}
    return TrackingConfig(**{**base, **kw})


def _run(xs, cfg=None, thin=True, n_gauge=6):
    """One far scan line per frame at the distances ``xs``; returns whether any track is reported."""
    tr = Tracker(cfg or _cfg())
    out = []
    for x in xs:
        cl = [] if x is None else [_cl(x, thin=thin, n_gauge=n_gauge)]
        tr.update([], ego_shift=0.0, frame_dt=0.1, thin=cl, far_thin=cl)
        out.append(any(t.reported for t in tr.tracks))
    return out


def test_shipped_default_and_both_yaml():
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        assert cfg.tracking.thin_far_min_distance == 60.0 and cfg.cluster.weak_min_points == 4


def test_off_scan_lines_never_start_a_track():
    tr = Tracker(_cfg(thin_far_min_distance=0.0))
    for k in range(10):
        cl = [_cl(100.0 - 1.7 * k)]
        tr.update([], ego_shift=0.0, frame_dt=0.1, thin=cl, far_thin=cl)
    assert not tr.tracks


def test_approaching_scan_line_is_reported_after_confirmation():
    out = _run([100.0 - 1.7 * k for k in range(8)])
    assert out[:4] == [False] * 4          # confirm_time_s 0.5 s and approach_hits 5
    assert out[4] and all(out[4:])


def test_static_scan_line_is_never_reported():
    # a ring on the bed ahead of a standing (or slowly moving) train: fixed in the sensor frame
    assert not any(_run([95.0] * 12))
    assert not any(_run([95.0 - 0.1 * k for k in range(12)]))   # 1 m/s < approach_min_speed


def test_jumping_scan_line_is_never_reported():
    # a ring whose range jumps with the pitch (+-1.2 m about the line, alternating): no consistent approach
    xs = [100.0 - 1.0 * k + (1.2 if k % 2 else -1.2) for k in range(12)]
    assert not any(_run(xs))


def test_near_or_sparse_or_advisory_scan_lines_are_not_used():
    cfg = _cfg(thin_far_min_distance=60.0, thin_far_min_voxels=4)
    tr = Tracker(cfg)
    for k in range(8):
        near = _cl(55.0 - 1.7 * k)                 # the detector selects far_thin; the tracker trusts it
        tr.update([], ego_shift=0.0, frame_dt=0.1, thin=[near], far_thin=[])
    assert not tr.tracks


def test_mixed_track_needs_the_approach_only_to_start_a_report():
    cfg = _cfg()
    tr = Tracker(cfg)
    # a standing normal cluster is reported as before (no scan-line hit in its window)
    for _ in range(6):
        tr.update([_cl(90.0, thin=False)], ego_shift=0.0, frame_dt=0.1, far_thin=[])
    assert any(t.reported for t in tr.tracks)
    # a scan-line hit on the same standing object does not take the report down (the ride: a STOP
    # episode split in two when it did)
    tr.update([], ego_shift=0.0, frame_dt=0.1, far_thin=[_cl(90.0)])
    assert any(t.reported for t in tr.tracks)
    # a standing track that is not reported yet and has a scan-line hit is not reported
    tr = Tracker(cfg)
    tr.update([], ego_shift=0.0, frame_dt=0.1, far_thin=[_cl(90.0)])
    for _ in range(8):
        tr.update([_cl(90.0, thin=False)], ego_shift=0.0, frame_dt=0.1, far_thin=[])
    assert not any(t.reported for t in tr.tracks)


def test_scan_line_continues_an_approaching_normal_track():
    xs = [100.0 - 1.7 * k for k in range(8)]
    tr = Tracker(_cfg())
    rep = []
    for k, x in enumerate(xs):
        normal = k % 2 == 0
        cl = _cl(x, thin=not normal)
        tr.update([cl] if normal else [], ego_shift=0.0, frame_dt=0.1, far_thin=[] if normal else [cl])
        rep.append(any(t.reported for t in tr.tracks))
    assert len(tr.tracks) == 1               # one track, continued by the scan lines
    assert rep[4] and all(rep[4:])


def test_off_run_unchanged_by_the_new_keys():
    # the keys only act when thin_far_min_distance > 0 (the approach history is not even recorded)
    tr = Tracker(TrackingConfig(thin_far_min_distance=0.0))
    tr.update([_cl(80.0, thin=False)], ego_shift=0.0, frame_dt=0.1)
    assert tr.tracks[0].approach == [] and tr.tracks[0].thin_hist == []


def _four_points(x: float):
    """A 0.3 m cube seen with 4 returns at ``x`` (as set O's #2 at 60-75 m), in track coordinates."""
    from resense.config import ClusterConfig
    pts = np.array([[x, 0.3, 1.3], [x, 0.45, 1.3], [x + 0.05, 0.3, 1.42], [x + 0.05, 0.45, 1.42]], dtype=np.float32)
    return pts, ClusterConfig()


def test_weak_cluster_kept_only_when_enabled_and_far_enough():
    from dataclasses import replace
    from resense.clustering import find_clusters
    pts, ccfg = _four_points(70.0)
    inten = np.full(4, 30.0, np.float32)
    dy, h, ig = pts[:, 1].copy(), pts[:, 2].copy(), np.ones(4, bool)
    assert find_clusters(pts, inten, dy, h, ig, ccfg) == []                     # under min_points 5: dropped
    off = replace(ccfg, weak_min_points=0)                                       # on (4) since 27.09
    assert find_clusters(pts, inten, dy, h, ig, off, weak_from=60.0) == []      # weak_min_points 0: off
    on = replace(ccfg, weak_min_points=4)
    out = find_clusters(pts, inten, dy, h, ig, on, weak_from=60.0)
    assert len(out) == 1 and out[0].weak and out[0].zone == "gauge"
    assert find_clusters(pts, inten, dy, h, ig, on, weak_from=80.0) == []       # nearer than the far distance
    assert find_clusters(pts[:3], inten[:3], dy[:3], h[:3], ig[:3], on, weak_from=60.0) == []   # 3 < 4 voxels


def test_weak_cluster_needs_the_approach_like_a_scan_line():
    tr = Tracker(_cfg())
    rep = []
    for k in range(8):
        cl = _cl(75.0 - 1.6 * k, thin=False, n_gauge=4)
        cl.weak = True
        tr.update([], ego_shift=0.0, frame_dt=0.1, far_thin=[cl])
        rep.append(any(t.reported for t in tr.tracks))
    assert not any(rep[:4]) and all(rep[4:])
    tr = Tracker(_cfg())
    for k in range(10):                      # the same weak evidence at a standing train: never reported
        cl = _cl(75.0, thin=False, n_gauge=4)
        cl.weak = True
        tr.update([], ego_shift=0.0, frame_dt=0.1, far_thin=[cl])
    assert not any(t.reported for t in tr.tracks)


def test_ambiguous_scan_line_is_not_used():
    """A scan line inside the gates of two tracks (one structure seen as two tracks on the ride) is
    neither a hit of one of them nor a new track: using it moved one track and changed the next
    frame's association."""
    tr = Tracker(_cfg())
    tr.update([_cl(100.0, thin=False), _cl(102.0, thin=False, lateral=0.5)], ego_shift=0.0, frame_dt=0.1)
    assert len(tr.tracks) == 2
    before = [t.centroid.copy() for t in tr.tracks]
    tr.update([], ego_shift=0.0, frame_dt=0.1, far_thin=[_cl(101.0, lateral=0.2)])
    assert len(tr.tracks) == 2
    assert all(np.allclose(t.centroid, b) for t, b in zip(tr.tracks, before))
    assert all(t.misses == 1 and not t.thin_hist[-1] for t in tr.tracks)


def test_scan_line_at_a_matched_track_is_not_a_new_track():
    tr = Tracker(_cfg())
    tr.update([_cl(100.0, thin=False)], ego_shift=0.0, frame_dt=0.1)
    tr.update([_cl(98.5, thin=False)], ego_shift=0.0, frame_dt=0.1, far_thin=[_cl(99.0, lateral=0.3)])
    assert len(tr.tracks) == 1 and tr.tracks[0].hits == 2


def test_weak_hits_long_ago_still_need_the_approach():
    """The ride (piece 2, frames 237-243): weak 4-voxel hits kept a fixture ahead of a standing train
    alive; later normal hits alone would have confirmed it. A track ever matched by far evidence
    starts a report only while it approaches."""
    tr = Tracker(_cfg())
    for k in range(6):
        cl = _cl(96.8, thin=False, n_gauge=4)
        cl.weak = True
        tr.update([], ego_shift=0.0, frame_dt=0.1, far_thin=[cl])
    for k in range(15):                       # > zone_window normal hits at the same place
        tr.update([_cl(96.8, thin=False)], ego_shift=0.0, frame_dt=0.1, far_thin=[])
    assert len(tr.tracks) == 1 and tr.tracks[0].far_evidence
    assert not tr.tracks[0].reported


def test_advisory_track_with_far_evidence_is_not_promoted_without_approach():
    """The ride (piece 2, frames 222-243): a fixture ahead of a standing train was reported as
    advisory; weak 4-voxel hits inside the envelope then turned its zone vote into a STOP. With far
    evidence and no approach it stays advisory."""
    tr = Tracker(_cfg())
    for _ in range(8):                        # advisory: normal hits outside the strict envelope
        tr.update([_cl(96.8, thin=False, zone="warning")], ego_shift=0.0, frame_dt=0.1, far_thin=[])
    t = tr.tracks[0]
    assert t.reported and t.zone == "warning"
    for _ in range(12):                       # weak hits inside, alternating with normal ones inside
        cl = _cl(96.8, thin=False, n_gauge=4)
        cl.weak = True
        tr.update([], ego_shift=0.0, frame_dt=0.1, far_thin=[cl])
        tr.update([_cl(96.8, thin=False)], ego_shift=0.0, frame_dt=0.1, far_thin=[])
        assert t.reported and t.zone == "warning"
