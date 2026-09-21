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


# ---------------------------------------------------------------------------
# configuration and result contract
# ---------------------------------------------------------------------------

def test_config_new_sections_round_trip():
    cfg = DetectorConfig()
    back = DetectorConfig.from_dict(cfg.to_dict())
    assert back.to_dict() == cfg.to_dict()
    assert cfg.accumulation.enabled and cfg.accumulation.n_frames == 5
    assert cfg.cluster.retro_intensity == 100.0
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
    cfg = DetectorConfig()
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
    on = DetectorConfig()
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
    hit = first_alarm(Detector(DetectorConfig()), approach(tunnel, 140.0, 20, kind="box", size=BOX), EGO)
    assert hit is not None and hit[1] >= 100.0, hit and hit[:2]
    assert abs(hit[2].nearest_distance - hit[1]) <= max(2.0, 0.03 * hit[1])
    print("\n[synthetic] box 0.5 m confirmed at truth %.1f m (frame %d)" % (hit[1], hit[0]))


def test_clear_tunnel_with_accumulation_stays_clear(tunnel):
    frame, _, _ = tunnel
    det = Detector(DetectorConfig())
    for _ in range(10):
        res = det.process(frame, ego_speed=EGO)
        assert not res.obstacle and not res.warning, [d.to_dict() for d in res.detections + res.warnings]


def test_near_object_not_smeared_by_accumulation(tunnel):
    # approaching box crosses the accumulation boundary (40 m): distance and length stay right
    det = Detector(DetectorConfig())
    for d, fr in approach(tunnel, 45.0, 8, kind="box", size=(0.6, 0.6, 0.6), dropout={}):
        res = det.process(fr, ego_speed=EGO)
        if res.obstacle:
            assert abs(res.nearest_distance - d) < 1.0, (res.nearest_distance, d)
            assert res.detections[0].size[0] < 1.0
    assert res.obstacle and res.nearest_distance == pytest.approx(29.6, abs=1.0)
    # static person at 60 m, train stopped: 5 frames merge into the same voxels
    frame, _, gt = tunnel
    inj = inject_obstacles(frame, gt, [ObstacleSpec(kind="person", size=PERSON, distance=60.0, lateral=0.0, reflectivity=60)],
                           rng=np.random.default_rng(3))
    det = Detector(DetectorConfig())
    for _ in range(6):
        res = det.process(inj.frame, ego_speed=0.0)
    assert res.obstacle and res.n_accumulated == 5
    assert abs(res.nearest_distance - 60.0) < 1.0 and res.detections[0].size[0] < 1.0
    assert res.detections[0].n_points < 80                    # 56 voxels single-frame: no double counting


def test_wrong_given_speed_degrades_to_single_frame(tunnel):
    """Smear guard: with the speed 8 m/s off, the merged cluster stretches along X and is
    re-described from the current frame; the object is kept and its distance stays within
    tolerance (biased towards the vehicle by at most smear_max_length)."""
    det = Detector(DetectorConfig())
    confirmed = 0
    for d, fr in approach(tunnel, 100.0, 8, dropout={}):
        res = det.process(fr, ego_speed=30.0)
        if res.obstacle:
            confirmed += 1
            assert abs(res.nearest_distance - d) <= max(3.0, 0.03 * d), (res.nearest_distance, d)
            assert res.detections[0].size[0] <= 2.5
    assert confirmed >= 4


def test_timing_with_accumulation(tunnel):
    det = Detector(DetectorConfig())
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
    det = Detector(DetectorConfig())
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
    det = Detector(DetectorConfig())
    for k in range(6):
        res = det.process(_textured_scene(posts, 0.0, None, seed=300 + k), ego_speed=None)
        assert res.ego_speed_source == "none" and res.n_accumulated == 1, res.to_dict()
        assert not res.obstacle
    det = Detector(DetectorConfig())
    for k in range(5):
        res = det.process(synthetic_tunnel_frame(rng=np.random.default_rng(400 + k))[0], ego_speed=None)
        assert res.ego_speed_source == "none" and res.ego_speed_confidence < 0.5
        assert not res.obstacle and not res.warning


def test_unknown_speed_never_smears_the_moving_person(tunnel):
    """The emulated sequence moves only the object, the background is one frame: the
    estimator sees nothing moving, reports 'unknown', and the detector falls back to single
    frames instead of merging unshifted frames (which would stretch the person to 8.8 m)."""
    det = Detector(DetectorConfig())
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
    det = Detector(DetectorConfig())
    for _ in range(4):
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


def test_retro_rule_can_be_switched_off(tunnel):
    frame, _, gt = tunnel
    inj = inject_obstacles(frame, gt, [ObstacleSpec(kind="box", size=(0.05, 0.6, 0.8), distance=40.0, lateral=1.0, reflectivity=220)],
                           rng=np.random.default_rng(5))
    cfg = DetectorConfig()
    cfg.cluster.retro_intensity = 0.0
    det = Detector(cfg)
    for _ in range(4):
        res = det.process(inj.frame, ego_speed=0.0)
    assert res.obstacle
