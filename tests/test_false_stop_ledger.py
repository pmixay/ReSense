"""Checks for scripts/false_stop_ledger.py on synthetic runs, clouds and tracks (no organizer data).

The classifier is checked against a case with a known answer for every class (CLAUDE.md item 2), the ego
transport against an exact circle and an exact slope, the episode extraction against a hand-made run.
"""

import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

_script = Path(__file__).resolve().parents[1] / "scripts" / "false_stop_ledger.py"
_spec = importlib.util.spec_from_file_location("resense_false_stop_ledger", _script)
assert _spec is not None and _spec.loader is not None
L = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = L          # dataclasses look the module up
_spec.loader.exec_module(L)

from resense.track import TrackModel  # noqa: E402


def straight_track(**kw):
    base = dict(floor_coef=np.array([0.0, 0.0, -1.5]), floor_range=(0.0, 200.0), center=0.0, yaw=0.0,
                curvature=0.0, rail_offset=0.35)
    base.update(kw)
    return TrackModel(**base)


def track_dict(**kw):
    t = {"floor_coef": [0.0, 0.0, -1.5], "floor_range": [0.0, 200.0], "center": 0.0, "yaw": 0.0, "curvature": 0.0,
         "rail_offset": 0.35}
    t.update(kw)
    return t


def box_points(x0, x1, y0, y1, z0, z1, n=200, seed=0):
    r = np.random.default_rng(seed)
    return np.column_stack([r.uniform(x0, x1, n), r.uniform(y0, y1, n), r.uniform(z0, z1, n)]).astype(np.float32)


def tunnel_points(x0=0.0, x1=100.0, seed=1):
    """A straight tunnel: bed 1.5 m below the sensor, rails at -1.15, walls at |y| = 2.3, a vault 3 m above."""
    r = np.random.default_rng(seed)
    n = int((x1 - x0) * 150)
    x = lambda: r.uniform(x0, x1, n)            # noqa: E731
    bed = np.column_stack([x(), r.uniform(-2.3, 2.3, n), np.full(n, -1.5)])
    rails = np.column_stack([x(), r.choice([-0.72, 0.72], n), np.full(n, -1.15)])
    wall = np.column_stack([x(), r.choice([-2.3, 2.3], n), r.uniform(-1.5, 2.9, n)])
    vault = np.column_stack([x(), r.uniform(-2.3, 2.3, n), np.full(n, 3.0)])
    return np.vstack([bed, rails, wall, vault]).astype(np.float32)


CENTER = (20.0, 0.0, -0.6)
SIZE = (0.5, 0.5, 1.0)


def test_in_envelope_structure():
    pts = np.vstack([tunnel_points(), box_points(19.8, 20.2, -0.25, 0.25, -1.1, -0.2)])
    r = L.classify_window(pts, straight_track(), CENTER, SIZE, traveled=100.0)
    assert r["class"] == "in_envelope"
    assert r["n_env"] >= 100 and abs(r["dy_med"]) < 0.3 and 0.15 < r["h_med"] < 1.5
    assert r["ambiguous"] == []


def test_side_structure_in_front_of_the_wall():
    pts = np.vstack([tunnel_points(), box_points(19.8, 20.2, 1.8, 2.1, -1.1, 0.5)])
    r = L.classify_window(pts, straight_track(), (20.0, 1.95, -0.3), SIZE, traveled=100.0)
    assert r["class"] == "side"
    assert r["dy_med"] > L.SIDE_DY + 0.3 and r["n_env"] == 0 and r["n_fabric"] > 0


def test_overhead_structure_below_the_vault():
    pts = np.vstack([tunnel_points(), box_points(19.8, 20.2, -0.3, 0.3, 2.3, 2.5)])    # 3.45-3.65 m above the rail head
    r = L.classify_window(pts, straight_track(), (20.0, 0.0, 2.4), (0.5, 0.5, 0.3), traveled=100.0)
    assert r["class"] == "overhead"
    assert r["h_med"] > L.OVERHEAD_H + 0.3


def test_bed_and_rail_only():
    r = L.classify_window(tunnel_points(), straight_track(), (20.0, 0.0, -1.2), (0.5, 0.5, 0.5), traveled=100.0)
    assert r["class"] == "bed_rail"
    assert r["n_bed"] > 10 and r["n_env"] == 0


def test_nothing_there_is_phantom():
    r = L.classify_window(tunnel_points(), straight_track(), (20.0, 0.0, 1.0), SIZE, traveled=0.0)
    assert r["class"] == "phantom" and r["n_all"] < 3


def test_a_position_outside_the_gauge_with_nothing_seen_is_side_by_position():
    r = L.classify_window(tunnel_points(), straight_track(), (20.0, 9.0, 0.5), SIZE, traveled=100.0)
    assert r["class"] == "side" and r["by_position"] and r["dy_position"] == pytest.approx(9.0)
    assert any(w.startswith("side_by_position") for w in r["ambiguous"])
    # the same empty air inside the gauge is a phantom, not a side structure
    assert L.classify_window(tunnel_points(), straight_track(), (20.0, 0.0, 1.0), SIZE, 0.0)["class"] == "phantom"


def test_the_wall_or_vault_at_the_position_is_flagged_tunnel_fabric_not_a_localized_structure():
    wall = L.classify_window(tunnel_points(), straight_track(), (20.0, 2.2, 0.5), SIZE, traveled=100.0)
    assert wall["class"] == "side" and wall["on_fabric"] and "on_tunnel_fabric" in wall["ambiguous"]
    assert wall["n_side"] == 0 and wall["n_fabric"] > 0                       # nothing localized
    vault = L.classify_window(tunnel_points(), straight_track(), (20.0, 0.0, 2.6), SIZE, traveled=100.0)
    assert vault["class"] == "overhead" and vault["on_fabric"]
    # the same position in the middle of the tunnel, away from every surface, sees only the bed
    mid = L.classify_window(tunnel_points(), straight_track(), (20.0, 0.0, -0.9), SIZE, traveled=0.0)
    assert mid["class"] == "bed_rail" and not mid.get("on_fabric")


def test_a_surface_seen_on_one_side_only_is_fabric():
    # the vault close to the sensor is not in its view: only the slices ahead of the window hold it
    pts = np.vstack([tunnel_points(0.0, 100.0)[tunnel_points(0.0, 100.0)[:, 2] < 2.9],
                     tunnel_points(14.0, 100.0, seed=5)[tunnel_points(14.0, 100.0, seed=5)[:, 2] >= 2.9]])
    r = L.classify_window(pts, straight_track(), (20.0, 0.0, 2.6), SIZE, traveled=100.0)
    assert r["class"] == "overhead" and r["on_fabric"] and r["n_over"] == 0
    # a plate that exists only inside the window is localized
    plate = np.vstack([pts, box_points(19.0, 21.0, -0.3, 0.3, 2.3, 2.5)])
    assert L.classify_window(plate, straight_track(), (20.0, 0.0, 2.4), SIZE, traveled=100.0)["n_over"] > 100


def test_the_card_limits():
    tr = straight_track()
    inside = np.vstack([tunnel_points(), box_points(19.8, 20.2, 1.25, 1.35, -1.1, -0.2)])
    outside = np.vstack([tunnel_points(), box_points(19.8, 20.2, 1.5, 1.6, -1.1, -0.2)])
    assert L.classify_window(inside, tr, (20.0, 1.3, -0.6), SIZE, 100.0)["class"] == "in_envelope"
    assert L.classify_window(outside, tr, (20.0, 1.55, -0.6), SIZE, 100.0)["class"] == "side"
    edge = np.vstack([tunnel_points(), box_points(19.8, 20.2, 1.35, 1.45, -1.1, -0.2)])
    assert "dy_near_limit" in L.classify_window(edge, tr, (20.0, 1.4, -0.6), SIZE, 100.0)["ambiguous"]


def test_mixed_and_sparse_structures_are_ambiguous():
    tr = straight_track()
    mixed = np.vstack([tunnel_points(), box_points(19.8, 20.2, -0.2, 0.2, -1.1, -0.2, n=60),
                       box_points(19.8, 20.2, 1.5, 1.6, -1.1, -0.2, n=50, seed=3)])
    r = L.classify_window(mixed, tr, (20.0, 0.8, -0.6), SIZE, 100.0)
    assert any(w.startswith("mixed") for w in r["ambiguous"])
    sparse = np.vstack([tunnel_points(), box_points(19.9, 20.1, -0.1, 0.1, -1.0, -0.5, n=6)])
    assert "few_points" in L.classify_window(sparse, tr, CENTER, SIZE, 100.0)["ambiguous"]


def test_the_window_grows_with_the_distance_travelled_and_is_capped():
    p = L.ClassifierParams()
    pts = np.vstack([tunnel_points(), box_points(19.8, 20.2, -0.25, 0.25, -1.1, -0.2)])
    near = L.classify_window(pts, straight_track(), CENTER, SIZE, 0.0)
    far = L.classify_window(pts, straight_track(), CENTER, SIZE, 1000.0)
    assert near["lon"] == p.lon0 and far["lon"] == p.lon_max and far["lat"] == p.lat_max


def test_the_episode_class_needs_agreeing_frames():
    f = lambda c, amb=(): {"class": c, "ambiguous": list(amb)}          # noqa: E731
    assert L.episode_class([f("side")] * 5) == ("side", 1.0, [])
    cls, agree, why = L.episode_class([f("side"), f("side"), f("in_envelope"), f("phantom")])
    assert cls == "side" and agree == 0.5 and why and why[0].startswith("frames_disagree")
    assert L.episode_class([f("side", ["few_points(4)"])] * 4)[2] == ["frames_ambiguous", "flags:few_points"]
    assert L.episode_class([])[2] == ["no_frames"]


# --- ego transport -------------------------------------------------------------------------------------------

def test_advance_straight():
    p = L.advance([100.0, 0.5, 0.2], 3.0, 0.0, 0.0, 0.0, 0.0)
    assert np.allclose(p, [97.0, 0.5, 0.2])


def test_advance_follows_a_circle_exactly():
    # a train on a left circle of radius R carries a world point; after travelling an arc it must be where the
    # geometry says, whatever the step size (the steps are chords of the arc, the rotation is the arc's)
    R, arc = 400.0, 120.0
    world = np.array([100.0, 3.0, 0.0])                       # in the frame at the start: R-circle centre at (0, R)
    n = 1200
    s = arc / n
    p = world.copy()
    for _ in range(n):
        p = L.advance(p, s, 0.0, 0.0, 1.0 / R, 0.0)
        # the vehicle's path direction is its own x axis on a circle: psi = 0 in its own frame
    th = arc / R
    ctr = np.array([0.0, R])
    c, s_ = math.cos(-th), math.sin(-th)
    rel = world[:2] - np.array([R * math.sin(th), R * (1 - math.cos(th))])   # relative to the new origin (world frame)
    exp = np.array([c * rel[0] - s_ * rel[1], s_ * rel[0] + c * rel[1]])
    assert ctr[1] == R
    assert np.allclose(p[:2], exp, atol=0.02)


def test_advance_up_a_slope_and_pitch_change():
    phi = math.atan(0.03)
    p = L.advance([100.0, 0.0, 0.0], 10.0, 0.0, phi, 0.0, 0.0)
    # moved 10 m along a 3 % slope: 9.995 m ahead and 0.3 m up, so the point is 0.3 m lower and 9.995 m nearer
    assert p[0] == pytest.approx(100.0 - 10.0 * math.cos(phi)) and p[2] == pytest.approx(-10.0 * math.sin(phi))
    q = L.advance([100.0, 0.0, 0.0], 10.0, 0.0, 0.0, 0.0, 0.001)   # the nose rises 0.01 rad: a fixed point drops
    assert q[2] < -0.5


def test_transport_uses_the_track_of_each_frame_and_the_speed_series():
    rows = []
    for i in range(80):
        rows.append({"stamp": 100.0 + 0.1 * i, "ego_speed": None, "ego_speed_estimate": 10.0 if i % 2 == 0 else None,
                     "track": track_dict(), "obstacle": False})
    v, src = L.speed_series(rows)
    assert np.allclose(v, 10.0) and set(src) == {"estimate", "interp", "hold"}
    path = L.transport(rows, 0, [60.0, 0.4, -0.5])
    assert path[0]["range"] == pytest.approx(math.hypot(60.0, 0.4))
    # 10 m/s * 0.1 s = 1 m per frame; the walk ends at the end of the piece (79 frames) or when x < -10
    assert path[10]["p"][0] == pytest.approx(50.0) and path[10]["traveled"] == pytest.approx(10.0)
    inb, closest, mode = L.band_frames(path)
    assert mode == "band" and inb and all(L.BAND[0] <= q["range"] <= L.BAND[1] for q in inb) and len(inb) <= 6
    assert closest < 25.0
    # a train that stops 30 m short: the closest approach is used and said so; 80 m short: nothing
    stop = [{"i": k, "p": np.array([60.0 - k, 0.0, 0.0]), "range": 60.0 - k, "traveled": float(k), "src": "x"}
            for k in range(31)]
    inb, closest, mode = L.band_frames(stop)
    assert mode == "nearest" and closest == 30.0 and all(q["range"] <= 32.5 for q in inb)
    assert L.band_frames(stop[:10])[2] == "none"


def test_long_gaps_take_the_intake_speed_of_the_split():
    rows = [{"frame_id": f"new_data_7_{i:03d}", "ego_speed": None,
             "ego_speed_estimate": 10.0 if i in (0, 1, 2, 3, 4, 80, 81) else None} for i in range(90)]
    v, src = L.speed_series(rows, {7: 12.0})
    assert src[2] == "estimate" and src[40] == "intake" and v[40] == 12.0 and src[5:80].tolist().count("intake") == 75
    short = [{"frame_id": "new_data_7_000", "ego_speed": None, "ego_speed_estimate": 10.0 if i % 20 == 0 else None}
             for i in range(61)]
    assert set(L.speed_series(short, {7: 12.0})[1][1:20]) == {"interp"}
    v, src = L.speed_series([{"frame_id": "new_data_7_000", "ego_speed_estimate": None}] * 3, {7: 12.0})
    assert set(src) == {"intake"} and np.allclose(v, 12.0)
    assert L.split_of("new_data_12_034") == 12 and L.split_of("roundT_doubleT_0001") is None


def test_speed_series_without_any_value_is_zero():
    v, src = L.speed_series([{"ego_speed": None, "ego_speed_estimate": None}] * 3)
    assert not v.any() and set(src) == {"none"}


def test_frame_dt_rejects_jumps():
    assert L.frame_dt(1.0, 1.1) == pytest.approx(0.1)
    assert L.frame_dt(1.0, 2.0) == 0.1 and L.frame_dt(None, 2.0) == 0.1


# --- episodes and the ledger rows -----------------------------------------------------------------------------

def run_rows(stops):
    """A 30-frame piece; ``stops`` = {frame: distance} marks STOP frames."""
    rows = []
    for i in range(30):
        dets = []
        if i in stops:
            dets = [{"id": 7, "zone": "gauge", "distance": stops[i], "lateral": 0.2, "center": [stops[i], 0.2, -0.5],
                     "size": [0.4, 0.8, 1.1], "n_points": 12, "confidence": 0.9, "age": 5, "height_min": 0.3,
                     "intensity": 20.0, "reason": "far_cluster", "kind": "free"}]
        rows.append({"frame": i, "frame_id": f"bag_{i:04d}", "stamp": 5.0 + 0.1 * i, "obstacle": bool(dets),
                     "detections": dets, "track": {**track_dict(), "axis_valid": 80.0}, "ego_speed": None,
                     "ego_speed_source": "none", "ego_speed_estimate": 12.0,
                     "health": {"level": "ok", "rail_lock": 0.95, "monitored_range": 120.0, "messages": []},
                     "mount": {"status": "identity"}})
    return rows


def test_stop_runs_count_every_go_to_stop_transition_including_the_first_frame():
    rows = run_rows({0: 80.0, 1: 79.0, 5: 120.0, 6: 119.0, 7: 118.0, 29: 50.0})
    assert L.stop_runs(rows) == [(0, 1), (5, 7), (29, 29)]
    assert L.stop_runs(run_rows({})) == []


def test_episode_row_fields():
    piece = {"bag": "bag", "piece": 0, "start": 0}
    rows = run_rows({5: 120.0, 6: 119.0, 7: 90.0})
    eps = L.build_rows([piece], [rows])
    assert len(eps) == 1
    e = eps[0]
    assert e["id"] == "bag:5" and e["distance"] == 120.0 and e["far_onset"] is True
    assert e["episode"] == {"stop_frames": 3, "last_frame": 7, "min_distance": 90.0, "max_distance": 120.0,
                            "kinds": ["free"]}
    assert e["rail_lock"] == 0.95 and e["mount"]["status"] == "identity" and e["ego"]["estimate"] == 12.0
    assert e["curvature"] == 0.0 and e["track"]["axis_valid"] == 80.0
    json.dumps(e)


def test_ride_frames_are_numbered_through_the_whole_ride():
    piece = {"bag": "new_data", "piece": 3, "start": 4000}
    rows = run_rows({2: 60.0})
    assert L.build_rows([piece], [rows])[0]["frame"] == 4002


def test_extended_rows_follow_the_pieces_of_the_same_recording():
    pieces = [{"bag": "new_data", "files": ["a", "b"]}, {"bag": "new_data", "files": ["c"]},
              {"bag": "other", "files": ["d"]}]
    rows = [[1, 2], [3], [4]]
    assert L.extended(pieces, rows, 0) == ([1, 2, 3], ["a", "b", "c"])
    assert L.extended(pieces, rows, 1) == ([3], ["c"])
    assert L.extended(pieces, rows, 2) == ([4], ["d"])


def test_reproduction_tolerances():
    row = {"frame": 5100, "piece_frame": 100, "distance": 120.0}     # the ride's frame numbers run through the whole ride
    assert L.reproduces(row, {"stop_first": {"frame": 102, "distance": 121.9}})[0]
    assert not L.reproduces(row, {"stop_first": {"frame": 103, "distance": 120.0}})[0]
    assert not L.reproduces(row, {"stop_first": {"frame": 100, "distance": 122.1}})[0]
    assert not L.reproduces(row, {"stop_first": None})[0]
    ok, df, dd = L.reproduces(row, {"stop_first": {"frame": 98, "distance": 119.0}})
    assert ok and df == -2 and dd == -1.0


def test_piece_table_splits_the_ride_like_the_gate(tmp_path):
    cache, runs = tmp_path / "cache", tmp_path / "runs"
    (cache / "new_data").mkdir(parents=True)
    runs.mkdir()
    names = [f"new_data_{s}_{f:03d}" for s in range(2) for f in range(5)]
    for n in names:
        (cache / "new_data" / f"{n}.npy").write_bytes(b"x")
    for k in range(3):
        (runs / f"new_data_{k}.jsonl").write_text("")
    pieces = L.piece_table(str(runs), str(cache), ["new_data"])
    assert [len(p["files"]) for p in pieces] == [4, 3, 3] and [p["start"] for p in pieces] == [0, 4, 7]
    rows = [{"frame_id": Path(f).name[:-4]} for f in pieces[0]["files"]]
    L.check_piece(pieces[0], rows)
    with pytest.raises(SystemExit):
        L.check_piece(pieces[0], rows[:-1])
    rows[1] = {"frame_id": "other"}
    with pytest.raises(SystemExit):
        L.check_piece(pieces[0], rows)


def test_f2_summary_counts_far_onsets_per_class_and_mechanism():
    eps = [{"id": "a", "far_onset": True, "passby": {"class": "side", "ambiguous": False, "axis_error_m": 1.6,
                                                     "on_tunnel_surface": True}},
           {"id": "b", "far_onset": True, "passby": {"class": "side", "ambiguous": True, "axis_error_m": 0.3}},
           {"id": "c", "far_onset": False, "passby": {"class": "phantom", "ambiguous": False}},
           {"id": "d", "far_onset": True, "passby": {"class": "overhead", "ambiguous": False, "axis_error_m": -1.0}}]
    s = L.f2_summary(eps)
    assert s["far_episodes"] == 3 and s["by_class"]["side"] == {"n": 2, "ambiguous": 1, "ids": ["a", "b"]}
    assert "phantom" not in s["by_class"] and s["by_class_all"]["phantom"]["n"] == 1
    assert s["by_mechanism_far"]["side_structure_axis_misfit_tunnel_surface"]["ids"] == ["a"]
    assert s["by_mechanism_far"]["side_structure_within_axis_error"]["ids"] == ["b"]
    assert s["by_mechanism_far"]["overhead_height_reference"]["ids"] == ["d"]
    assert s["by_mechanism_all"]["bed_or_phantom_height_reference"]["ids"] == ["c"]
    assert s["far_axis_error_m"]["n"] == 3 and s["far_axis_error_m"]["share_at_least_0.9"] == 0.67


def test_track_dict_round_trip_reproduces_the_coordinates():
    from resense.gauge import corridor_coordinates
    t = track_dict(floor_coef=[1e-5, 0.004, -1.5], center=0.3, yaw=0.01, curvature=2e-4)
    m = L.track_from_dict(t)
    xyz = np.array([[20.0, 0.5, -1.0], [80.0, -0.2, -0.5]], dtype=np.float32)
    dy, h = corridor_coordinates(xyz, m)
    assert dy[0] == pytest.approx(0.5 - float(m.center_y(np.array([20.0]))[0]), abs=1e-4)
    assert h[0] == pytest.approx(-1.0 - float(m.rail_z(np.array([20.0]))[0]), abs=1e-4)
    assert L.floor_slope(t, 10.0) == pytest.approx(2 * 1e-5 * 10.0 + 0.004, abs=1e-4)


def test_render_episode_writes_a_small_png(tmp_path):
    pts = np.vstack([tunnel_points(), box_points(19.8, 20.2, -0.25, 0.25, -1.1, -0.2)])
    row = {"id": "bag:5", "distance": 120.0, "lateral": 0.2, "kind": "free", "reason": "far_cluster",
           "center": [120.0, 0.2, -0.5], "size": [0.4, 0.8, 1.1]}
    r = L.classify_window(pts, straight_track(), CENTER, SIZE, 100.0)
    r.update({"frame": 9, "range": 18.0})
    saved = {"onset_xyz": pts, "onset_track": track_dict(), "passby_xyz": {9: pts}, "passby_track": {9: track_dict()}}
    pb = {"class": r["class"], "frames": [r], "path": [{"i": 9, "p": np.array(CENTER)}]}
    out = tmp_path / "e.png"
    L.render_episode(str(out), row, saved, pb)
    assert out.exists() and 2000 < out.stat().st_size < 400_000
    out2 = tmp_path / "e2.png"
    L.render_episode(str(out2), row, saved, {"class": "unreached", "frames": []})
    assert out2.exists()
