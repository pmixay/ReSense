"""Sprint 2 algorithm tests (P3): ego speed, multi-frame accumulation, verified bed
extrapolation, retro-reflector filter. Everything runs on the synthetic ray-cast tunnel
with fixed seeds; no dataset needed. Timings printed here are for the machine that runs
the suite (the 4-core sandbox is slower than the jury's i7-9700E)."""
from pathlib import Path

import numpy as np
import pytest

from resense import Detector, DetectorConfig
from resense.accumulate import CandidateBuffer
from resense.egomotion import BIN, correlate_lags, normalise_profile, peak_lag
from resense.track import TrackModel, verify_floor_extrapolation

o3d = pytest.importorskip("open3d", reason="open3d needed for the synthetic tunnel")
from resense.synthetic import ObstacleSpec, inject_obstacles, synthetic_tunnel_frame  # noqa: E402

PERSON = (0.4, 0.5, 1.7)
BOX = (0.5, 0.5, 0.5)
STEP = 2.2                      # m per frame = 22 m/s at 10 Hz
EGO = 22.0
# the injector's default dropout (120 -> 260 m) is optimistic against the budget measured on
# real frames (EXPERIMENTS.md section 2: 3-5 returns from a person at 150-190 m, 0-1 beyond
# 200 m); this setting reproduces that budget on the synthetic tunnel (2-5 returns at 185-200 m)
DROPOUT = dict(dropout_start=60.0, dropout_full=200.0)


@pytest.fixture(scope="module")
def tunnel():
    return synthetic_tunnel_frame(rng=np.random.default_rng(1))


def approach(tunnel, d0, n, kind="person", size=PERSON, refl=60, seed=0, lateral=0.0, dropout=DROPOUT):
    """Frames with the object injected at d0, d0 - 2.2, ... into the same background."""
    frame, _, gt = tunnel
    for k in range(n):
        d = d0 - STEP * k
        spec = ObstacleSpec(kind=kind, size=size, distance=d, lateral=lateral, reflectivity=refl)
        inj = inject_obstacles(frame, gt, [spec], rng=np.random.default_rng(1000 * seed + k), **dropout)
        yield d, inj.frame


def first_alarm(det, frames, speed):
    """(frame index, truth distance, result) of the first obstacle, or None."""
    for k, (d, fr) in enumerate(frames):
        res = det.process(fr, ego_speed=speed)
        if res.obstacle:
            return k, d, res
    return None


def acc_cfg(estimate=False):
    """Defaults (accumulation is on, merging only with a given speed; v0.5 ships the LiDAR-only
    estimator off, EXPERIMENTS.md 1b); ``estimate`` switches the ego-speed estimator on."""
    cfg = DetectorConfig()
    cfg.accumulation.enabled = True
    cfg.accumulation.estimate_speed = bool(estimate)
    return cfg


# ---------------------------------------------------------------------------
# configuration and result contract
# ---------------------------------------------------------------------------

def test_config_new_sections_round_trip():
    cfg = DetectorConfig()
    back = DetectorConfig.from_dict(cfg.to_dict())
    assert back.to_dict() == cfg.to_dict()
    assert cfg.accumulation.enabled and not cfg.accumulation.estimate_speed and cfg.accumulation.n_frames == 5   # v0.5: merge only with a given speed
    assert cfg.cluster.retro_intensity == 0.0           # v0.5: retro rule off by default (EXPERIMENTS.md 1b, 2c)
    with pytest.raises(KeyError):
        DetectorConfig.from_dict({"accumulation": {"n_frame": 5}})
    yaml_cfg = DetectorConfig.from_yaml(str(Path(__file__).resolve().parents[1] / "configs" / "default.yaml"))
    assert yaml_cfg.to_dict() == cfg.to_dict(), "configs/default.yaml drifted from the dataclass defaults"


def test_result_dict_keeps_old_keys_and_adds_ego_keys(tunnel):
    frame, _, _ = tunnel
    res = Detector(DetectorConfig()).process(frame, ego_speed=EGO)
    d = res.to_dict()
    for k in ("stamp", "obstacle", "warning", "nearest_distance", "detections", "warnings", "n_candidates",
              "n_points", "n_corridor", "track", "timing_ms"):
        assert k in d
    assert d["ego_speed"] == 22.0 and d["ego_speed_source"] == "given" and d["n_accumulated"] == 1
    assert "ego_speed_estimate" in d and "ego_speed_confidence" in d
    assert "floor_verified" in d["track"]
    assert set(d["timing_ms"]) >= {"track", "corridor", "egomotion", "accumulate", "cluster", "tracking", "total"}
    res2 = Detector(DetectorConfig()).process(frame)          # the old call signature still works
    assert res2.ego_speed is None and res2.ego_speed_source == "none"


# ---------------------------------------------------------------------------
# candidate buffer
# ---------------------------------------------------------------------------

def test_candidate_buffer_shift_merge_and_cap():
    buf = CandidateBuffer(n_frames=3, max_points=4)
    assert buf.merged() is None
    X = np.arange(10, dtype=np.float32) * 10.0 + 45.0        # 45 .. 135 m, 10 points -> capped to 4
    z = np.zeros(10, np.float32)
    buf.push(X, z, z, z, np.ones(10, bool))
    assert len(buf) == 1 and buf.merged()[0].size == 4
    buf.shift(2.2)
    buf.push(X[:2], z[:2], z[:2], z[:2], np.ones(2, bool))
    buf.shift(2.2)
    Xm, dym, hm, im, gm = buf.merged(min_range=40.0)
    assert len(buf) == 2 and Xm.size == 6
    assert np.isclose(Xm.min(), 45.0 - 4.4, atol=1e-4)       # the oldest frame moved twice
    assert np.isclose(np.sort(Xm)[1], 45.0 - 2.2, atol=1e-4)  # the newer one once
    buf.push(X[:1], z[:1], z[:1], z[:1], np.ones(1, bool))    # ring: only n_frames - 1 = 2 kept
    assert len(buf) == 2
    assert buf.merged(min_range=200.0) is None
    none = CandidateBuffer(n_frames=1)
    none.push(X, z, z, z, np.ones(10, bool))
    assert len(none) == 0


# ---------------------------------------------------------------------------
# verified bed extrapolation (second height anchor)
# ---------------------------------------------------------------------------

def test_floor_verification_extends_trusted_corridor(tunnel):
    frame, _, _ = tunnel
    cfg = DetectorConfig()
    det = Detector(cfg)
    res = det.process(frame, ego_speed=EGO)
    fit_end = res.track.floor_range[1]
    assert fit_end < 130.0                                    # the bed fit itself stops early
    assert res.track.floor_verified >= 180.0, res.track.to_dict()
    assert res.track.floor_verified > fit_end + cfg.track.floor_valid_margin
    cfg2 = DetectorConfig()
    cfg2.track.floor_verify_enabled = False
    res2 = Detector(cfg2).process(frame, ego_speed=EGO)
    assert res2.track.floor_verified == pytest.approx(res2.track.floor_range[1])


def _side_scene(bend_radius=None):
    """Hand-made cloud: flat bed to 100 m, wall foot on both sides to 250 m that follows a
    vertical curve of ``bend_radius`` beyond 120 m (None = straight)."""
    rng = np.random.default_rng(3)
    X = rng.uniform(3.0, 100.0, 6000)
    bed = np.stack([X, rng.uniform(-0.8, 0.8, X.size), -1.5 + rng.normal(0, 0.01, X.size)], 1)
    Xw = rng.uniform(3.0, 250.0, 20000)
    z_foot = -1.5 + np.where(Xw > 120.0, 0.0 if bend_radius is None else (Xw - 120.0) ** 2 / (2 * bend_radius), 0.0)
    wall = np.stack([Xw, np.where(rng.random(Xw.size) < 0.5, 1.0, -1.0) * rng.uniform(2.0, 2.8, Xw.size),
                     z_foot + rng.uniform(0.0, 1.5, Xw.size) ** 2], 1)
    return np.concatenate([bed, wall]).astype(np.float32)


def test_floor_verification_stops_at_a_vertical_curve():
    model = TrackModel(floor_coef=np.array([0.0, 0.0, -1.5]), floor_range=(3.0, 100.0), center=0.0, yaw=0.0,
                       curvature=0.0, rail_offset=0.35)
    cfg = DetectorConfig().track
    straight = verify_floor_extrapolation(_side_scene(None), model, cfg)
    curved = verify_floor_extrapolation(_side_scene(1500.0), model, cfg)
    assert straight >= 240.0
    # 1500 m vertical curve from 120 m: 0.5 m off at 159 m, 1.2 m at 180 m; the 30 m window
    # median lets the verification run to ~180 m and no further
    assert 150.0 <= curved <= 195.0, curved


# ---------------------------------------------------------------------------
# multi-frame accumulation with a given ego speed
# ---------------------------------------------------------------------------

def test_accumulation_confirms_person_within_8_frames_from_200m(tunnel):
    cfg = acc_cfg()
    det = Detector(cfg)
    hit = first_alarm(det, approach(tunnel, 200.0, 8), EGO)
    assert hit is not None, "person approaching from 200 m not confirmed within 8 frames"
    k, d, res = hit
    assert abs(res.nearest_distance - d) <= max(3.0, 0.03 * d), (res.nearest_distance, d)
    assert res.n_accumulated > 1 and res.ego_speed_source == "given"
    assert res.detections[0].size[0] < 1.5, "accumulated person is smeared along the track"
    print("\n[synthetic] accumulation on: person confirmed at frame %d, truth %.1f m, reported %.1f m, %d frames merged"
          % (k, d, res.nearest_distance, res.n_accumulated))


def test_single_frame_confirms_later_than_accumulation(tunnel):
    """Documents the gain. With the real-frame point budget the single-frame detector needs
    3 consecutive frames with >= 3 returns and confirms the seed-0 sequence at 178 m (167-189 m
    over seeds); accumulation confirms it at 189-191 m in every seed."""
    on = acc_cfg()
    off = DetectorConfig()
    off.accumulation.enabled = False
    hit_on = first_alarm(Detector(on), approach(tunnel, 200.0, 20), EGO)
    hit_off = first_alarm(Detector(off), approach(tunnel, 200.0, 20), EGO)
    assert hit_on is not None and hit_off is not None
    assert hit_off[2].n_accumulated == 1
    assert hit_off[0] > hit_on[0], (hit_on[:2], hit_off[:2])
    assert hit_off[1] < 185.0, "single-frame confirmed above 185 m: the synthetic budget is too generous"
    print("\n[synthetic] first confirmed: accumulation %.1f m (frame %d) vs single frame %.1f m (frame %d)"
          % (hit_on[1], hit_on[0], hit_off[1], hit_off[0]))


def test_box_05m_confirmed_beyond_100m(tunnel):
    hit = first_alarm(Detector(acc_cfg()), approach(tunnel, 140.0, 20, kind="box", size=BOX), EGO)
    assert hit is not None and hit[1] >= 100.0, hit and hit[:2]
    assert abs(hit[2].nearest_distance - hit[1]) <= max(2.0, 0.03 * hit[1])
    print("\n[synthetic] box 0.5 m confirmed at truth %.1f m (frame %d)" % (hit[1], hit[0]))


def test_clear_tunnel_with_accumulation_stays_clear(tunnel):
    frame, _, _ = tunnel
    det = Detector(acc_cfg())
    for _ in range(10):
        res = det.process(frame, ego_speed=EGO)
        assert not res.obstacle and not res.warning, [d.to_dict() for d in res.detections + res.warnings]


def test_near_object_not_smeared_by_accumulation(tunnel):
    # approaching box crosses the accumulation boundary (40 m): distance and length stay right
    det = Detector(acc_cfg())
    for d, fr in approach(tunnel, 45.0, 8, kind="box", size=(0.6, 0.6, 0.6), dropout={}):
        res = det.process(fr, ego_speed=EGO)
        if res.obstacle:
            assert abs(res.nearest_distance - d) < 1.0, (res.nearest_distance, d)
            assert res.detections[0].size[0] < 1.0
    assert res.obstacle and res.nearest_distance == pytest.approx(29.6, abs=1.0)
    # static person at 60 m, train stopped (given 0 m/s): v0.5 merges nothing below
    # accumulation.min_speed (identical frames add no density but the scaled thresholds lose
    # marginal objects, P4 static sets 21.09); the object is confirmed from single frames
    frame, _, gt = tunnel
    inj = inject_obstacles(frame, gt, [ObstacleSpec(kind="person", size=PERSON, distance=60.0, lateral=0.0, reflectivity=60)],
                           rng=np.random.default_rng(3))
    det = Detector(acc_cfg())
    for _ in range(6):
        res = det.process(inj.frame, ego_speed=0.0)
    assert res.obstacle and res.n_accumulated == 1 and res.ego_speed_source == "given"
    assert abs(res.nearest_distance - 60.0) < 1.0 and res.detections[0].size[0] < 1.0
    assert res.detections[0].n_points < 80                    # 56 voxels single-frame
    # crawling (2 m/s given): the 5 frames are merged and still land on the same voxels
    det = Detector(acc_cfg())
    for _ in range(6):
        res = det.process(inj.frame, ego_speed=2.0)
    assert res.obstacle and res.n_accumulated == 5 and res.detections[0].size[0] < 1.5


def test_wrong_given_speed_degrades_to_single_frame(tunnel):
    """Smear guard: with the speed 8 m/s off, the merged cluster stretches along X and is
    re-described from the current frame; the object is kept and its distance stays within
    tolerance (biased towards the vehicle by at most smear_max_length)."""
    det = Detector(acc_cfg())
    confirmed = 0
    for d, fr in approach(tunnel, 100.0, 8, dropout={}):
        res = det.process(fr, ego_speed=30.0)
        if res.obstacle:
            confirmed += 1
            assert abs(res.nearest_distance - d) <= max(3.0, 0.03 * d), (res.nearest_distance, d)
            assert res.detections[0].size[0] <= 2.5
    assert confirmed >= 4


def test_timing_with_accumulation(tunnel):
    det = Detector(acc_cfg())
    totals = []
    for d, fr in approach(tunnel, 200.0, 20, seed=5):
        res = det.process(fr, ego_speed=EGO)
        totals.append(res.timing_ms["total"])
    totals = np.array(totals[1:])                              # the first frame warms caches
    mean, p95 = totals.mean(), np.percentile(totals, 95)
    print("\n[synthetic, this machine] detector with accumulation: mean %.1f ms, p95 %.1f ms, max %.1f ms over %d frames; last frame stages: %s"
          % (mean, p95, totals.max(), totals.size, {k: round(v, 1) for k, v in res.timing_ms.items()}))
    assert p95 < 150.0


# ---------------------------------------------------------------------------
# ego-speed estimation
# ---------------------------------------------------------------------------

def test_profile_correlation_recovers_a_known_shift():
    rng = np.random.default_rng(0)
    nb = 210
    tex = np.zeros(nb)
    tex[rng.choice(nb, 12, replace=False)] = rng.uniform(5, 40, 12)   # sparse spikes = brackets
    base = 20.0 + rng.normal(0, 1.0, nb)
    lag = 22                                                          # 2.2 m = 22 m/s at 10 Hz
    prev_counts = base + tex
    cur_counts = base + np.concatenate([tex[lag:], np.zeros(lag)])    # texture slid towards the vehicle
    prev, cur = normalise_profile(prev_counts), normalise_profile(cur_counts)
    c = correlate_lags(prev, cur, 30)
    got, corr, prom = peak_lag(c)
    assert abs(got - lag) < 0.6 and corr > 0.6 and corr * min(prom / 0.3, 1.0) > 0.5
    assert abs(got * BIN / 0.1 - 22.0) < 0.6
    # noise only: no usable peak
    c0 = correlate_lags(normalise_profile(base), normalise_profile(20.0 + rng.normal(0, 1.0, nb)), 30)
    _, corr0, prom0 = peak_lag(c0)
    assert corr0 * min(prom0 / 0.3, 1.0) < 0.5


def _posts(rng):
    posts, x = [], 3.0
    while x < 260.0:
        posts.append((x, (1.0 if rng.random() < 0.5 else -1.0) * 2.3))
        x += rng.uniform(3.0, 9.0)
    return posts


def _textured_scene(posts, shift, person_d=None, seed=0):
    specs = [ObstacleSpec(kind="box", size=(0.2, 0.2, 2.5), distance=px - shift, lateral=py, reflectivity=30)
             for px, py in posts if 2.0 < px - shift < 240.0]
    if person_d is not None:
        specs.append(ObstacleSpec(kind="person", size=PERSON, distance=person_d, lateral=0.0, reflectivity=60))
    return synthetic_tunnel_frame(rng=np.random.default_rng(seed), specs=specs)[0]


def test_estimator_finds_ego_speed_on_a_textured_moving_tunnel():
    """Posts on both walls, the whole scene (and a person from 200 m) moves 2.2 m per frame:
    the texture cue must report ~22 m/s with no speed given, and accumulation must run."""
    posts = _posts(np.random.default_rng(7))
    det = Detector(acc_cfg(estimate=True))
    speeds = []
    hit = None
    for k in range(11):
        shift = EGO * 0.1 * k
        res = det.process(_textured_scene(posts, shift, 200.0 - shift, seed=100 + k), ego_speed=None)
        speeds.append((res.ego_speed_source, res.ego_speed))
        if res.obstacle and hit is None:
            hit = (k, 200.0 - shift, res.nearest_distance, res.n_accumulated)
    estimated = [v for s, v in speeds[4:] if s == "estimated"]
    assert len(estimated) >= 5, speeds
    assert all(abs(v - EGO) < 2.0 for v in estimated), speeds
    assert hit is not None and hit[1] >= 170.0 and abs(hit[2] - hit[1]) <= max(3.0, 0.03 * hit[1]), hit
    print("\n[synthetic, textured] estimated speeds %s; person confirmed at truth %.1f m, frame %d, %d frames merged"
          % ([round(v, 1) for v in estimated], hit[1], hit[0], hit[3]))


def test_estimator_reports_unknown_when_nothing_moves():
    """A stopped train in front of the same posts, and a featureless tunnel with fresh noise:
    nothing moves, so the honest answer is 'unknown' (no accumulation), not a confident 0."""
    posts = _posts(np.random.default_rng(7))
    det = Detector(acc_cfg(estimate=True))
    for k in range(6):
        res = det.process(_textured_scene(posts, 0.0, None, seed=300 + k), ego_speed=None)
        assert res.ego_speed_source == "none" and res.n_accumulated == 1, res.to_dict()
        assert not res.obstacle
    det = Detector(acc_cfg(estimate=True))
    for k in range(5):
        res = det.process(synthetic_tunnel_frame(rng=np.random.default_rng(400 + k))[0], ego_speed=None)
        assert res.ego_speed_source == "none" and res.ego_speed_confidence < 0.5
        assert not res.obstacle and not res.warning


def test_unknown_speed_never_smears_the_moving_person(tunnel):
    """The emulated sequence moves only the object, the background is one frame: the
    estimator sees nothing moving, reports 'unknown', and the detector falls back to single
    frames instead of merging unshifted frames (which would stretch the person to 8.8 m)."""
    det = Detector(acc_cfg(estimate=True))
    hit = first_alarm(det, approach(tunnel, 200.0, 20), None)
    assert hit is not None
    k, d, res = hit
    assert res.ego_speed_source == "none" and res.n_accumulated == 1
    assert abs(res.nearest_distance - d) <= max(3.0, 0.03 * d) and res.detections[0].size[0] < 1.5


# ---------------------------------------------------------------------------
# retro-reflector filter
# ---------------------------------------------------------------------------

def _single(tunnel, kind, size, distance, lateral, refl, speed=0.0):
    frame, _, gt = tunnel
    inj = inject_obstacles(frame, gt, [ObstacleSpec(kind=kind, size=size, distance=distance, lateral=lateral, reflectivity=refl)],
                           rng=np.random.default_rng(5))
    cfg = DetectorConfig()
    cfg.cluster.retro_intensity = 100.0                 # the rule is off by default since v0.5
    det = Detector(cfg)
    for _ in range(cfg.tracking.frames_to_confirm() + 1):
        res = det.process(inj.frame, ego_speed=speed)
    return res


def test_retro_sign_is_advisory_person_is_obstacle(tunnel):
    # a standing sign plate at the corridor edge, reflectivity 220 -> advisory (retro rule)
    sign = _single(tunnel, "box", (0.05, 0.6, 0.8), 40.0, 1.0, 220)
    assert not sign.obstacle and sign.warning, [c.zone for c in sign.candidates]
    assert any(c.retro for c in sign.candidates)
    # the same plate with a matte surface is a real obstacle (control: geometry is identical)
    matte = _single(tunnel, "box", (0.05, 0.6, 0.8), 40.0, 1.0, 60)
    assert matte.obstacle and not any(c.retro for c in matte.candidates)
    # the plank-shaped sign of the spec on the sleepers at the corridor edge: not an obstacle
    plank = _single(tunnel, "plank", (2.0, 0.25, 0.3), 40.0, 1.2, 220)
    assert not plank.obstacle
    # a person at 60 m stays an obstacle whatever the reflectivity (height rule)
    for refl in (15, 60, 200):
        person = _single(tunnel, "person", PERSON, 60.0, 0.0, refl)
        assert person.obstacle and not any(c.retro for c in person.candidates), refl
    # anything wider than a sign keeps its zone even when retro-reflective (a train, a crate)
    crate = _single(tunnel, "box", (1.0, 1.0, 1.0), 60.0, 0.0, 220)
    assert crate.obstacle


def test_retro_rule_is_off_by_default(tunnel):
    frame, _, gt = tunnel
    inj = inject_obstacles(frame, gt, [ObstacleSpec(kind="box", size=(0.05, 0.6, 0.8), distance=40.0, lateral=1.0, reflectivity=220)],
                           rng=np.random.default_rng(5))
    cfg = DetectorConfig()
    assert cfg.cluster.retro_intensity == 0.0
    det = Detector(cfg)
    for _ in range(cfg.tracking.frames_to_confirm() + 1):
        res = det.process(inj.frame, ego_speed=0.0)
    assert res.obstacle


# ---------------------------------------------------------------------------
# v0.5 (real data, 21.09): axis from the rails, persistence in seconds, infrastructure
# signatures, stopped-train and lateral smear guards. All hand-made point sets, no dataset.
# ---------------------------------------------------------------------------

from resense.clustering import Cluster, find_clusters             # noqa: E402
from resense.config import TrackingConfig                         # noqa: E402
from resense.egomotion import EgoSpeedEstimator                   # noqa: E402
from resense.gauge import gauge_core_mask, point_in_polygon, widened_profile  # noqa: E402
from resense.track import estimate_track                          # noqa: E402
from resense.tracking import Track, Tracker                       # noqa: E402


def _curved_scene(R, yaw_deg, seed=0, wall=2.2, right_bend_R=None):
    """Bed, two rail ridges (4-60 m) and two vertical walls following a track of radius R
    (1e9 = straight) with the given yaw at the vehicle; with ``right_bend_R`` the right wall
    bends away to the right with that radius (a diverging tunnel, not parallel to the track)."""
    rng = np.random.default_rng(seed)
    t, kap = np.tan(np.radians(yaw_deg)), 1.0 / R

    def yc(X):
        return -0.1 + t * X + 0.5 * kap * X * X
    parts = []
    X = 3 + 117 * rng.random(40000) ** 0.5
    parts.append(np.stack([X, yc(X) + rng.uniform(-1.2, 1.2, X.size), -1.5 + rng.normal(0, 0.01, X.size)], 1))
    for s in (-1, 1):
        Xr = 3 + 57 * rng.random(12000) ** 0.5
        parts.append(np.stack([Xr, yc(Xr) + s * 0.795 + rng.uniform(-0.03, 0.03, Xr.size),
                               -1.15 + rng.normal(0, 0.005, Xr.size)], 1))
    for s in (-1, 1):
        Xw = rng.uniform(3, 200, 30000)
        off = s * wall
        if s < 0 and right_bend_R:
            off = off - 0.5 * Xw * Xw / right_bend_R
        parts.append(np.stack([Xw, yc(Xw) + off + rng.normal(0, 0.02, Xw.size), rng.uniform(-1.4, 3.3, Xw.size)], 1))
    return np.concatenate(parts).astype(np.float32), yc


def _run_track(xyz, cfg, n=6):
    prev = None
    for _ in range(n):
        prev = estimate_track(xyz, cfg.track, prev=prev)
    return prev


def test_axis_follows_a_curved_track():
    """v0.3 stored the walls' quadratic coefficient (1/2R) as the curvature and applied it as
    1/R: the axis bent half as much as the tunnel (2.4 m off at 100 m on R = 800 m), and the
    rail profile in absolute Y smeared by the yaw over 4-30 m (centre 0.9 m off). v0.5: yaw
    and centre from the rail slabs, curvature 1/R from the walls with the tangent fixed."""
    cfg = DetectorConfig()
    for R, yaw in ((800.0, 1.2), (2000.0, -0.8), (1e9, 0.0)):
        xyz, yc = _curved_scene(R, yaw)
        m = _run_track(xyz, cfg)
        assert abs(np.degrees(m.yaw) - yaw) < 0.15, (R, yaw, np.degrees(m.yaw))
        assert abs(m.curvature - 1.0 / R) < 0.15 / R + 4e-5, (R, m.curvature)   # 4e-5 = the fit's noise floor (0.2 m at 100 m)
        err = max(abs(float(m.center_y(x) - yc(x))) for x in (30.0, 60.0, 100.0))
        assert err < 0.25, (R, yaw, err)
        assert m.rail_slabs >= 2 and m.axis_sides == 2 and m.rail_score > cfg.track.rails_min_score


def test_diverging_wall_cannot_bend_the_axis():
    """Left wall parallel, right wall bending away with R = 600 m (a diverging tunnel): the two
    boundaries disagree, the nearer (parallel) one wins, the axis follows the rails and that
    wall, and the trusted range is capped at ``axis_disagree_range``. A boundary that kinks
    away is simply dropped as outliers by the two-pass fit and does not reach this rule."""
    cfg = DetectorConfig()
    xyz, yc = _curved_scene(1e9, 0.5, right_bend_R=600.0)
    m = _run_track(xyz, cfg)
    assert abs(np.degrees(m.yaw) - 0.5) < 0.2
    assert abs(float(m.center_y(100.0) - yc(100.0))) < 0.4
    assert m.axis_sides == 2 and m.axis_valid <= cfg.track.axis_disagree_range, m.to_dict()
    one, yc1 = _curved_scene(1e9, 0.5, wall=2.2)
    one = one[~((one[:, 1] - yc1(one[:, 0]) < -1.5) & (one[:, 2] > -1.4))]   # no right wall at all: one boundary
    m = _run_track(one, cfg)
    assert m.axis_sides == 1 and m.axis_valid <= cfg.track.axis_one_side_range, m.to_dict()


def test_axis_rate_limits_clip_a_jump():
    cfg = DetectorConfig()
    xyz0, _ = _curved_scene(1e9, 0.0)
    xyz1, _ = _curved_scene(1e9, 2.0, seed=1)
    m = _run_track(xyz0, cfg, cfg.track.axis_warmup_frames + 1)   # past the warm-up (v0.6)
    y0, k0 = m.yaw, m.curvature
    m = estimate_track(xyz1, cfg.track, prev=m)
    assert abs(m.yaw - y0) <= cfg.track.axis_max_yaw_rate + 1e-9
    assert abs(m.curvature - k0) <= cfg.track.axis_max_curvature_rate + 1e-12
    for _ in range(20):
        m = estimate_track(xyz1, cfg.track, prev=m)
    assert abs(np.degrees(m.yaw) - 2.0) < 0.2, "the limit delays, it must not block"


def test_rate_limits_do_not_apply_during_the_warm_up():
    """v0.6: a cold start on a frame whose estimate is off (the node started mid-ride, or the
    model re-seeded after the mount calibration) must not be locked in by the rate limits."""
    cfg = DetectorConfig()
    xyz0, _ = _curved_scene(1e9, 0.0)
    xyz1, _ = _curved_scene(1e9, 2.0, seed=1)
    m = estimate_track(xyz0, cfg.track, prev=None)       # a seed that is 2 deg off
    for _ in range(cfg.track.axis_warmup_frames):
        m = estimate_track(xyz1, cfg.track, prev=m)
    assert abs(np.degrees(m.yaw) - 2.0) < 0.3, np.degrees(m.yaw)


def test_axis_rates_per_period_follow_sensor_time_not_frames():
    """25.09 (SCORECARD #13): at 5 Hz one frame spans two nominal periods. With
    ``rates_per_period`` the yaw / curvature limits and the warm-up count periods, and with
    ``walls_smoothing_per_period`` the yaw / curvature EMA does too: one 5 Hz step then moves
    the axis as far as two 10 Hz steps (per frame it lagged the 10 Hz axis by 0.009 rad in the
    curve of roundT_doubleT, and far structures beside the track entered the gauge). Off, the
    interval is ignored (the 10 Hz behaviour)."""
    xyz0, _ = _curved_scene(1e9, 0.0)
    xyz1, _ = _curved_scene(1e9, 2.0, seed=1)
    for on in (False, True):
        cfg = DetectorConfig()
        cfg.track.rates_per_period = cfg.track.walls_smoothing_per_period = on
        m = _run_track(xyz0, cfg, cfg.track.axis_warmup_frames + 1)
        y0 = m.yaw
        five = estimate_track(xyz1, cfg.track, prev=m, periods=2)
        ten = estimate_track(xyz1, cfg.track, prev=estimate_track(xyz1, cfg.track, prev=m))
        assert abs(ten.yaw - y0) == pytest.approx(2 * cfg.track.axis_max_yaw_rate, abs=1e-9)   # clipped twice
        step = cfg.track.axis_max_yaw_rate * (2 if on else 1)
        assert abs(five.yaw - y0) == pytest.approx(step, abs=1e-9)
        assert five.age == m.age + (2 if on else 1)
    cfg = DetectorConfig()
    cfg.track.walls_smoothing_per_period = True
    cfg.track.axis_max_yaw_rate = 0.0                    # the EMA alone: a^2 over one 5 Hz step
    m = _run_track(xyz0, cfg, 3)
    five = estimate_track(xyz1, cfg.track, prev=m, periods=2)
    ten = estimate_track(xyz1, cfg.track, prev=estimate_track(xyz1, cfg.track, prev=m))
    assert abs(five.yaw - ten.yaw) < 0.1 * abs(ten.yaw - m.yaw), (m.yaw, five.yaw, ten.yaw)


def _cluster_at(x, zone="gauge"):
    c = np.array([x, 0.0, 0.5])
    return Cluster(points_idx=np.arange(3), n=10, n_raw=20, centroid=c, bbox_min=c - 0.25, bbox_max=c + 0.25,
                   distance=x - 0.25, lateral=0.0, height_min=0.2, height_max=0.7, intensity=30.0,
                   n_expected=10.0, score=1.0, zone=zone, n_gauge=10)


def test_persistence_in_seconds_derives_the_hit_count_from_the_frame_interval():
    cfg = TrackingConfig(confirm_time_s=0.5)
    t = Tracker(cfg)
    for k in range(1, 5):
        t.update([_cluster_at(100.0)], frame_dt=0.1)
        assert t.confirmed() == [], f"confirmed after {k} frames = {0.1 * k:.1f} s"
    t.update([_cluster_at(100.0)], frame_dt=0.1)
    assert len(t.confirmed()) == 1                      # 5 frames = 0.5 s at 10 Hz
    t = Tracker(cfg)                                    # at 5 Hz the same 0.5 s is 3 frames (= confirm_hits)
    for k in range(3):
        t.update([_cluster_at(100.0)], frame_dt=0.2)
        assert len(t.confirmed()) == (1 if k == 2 else 0)
    t = Tracker(cfg)                                    # no time base given: hit counting (confirm_hits)
    for k in range(3):
        t.update([_cluster_at(100.0)])
    assert len(t.confirmed()) == 1
    assert TrackingConfig().confirm_time_s == 0.5       # the default since v0.6.2 (0.3 s = 3 frames before)
    assert TrackingConfig().frames_to_confirm() == 5 and TrackingConfig().frames_to_confirm(0.2) == 3
    assert TrackingConfig(confirm_time_s=0.3).frames_to_confirm() == 3
    assert TrackingConfig(confirm_time_s=0.0).frames_to_confirm() == 3


def test_flickering_track_is_not_confirmed_and_zone_needs_a_clear_majority():
    cfg = TrackingConfig()                              # min_hit_fraction 0.6 over 10 frames
    t = Tracker(cfg)
    for k in range(14):                                 # matched every other frame: 50 % < 60 %
        t.update([_cluster_at(100.0)] if k % 2 == 0 else [], frame_dt=0.1)
        assert t.confirmed() == [], k
    t = Tracker(cfg)
    for k in range(12):                                 # one dropout in twelve: still reported once re-matched
        t.update([_cluster_at(100.0)] if k != 6 else [], frame_dt=0.1)
    assert len(t.confirmed()) == 1
    t = Tracker(cfg)                                    # zone: 10-hit window, 60 % must be inside the gauge
    for k in range(12):
        t.update([_cluster_at(50.0, "gauge" if k % 2 == 0 else "warning")], frame_dt=0.1)
    assert t.confirmed()[0].zone == "warning"
    for _ in range(4):
        t.update([_cluster_at(50.0, "gauge")], frame_dt=0.1)
    assert t.confirmed()[0].zone == "gauge"             # 7 of the last 10 hits inside


def _box(x, y, z, L, W, H, step=0.05):
    """Dense box of points (nearest face at X = x, centre at Y = y, bottom at Z = z) in a frame
    whose track axis is Y = 0 and rail head Z = 0, so dy = Y and h = Z."""
    xs = x + np.arange(0.0, L + 1e-9, step)
    ys = y - W / 2 + np.arange(0.0, W + 1e-9, step)
    zs = z + np.arange(0.0, H + 1e-9, step)
    return np.array(np.meshgrid(xs, ys, zs)).reshape(3, -1).T.astype(np.float32)


def _find(pts, cfg=None, frame_idx=None, **kw):
    cfg = cfg or DetectorConfig()
    dy, h = pts[:, 1].astype(np.float64), pts[:, 2].astype(np.float64)
    wide = point_in_polygon(dy, h, widened_profile(cfg.gauge, cfg.gauge.warning_margin))
    pts, dy, h = pts[wide], dy[wide], h[wide]
    ig = point_in_polygon(dy, h, cfg.gauge.profile)
    fi = None if frame_idx is None else frame_idx[wide]
    return find_clusters(pts, np.full(pts.shape[0], 30.0, np.float32), dy, h, ig, cfg.cluster, frame_idx=fi, **kw)


def test_infrastructure_signatures_are_advisory_and_objects_are_not():
    """v0.6: the envelope is 2.1 m x 3.0 m and the column / floating signatures only apply off
    the track centre (|lateral| > 0.6 m): a cable or object hanging near the axis is an obstacle."""
    cases = {
        "column":    (_box(40.0, 0.8, -0.15, 0.4, 0.4, 2.8), "column"),      # post / column / gate leg pulled in at the edge
        "beam":      (_box(60.0, 0.0, 1.6, 0.3, 2.6, 0.3), "elevated"),      # beam / roof strip across the corridor
        "sign":      (_box(50.0, 1.0, 1.2, 0.05, 0.6, 0.6), "floating"),     # sign on the wall, not touching the ground
        "duct":      (_box(30.0, 1.25, 0.6, 1.6, 0.5, 0.6), "edge"),         # duct / bench fragment at the corridor edge
        "portal":    (_box(75.0, 1.15, 0.55, 0.3, 1.6, 2.9), "wall_face"),   # wall face pulled in: hugs the edge, centre clear
        "person":    (_box(40.0, 0.0, -0.15, 0.4, 0.5, 1.7), ""),
        "crate":     (_box(60.0, 0.3, -0.15, 1.0, 1.0, 1.0), ""),
        "trolley":   (_box(50.0, -0.5, -0.15, 0.6, 0.6, 1.0), ""),
        "train":     (_box(75.0, 0.0, 0.1, 0.3, 2.7, 3.3), ""),              # a train ahead reaches the polygon bottom and both edges
        "edge_person": (_box(40.0, 0.9, -0.15, 0.4, 0.5, 1.7), ""),         # person at the envelope edge stays an obstacle
        "cable":     (_box(40.0, 0.1, 0.6, 0.05, 0.05, 2.4), ""),            # broken cable hanging near the axis (organizers' Q&A)
        "hanging":   (_box(45.0, -0.2, 1.5, 0.3, 0.3, 0.5), ""),             # small object hanging into the envelope near the axis
    }
    for name, (pts, want) in cases.items():
        cl = _find(pts)
        assert len(cl) == 1, (name, len(cl))
        assert cl[0].reason == want, (name, cl[0].reason, cl[0].zone)
        assert cl[0].zone == ("warning" if want else "gauge"), name
    off = DetectorConfig()
    for k in ("column_min_height", "elevated_min_height", "floating_min_height", "edge_min_lateral", "wall_face_min_height"):
        setattr(off.cluster, k, 0.0)
    for name in ("column", "beam", "sign", "duct", "portal"):
        cl = _find(cases[name][0], off)
        assert len(cl) == 1 and cl[0].zone == "gauge" and cl[0].reason == "", name


def test_gauge_edge_margin_shrinks_the_strict_decision_with_range():
    cfg = DetectorConfig().gauge
    cfg.edge_margin, cfg.edge_margin_per_100m = 0.0, 0.0          # v0.6 ships 0.15 m / 100 m; test the polygon itself first
    hw = float(np.abs(np.asarray(cfg.profile)[:, 0]).max())       # 1.05 m since v0.6
    dy = np.array([hw - 0.1, hw - 0.1, 0.5, -(hw - 0.1)])
    h = np.array([1.0, 1.0, 1.0, 1.0])
    X = np.array([10.0, 100.0, 100.0, 10.0])
    assert gauge_core_mask(dy, h, X, cfg).tolist() == [True, True, True, True]     # margins 0: the polygon itself
    cfg.edge_margin, cfg.edge_margin_per_100m = 0.02, 0.3
    assert gauge_core_mask(dy, h, X, cfg).tolist() == [True, False, True, True]    # 0.32 m margin at 100 m, 0.05 m at 10 m


def test_stopped_train_tracks_cue_reports_nothing():
    def tracks(vx):
        return [Track(id=i, centroid=np.array([50.0 + 10 * i, 0.0, 0.5]), velocity=np.array([vx, 0.0, 0.0]),
                      hits=4, misses=0, last=_cluster_at(50.0 + 10 * i)) for i in range(3)]
    assert EgoSpeedEstimator.tracks_cue(tracks(0.0), 0.1, min_speed=1.0) is None        # stopped: unknown, no merge
    assert EgoSpeedEstimator.tracks_cue(tracks(0.0), 0.1, min_speed=0.0) == (0.0, 3)    # the v0.4 behaviour
    v, n = EgoSpeedEstimator.tracks_cue(tracks(-1.5), 0.1, min_speed=1.0)
    assert abs(v - 15.0) < 1e-9 and n == 3


def test_lateral_smear_guard_redescribes_a_merged_cluster_from_the_current_frame():
    cur = _box(60.0, 0.0, -0.15, 0.4, 0.5, 1.7)
    old = _box(60.0, 1.2, -0.15, 0.4, 0.5, 1.7)                     # the same person 1.2 m to the left 0.3 s ago
    pts = np.concatenate([cur, old])
    fi = np.concatenate([np.arange(cur.shape[0]), np.full(old.shape[0], -1)])
    smeared = _find(pts, frame_idx=fi, smear_max_length=2.0, smear_max_width=0.0)
    guarded = _find(pts, frame_idx=fi, smear_max_length=2.0, smear_max_width=1.0)
    assert len(smeared) == 1 and smeared[0].size[1] > 1.5
    assert len(guarded) == 1 and guarded[0].size[1] < 0.6 and abs(guarded[0].lateral) < 0.1
    assert (guarded[0].points_idx >= 0).all()
