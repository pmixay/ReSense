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


@pytest.mark.parametrize("extra", [0.7, 1.5])
def test_a_refinement_while_a_stop_is_confirmed_keeps_it(extra):
    """Ray-cast: a 0.6 m box 30 m ahead, rig rolled 3 deg, the first 5 frames see ``extra`` deg
    more (one canted stretch: the provisional tilt is off by that much). The spaced observations
    (every 3 frames here) refine it at frame 15, while the box has been a STOP since frame 8. The
    STOP is kept on every frame from its first confirmation and ``clear_distance`` is never
    beyond the box. A sub-degree refinement keeps the track model (rotated: its age and the
    floor-shadow reference continue); 1.5 deg re-seeds it but the tracks are kept. On 17a850d
    the 1.5 deg refinement reset the tracker: no STOP on 4 frames."""
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
    frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(5),
                                         specs=[ObstacleSpec(kind="box", size=(0.6, 0.6, 0.6), distance=30.0)])
    cfg = DetectorConfig()
    cfg.calibration.obs_spacing = 3
    det = Detector(cfg)
    true, canted = rot_x(np.radians(3.0)), rot_x(np.radians(3.0 + extra))
    res, changes = [], []
    for k in range(24):
        before = det.mount_rotation.copy()
        age = det.track.age if det.track is not None else -1
        res.append(det.process(Frame(xyz=_remount(frame.xyz, canted if k < 5 else true),
                                     intensity=frame.intensity, stamp=0.1 * k)))
        if not np.allclose(before, det.mount_rotation):
            changes.append((k, det.calib.last_change_deg, age, res[-1].track.age))
    assert [c[0] for c in changes][0] == 4                      # the provisional tilt
    refine = [c for c in changes if c[0] > 4]
    assert len(refine) == 1 and abs(refine[0][1] - extra) < 0.3, changes
    k_ref = refine[0][0]
    first = next(k for k, r in enumerate(res) if r.obstacle)
    assert first < k_ref - 2, (first, k_ref)
    for k in range(first, len(res)):
        r = res[k]
        assert r.obstacle, (k, k_ref, [c[0] for c in changes])
        assert 29.5 < r.nearest_distance < 30.5
        assert r.clear_distance <= r.nearest_distance + 0.1, (k, r.clear_distance)
    if extra < 1.0:
        assert refine[0][3] == refine[0][2] + 1                  # the model was kept, not re-seeded
    assert res[-1].mount["status"] == "provisional" and abs(res[-1].mount["roll_deg"] + 3.0) < 0.3


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
    ``hold_misses`` (1) frame. A track matched again during the hold continues as before."""
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
    assert t.reported and t.misses == 0 and t.hold == 0 and t.hit_fraction == 1.0


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


def test_refinement_on_raw_medians_does_not_flap():
    """The reviewer's flapping: the median roll of the spaced observations hovers around
    apply_min_deg (0.75 deg). Compared after the zeroing below 0.75 every crossing was a jump of
    at least 0.75 deg and re-seeded the track model (4 re-seeds on roundT_doubleT +3 deg pitch).
    With the raw trigger and its hysteresis (the raw median must move refine_min_deg from the one
    behind the applied value) the roll changes once. A median swinging by the full deadband
    (0.5 deg) still flips it on every swing with one observation; the two in a row that
    ``refine_confirm_obs`` asks for (shipped) change it once."""
    cfg = DetectorConfig()

    def changes(rolls, raw: bool, confirm: int) -> int:
        c = replace(cfg.calibration, refine_raw_trigger=raw, refine_confirm_obs=confirm)
        return sum(ch for ch, _ in _feed(_calibrator_with_provisional(replace(cfg, calibration=c), 0.0), rolls))

    hover = [0.55, 0.95] * 2 + [0.95] + [0.55, 0.55, 0.95, 0.95] * 2      # median 0.75 +- 0.2
    assert changes(hover, False, 1) == 5
    assert changes(hover, True, 1) == 1 and changes(hover, True, 2) == 1
    swing = [0.5, 1.0, 0.5, 1.0, 1.0, 0.5, 0.5, 1.0, 1.0, 0.5, 0.5, 1.0, 1.0]    # median 0.75 +- 0.25
    assert changes(swing, False, 1) == 5 and changes(swing, True, 1) == 5
    assert changes(swing, True, 2) == 1
    assert (cfg.calibration.refine_raw_trigger, cfg.calibration.refine_confirm_obs) == (True, 2)
    # a real correction (the canted-stretch case: provisional roll 2 deg off) is still made
    cal = _calibrator_with_provisional(cfg, -1.0)
    out = _feed(cal, [-3.0, -3.1, -2.9, -3.0, -3.05, -2.95, -3.0])
    assert sum(ch for ch, _ in out) == 1 and abs(cal.state.roll_deg + 3.0) < 0.1, out


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
