"""Safety review of the round-2 items (26.09): a mount-calibration change must not drop a
confirmed STOP (docs/evidence/results/p3_round2_review_fixes_2026-09-26.json, EXPERIMENTS §1i).

On 17a850d every refinement of the provisional tilt re-seeded the track model from nothing
(``prev=None``): for its warm-up it had no floor-shadow reference and no smoothing, and on
``doubleT_obstacle`` (5 Hz, rig +2 / +2 deg) the fresh bed fit swallowed the object at 56 m, so the
STOP was lost for 2 frames with ``clear_distance`` 151 / 163 m while the object's track was alive;
a change above 1 deg reset the tracker outright. The fixes: the refinement is triggered per axis
by the raw median with a deadband and on two observations in a row
(``calibration.refine_raw_trigger``, ``refine_confirm_obs``); a change of at most 1 deg rotates
the track model instead of re-seeding it (``calibration.reseed_keep_max_deg``); the tracks follow
every change and a reported one is held through it (``tracking.reseed_hold``); ``clear_distance``
is capped at a lost reported track (``health.clear_cap_lost``). Also the input-rate estimate
counts the short in-burst stamp intervals.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from resense.calibration import MountCalibrator, rot_x, rot_y, rot_z
from resense.clustering import Cluster
from resense.config import DetectorConfig
from resense.detector import Candidates, Detector, clear_cap_distance
from resense.frame import Frame
from resense.track import TrackModel, rotate_track_model
from resense.tracking import Tracker


def _remount(xyz: np.ndarray, M: np.ndarray) -> np.ndarray:
    return (xyz @ M.T).astype(np.float32)


@pytest.mark.parametrize("stage", ["final", "refinement"])
@pytest.mark.parametrize("extra", [0.7, 1.5])
def test_a_calibration_change_while_a_stop_is_confirmed_keeps_it(stage, extra):
    """Ray-cast: a 0.6 m box 30 m ahead, rig rolled 3 deg, the first 5 frames see ``extra`` deg
    more (one canted stretch: the provisional tilt is off by that much). The spaced observations
    (every 3 frames here) correct it while the box has been a STOP since frame 8: the final
    calibration (after 7 observations here, frame 18; the shipped defaults) or, with the
    refinement turned on (``refine_min_deg`` 0.5, off since 26.09), the refinement at frame 15.
    The STOP is kept on every frame from its first confirmation and ``clear_distance`` is never
    beyond the box. A sub-degree change keeps the track model (rotated: its age and the
    floor-shadow reference continue); 1.5 deg re-seeds it but the STOP track is kept. On 17a850d
    the 1.5 deg change reset the tracker: no STOP on 4 frames."""
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
    frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(5),
                                         specs=[ObstacleSpec(kind="box", size=(0.6, 0.6, 0.6), distance=30.0)])
    cfg = DetectorConfig()
    cfg.calibration.obs_spacing = 3
    if stage == "final":
        cfg.calibration.frames, cfg.calibration.refine_min_deg = 7, 0.0
    else:
        cfg.calibration.refine_min_deg = 0.5
    det = Detector(cfg)
    true, canted = rot_x(np.radians(3.0)), rot_x(np.radians(3.0 + extra))
    res, changes = [], []
    for k in range(24):
        before = det.mount_rotation.copy()
        age = det.track.age if det.track is not None else -1
        res.append(det.process(Frame(xyz=_remount(frame.xyz, canted if k < 5 else true),
                                     intensity=frame.intensity, stamp=0.1 * k)))
        if not np.allclose(before, det.mount_rotation):
            changes.append((k, det.calib.last_change_deg, age, res[-1].track.age,
                            [t.hold for t in det.tracker.tracks if t.reported and t.zone == "gauge"]))
    assert [c[0] for c in changes][0] == 4                      # the provisional tilt
    later = [c for c in changes if c[0] > 4]
    assert len(later) == 1 and abs(later[0][1] - extra) < 0.3, changes
    k_ch = later[0][0]
    confirm = getattr(cfg.calibration, "refine_confirm_obs", 1)      # 2 since 26.09: one observation later
    assert k_ch == (18 if stage == "final" else 12 + 3 * (confirm - 1))
    first = next(k for k, r in enumerate(res) if r.obstacle)
    assert first < k_ch - 2, (first, k_ch)
    for k in range(first, len(res)):
        r = res[k]
        assert r.obstacle, (k, k_ch, [c[0] for c in changes])
        assert 29.5 < r.nearest_distance < 30.5
        assert r.clear_distance <= r.nearest_distance + 0.1, (k, r.clear_distance)
    if extra < 1.0:
        assert later[0][3] == later[0][2] + 1                    # the model was kept, not re-seeded
    # the STOP's hold window after the change frame: reseed_hold (5) frames, 6 when the model is
    # re-seeded at 10 Hz (its warm-up without a floor-shadow reference); 0 on 10e2707 (a match ended it)
    assert later[0][4] == [(5 if extra < 1.0 else 6) - 1], later
    assert res[-1].mount["status"] == ("ok" if stage == "final" else "provisional")
    assert abs(res[-1].mount["roll_deg"] + 3.0) < 0.3


def test_rotate_track_model_is_the_same_bed_and_axis():
    """``rotate_track_model``: the bed profile and the axis of a model, rotated by a sub-degree
    change of the correction, pass through the rotated points of the old ones (1 mm), and the
    state the next frame reads (age, rail offset, floor-shadow run) is kept."""
    m = TrackModel(floor_coef=np.array([2e-5, 0.012, -1.62]), floor_range=(4.0, 87.5), center=0.31,
                   yaw=0.004, curvature=2e-4, rail_offset=0.17, age=37, floor_hold_run=2)
    dR = rot_z(np.radians(0.1)) @ rot_y(np.radians(-0.6)) @ rot_x(np.radians(0.45))
    r = rotate_track_model(m, dR)
    X = np.linspace(5.0, 85.0, 30)
    bed = np.stack([X, m.center_y(X), m.floor_z(X)], 1) @ dR.T
    assert np.max(np.abs(r.floor_z(bed[:, 0]) - bed[:, 2])) < 1e-3
    axis = np.stack([X, m.center_y(X), m.rail_z(X)], 1) @ dR.T
    assert np.max(np.abs(r.center_y(axis[:, 0]) - axis[:, 1])) < 1e-3
    assert (r.age, r.rail_offset, r.floor_hold_run) == (37, 0.17, 2)
    same = rotate_track_model(m, np.eye(3))
    assert np.allclose(same.floor_coef, m.floor_coef, atol=1e-9) and abs(same.center - m.center) < 1e-9


def _cluster(x: float, zone: str = "gauge", reason: str = "", lateral: float = 0.0, n_gauge: int = 5) -> Cluster:
    c = np.array([x + 0.2, lateral, -1.0])
    return Cluster(points_idx=np.arange(3), n=8, n_raw=20, centroid=c, bbox_min=c - 0.25, bbox_max=c + 0.25,
                   distance=x, lateral=lateral, height_min=0.1, height_max=0.6, intensity=20.0,
                   n_expected=8.0, score=1.0, zone=zone, n_gauge=n_gauge, reason=reason)


def _reported_tracker(cfg: DetectorConfig) -> Tracker:
    tr = Tracker(cfg.tracking)
    for _ in range(6):
        tr.update([_cluster(40.0)], frame_dt=0.1)
    assert [t.reported for t in tr.tracks] == [True]
    return tr


def test_reseed_hold_is_bounded_and_not_extended():
    """``tracking.reseed_hold``: a track reported at a calibration change stays reported without a
    match for 5 frames after its last match (its confidence and hit history untouched), then goes;
    re-seeding every frame does not extend that. Without the hold it goes after
    ``hold_misses`` (1) frame. A track matched again during the hold continues as before, its
    window not ended by the match (re-review 26.09)."""
    cfg = DetectorConfig()
    for every_frame in (False, True):
        tr = _reported_tracker(cfg)
        conf = tr.tracks[0].confidence
        tr.reseed(np.eye(3), cfg.tracking.reseed_hold)
        reported = []
        for _ in range(8):
            tr.update([], frame_dt=0.1)
            reported.append(bool(tr.tracks and tr.tracks[0].reported))
            if tr.tracks:
                assert tr.tracks[0].confidence == conf
            if every_frame:
                tr.reseed(np.eye(3), cfg.tracking.reseed_hold)
        assert reported == [True] * 5 + [False] * 3, (every_frame, reported)
    tr = _reported_tracker(cfg)
    tr.reseed(rot_y(np.radians(0.5)), 0)
    tr.update([], frame_dt=0.1)
    tr.update([], frame_dt=0.1)
    assert not any(t.reported for t in tr.tracks)
    tr = _reported_tracker(cfg)
    tr.reseed(np.eye(3), cfg.tracking.reseed_hold)
    for _ in range(3):
        tr.update([], frame_dt=0.1)
    tr.update([_cluster(40.0)], frame_dt=0.1)
    (t,) = tr.tracks
    assert t.reported and t.misses == 0 and t.hold == 1 and t.hit_fraction == 1.0


def test_reseed_hold_is_a_window_a_match_does_not_end():
    """Re-review of 26.09: a match on the change frame ended the hold, so a STOP whose object the
    re-seeded model loses from the next frame on stayed reported one frame more only
    (``hold_misses``; the reviewer's [T, F, F, F, F] on 10e2707). The hold is a fixed window from
    the change, the change frame the first: matched on the change frame and then missed for 4
    frames the STOP is reported on all 4, as when it is missed from the change frame on, with its
    confidence untouched, and goes after the window. A 6-frame window (a re-seeded model at
    10 Hz) holds one frame more."""
    cfg = DetectorConfig()
    for matched_on_change in (False, True):
        tr = _reported_tracker(cfg)
        tr.reseed(np.eye(3), cfg.tracking.reseed_hold)
        tr.update([_cluster(40.0)] if matched_on_change else [], frame_dt=0.1)     # the change frame
        assert [t.reported for t in tr.tracks] == [True]
        conf = tr.tracks[0].confidence
        reported, confs = [], []
        for _ in range(5):
            tr.update([], frame_dt=0.1)
            reported.append(bool(tr.tracks and tr.tracks[0].reported))
            confs.append(tr.tracks[0].confidence if tr.tracks else None)
        assert reported == [True] * 4 + [False], (matched_on_change, reported)
        assert confs[:4] == [conf] * 4
    tr = _reported_tracker(cfg)
    tr.reseed(np.eye(3), 6)
    tr.update([_cluster(40.0)], frame_dt=0.1)
    assert [any(t.reported for t in tr.update([], frame_dt=0.1)) for _ in range(6)] == [True] * 5 + [False]


@pytest.mark.parametrize("dist", [30.0, 50.0])
@pytest.mark.parametrize("rig,extra", [(3.0, 0.7), (3.0, -0.7), (3.0, 0.95), (3.5, -0.7)])
@pytest.mark.parametrize("axis", ["roll", "pitch"])
def test_a_calibration_change_keeps_the_stop_track_matched(axis, rig, extra, dist):
    """Re-review of 26.09: nothing guarded the sign of the rotation ``dR`` in
    ``Detector._fit_track`` (the track model and the tracks): transposed, or not applied, every
    test passed because the hold kept the STOP reported. Ray-cast, the reviewer's scenario: a
    0.6 m box at 30 / 50 m, the rig at ``rig`` deg roll or pitch, the first 5 frames ``extra`` deg
    more; the final calibration corrects the provisional tilt at frame 18 by less than 1 deg (the
    model rotated, not re-seeded; with the rig at 3 deg and -0.7 the canted 2.3 deg is mostly
    below provisional_min_deg, so the final is a ~3 deg change that re-seeds the model, hence the
    3.5 deg rig). From its first STOP the box is a STOP on every frame and its track is MATCHED on
    every frame, not held. With ``dR`` transposed every pitch case fails, without the rotation the
    50 m pitch cases (a roll of the rig barely moves a box on the axis)."""
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
    frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(5),
                                         specs=[ObstacleSpec(kind="box", size=(0.6, 0.6, 0.6), distance=dist)])
    cfg = DetectorConfig()
    cfg.calibration.obs_spacing, cfg.calibration.frames = 3, 7
    rot = rot_x if axis == "roll" else rot_y
    true, canted = rot(np.radians(rig)), rot(np.radians(rig + extra))
    det = Detector(cfg)
    changes, first = [], None
    for k in range(26):
        before = det.mount_rotation.copy()
        age = det.track.age if det.track is not None else -1
        r = det.process(Frame(xyz=_remount(frame.xyz, canted if k < 5 else true),
                              intensity=frame.intensity, stamp=0.1 * k))
        if not np.allclose(before, det.mount_rotation):
            changes.append((k, det.calib.last_change_deg, r.track.age - age))
        if first is None and r.obstacle:
            first = k
        if first is not None:
            tracks = {t.id: t for t in det.tracker.tracks}
            assert r.obstacle and all(tracks[d.id].misses == 0 for d in r.detections), (k, changes)
            assert abs(r.nearest_distance - dist) < 0.5, (k, r.nearest_distance)
    assert [c[0] for c in changes][-1] == 18 and first < 16, changes
    if rig + extra >= 2.5:                                  # the provisional tilt, then a sub-degree final
        assert changes[0][0] == 4 and len(changes) == 2, changes
        assert abs(changes[1][1] - abs(extra)) < 0.3 and changes[1][1] <= 1.0 and changes[1][2] == 1, changes


def test_reseed_rotates_the_tracks_and_a_large_change_drops_only_unreported_ones():
    """The tracks follow the correction (a 3 deg pitch change moves a track at 40 m by 2 m in
    height: out of the association gate if left where it was); above 1 deg the tracks not reported
    are dropped as the tracker reset did, the reported one is kept."""
    cfg = DetectorConfig()
    tr = _reported_tracker(cfg)
    tr.update([_cluster(40.0), _cluster(20.0, lateral=0.5)], frame_dt=0.1)
    assert [t.reported for t in tr.tracks] == [True, False]
    dR = rot_y(np.radians(3.0))
    c0 = tr.tracks[0].centroid.copy()
    tr.reseed(dR, 5, keep_unreported=False)
    assert len(tr.tracks) == 1 and np.allclose(tr.tracks[0].centroid, dR @ c0)
    moved = _cluster(40.0)
    moved.centroid = dR @ moved.centroid
    tr.update([moved], frame_dt=0.1)
    assert tr.tracks[0].misses == 0 and tr.tracks[0].reported


def test_an_advisory_track_is_neither_held_nor_kept_through_a_large_change():
    """doubleT_obstacle at 5 Hz (candidate C1 of the review): the object was reported as ADVISORY
    under the 3 deg tilt before the provisional correction; kept with that zone history, its
    vote stayed advisory 3 frames after the correction (first STOP frame 12 -> 18). Only a STOP
    (reported in zone gauge) is held, and on a change above 1 deg only STOPs are kept; on a
    sub-degree change every track stays (unrotated history, as before), an advisory one unheld."""
    cfg = DetectorConfig()
    tr = Tracker(cfg.tracking)
    for _ in range(6):
        tr.update([_cluster(40.0, zone="warning")], frame_dt=0.1)
    assert [(t.reported, t.zone) for t in tr.tracks] == [(True, "warning")]
    tr.reseed(rot_x(np.radians(0.6)), cfg.tracking.reseed_hold, keep_unreported=True)
    assert len(tr.tracks) == 1 and tr.tracks[0].hold == 0
    tr.reseed(rot_x(np.radians(3.0)), cfg.tracking.reseed_hold, keep_unreported=False)
    assert tr.tracks == []


def test_clear_cap_at_a_lost_reported_track():
    """``health.clear_cap_lost``: a track reported when it was last matched that misses this frame
    caps the verified-clear distance at its predicted distance until the tracker drops it (the
    reviewer's frames 102 / 104: 151 / 163 m with the object's track alive at 56.4 m); without
    the rule, or for a track never reported, nothing caps."""
    cfg = DetectorConfig()
    tr = _reported_tracker(cfg)
    empty = Candidates(xyz=np.zeros((0, 3), np.float32), dy=np.zeros(0), h=np.zeros(0), in_gauge=np.zeros(0, bool),
                       intensity=np.zeros(0, np.float32), idx=np.zeros(0, np.int64), low=np.zeros(0, bool))
    caps = []
    for _ in range(cfg.tracking.max_misses + 1):
        tr.update([], frame_dt=0.1)
        caps.append(clear_cap_distance([], tr.tracks, empty, np.zeros(0), np.zeros(0), cfg.gauge, cfg.health))
    assert caps[:cfg.tracking.max_misses] == [pytest.approx(40.0)] * cfg.tracking.max_misses
    assert caps[-1] is None                                     # dropped by the tracker
    tr = _reported_tracker(cfg)
    tr.update([], frame_dt=0.1)
    tr.update([], frame_dt=0.1)
    off = replace(cfg.health, clear_cap_lost=False)
    assert clear_cap_distance([], tr.tracks, empty, np.zeros(0), np.zeros(0), cfg.gauge, off) is None
    young = Tracker(cfg.tracking)
    young.update([_cluster(40.0)], frame_dt=0.1)
    young.update([], frame_dt=0.1)
    assert clear_cap_distance([], young.tracks, empty, np.zeros(0), np.zeros(0), cfg.gauge, cfg.health) is None


def _calibrator_with_provisional(cfg: DetectorConfig, roll_deg: float) -> MountCalibrator:
    cal = MountCalibrator(cfg.calibration, cfg.track)
    cal.state.status = "provisional"
    cal._provisional_done = True
    cal._set_tilt(np.radians(roll_deg), np.radians(3.0), 0.0)
    return cal


def _feed(cal: MountCalibrator, rolls) -> list:
    """Spaced observations with these roll values (pitch 3 deg): the refinement after each."""
    out = []
    for r in rolls:
        cal._obs.append((np.radians(r), np.radians(3.0), float("nan"), 1.5, 0.0))
        out.append((cal._refine(), round(cal.state.roll_deg, 2)))
    return out


def test_refinement_does_not_flap():
    """The reviewer's flapping: the median roll of the spaced observations hovers around
    apply_min_deg (0.75 deg). Compared after the zeroing below 0.75 every crossing was a jump of
    at least 0.75 deg and re-seeded the track model (4 re-seeds on roundT_doubleT +3 deg pitch;
    here 5 changes). The refinement is off since the review; turned on (refine_min_deg 0.5) the
    condition must hold on two spaced observations in a row and at most one refinement is made -
    one change. The opt-in raw
    trigger (tried, not shipped) makes one change on a median hovering by 0.2 deg but still
    flaps on one swinging by its whole 0.5 deg deadband."""
    cfg = DetectorConfig()

    def changes(rolls, **kw) -> int:
        c = replace(cfg.calibration, **{"refine_min_deg": 0.5, **kw})
        return sum(ch for ch, _ in _feed(_calibrator_with_provisional(replace(cfg, calibration=c), 0.0), rolls))

    old = dict(refine_confirm_obs=1, refine_max=0)
    hover = [0.55, 0.95] * 2 + [0.95] + [0.55, 0.55, 0.95, 0.95] * 2      # median 0.75 +- 0.2
    swing = [0.5, 1.0, 0.5, 1.0, 1.0, 0.5, 0.5, 1.0, 1.0, 0.5, 0.5, 1.0, 1.0]    # median 0.75 +- 0.25
    assert changes(hover, **old) == 5 and changes(swing, **old) == 5
    assert changes(hover) == 1 and changes(swing) == 1
    assert changes(hover, refine_max=0) == 1 and changes(swing, refine_confirm_obs=1) == 1     # each rule alone
    assert changes(hover, refine_raw_trigger=True, **old) == 1
    assert changes(swing, refine_raw_trigger=True, **old) == 5
    c = cfg.calibration
    assert (c.refine_raw_trigger, c.refine_confirm_obs, c.refine_max, c.refine_min_deg) == (False, 2, 1, 0.0)
    # a real correction (the canted-stretch case: provisional roll 2 deg off) is still made, on
    # the second observation that says so
    cal = _calibrator_with_provisional(replace(cfg, calibration=replace(cfg.calibration, refine_min_deg=0.5)), -1.0)
    out = _feed(cal, [-3.0, -3.1, -2.9, -3.0, -3.05, -2.95, -3.0])
    assert [ch for ch, _ in out] == [False] * 5 + [True, False] and abs(cal.state.roll_deg + 3.0) < 0.1, out


def _periods(stamps) -> list:
    det = Detector(DetectorConfig())
    out = []
    for s in stamps:
        det._frame_dt(s)
        out.append(det._periods())
    return out


def test_input_rate_is_one_period_for_bursty_10hz_stamps():
    """Recorded receive stamps come in bursts. The median of the last 9 intervals without the ones
    under 0.02 s read alternating 0.19 / 0.01 s intervals as 2 periods and 0.29 / 0.005 / 0.005 s
    as 3 (the track model's rate limits and the calibration cadence then counted double). The mean
    of the last 14 intervals is 1 on every frame; 5 Hz is 2, a 5 s pause and a step back of the
    stamps do not enter it."""
    assert _periods(np.cumsum(np.tile([0.19, 0.01], 30)))[1:] == [1] * 59
    assert _periods(np.cumsum(np.tile([0.29, 0.005, 0.005], 20)))[1:] == [1] * 59
    assert _periods(np.cumsum(0.1 + np.random.default_rng(0).uniform(-0.03, 0.03, 60))) == [1] * 60
    assert _periods(np.arange(40) * 0.2)[1:] == [2] * 39
    pause = np.concatenate([np.arange(20) * 0.1, 7.0 + np.arange(20) * 0.1])
    assert _periods(pause) == [1] * 40
    back = np.concatenate([np.arange(20) * 0.1, np.arange(20) * 0.1])
    assert _periods(back) == [1] * 40
    assert _periods([0.0]) == [1]
