"""B6 harness (scripts/gauge_stability.py): known answers for the driven-path truth.

A train runs a circle of radius 400 m at 1.5 m per frame. A detector that reports that curvature must show
only the parabola-vs-arc gap against the driven path; one that reports a straight track must be off by the circle's offset
x^2 / (2 R) (to the arc's exact lateral); a missing registration starts a new segment that is never
composed across.
"""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gauge_stability", ROOT / "scripts/gauge_stability.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)

RADIUS, STEP, N = 400.0, 1.5, 260


def _step_transform(sign=1.0):
    """Pose of frame k in frame k-1: forward along a left-hand (sign +1) circle by STEP."""
    a = sign * STEP / RADIUS
    T = np.eye(4)
    T[:2, :2] = [[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]]
    T[0, 3] = RADIUS * np.sin(a)
    T[1, 3] = sign * RADIUS * (1 - np.cos(a))
    return T.tolist()


def _write(tmp_path, curvature, gap_at=None):
    poses = [{"i": 0, "T": None, "fitness": 0.0}]
    poses += [{"i": k, "T": None if k == gap_at else _step_transform(), "fitness": 1.0} for k in range(1, N)]
    track = [{"i": k, "decision": "GO", "R": np.eye(3).tolist(), "center": 0.3, "tan_yaw": 0.0,
              "half_curv": 0.5 * curvature, "axis_valid": 250.0} for k in range(N)]
    p, t = tmp_path / "poses.json", tmp_path / "track.json"
    p.write_text(json.dumps({"rows": poses}))
    t.write_text(json.dumps({"range_max": 250.0, "rows": track}))
    out = tmp_path / "out.json"
    G.measure(SimpleNamespace(track=str(t), poses=str(p), out=str(out)))
    return json.loads(out.read_text())


def test_exact_curvature_leaves_only_the_parabola_gap(tmp_path):
    """The detector's axis is a parabola in x; with the exact curvature the only error left is the gap between
    that parabola and the arc (0.30 m at 110 m, 2.0 m at 175 m for R = 400 m)."""
    r = _write(tmp_path, 1.0 / RADIUS)
    for lo, hi in G.BINS:
        x = 0.5 * (lo + hi)
        gap = (RADIUS - np.sqrt(RADIUS ** 2 - x ** 2)) - x * x / (2 * RADIUS)
        got = r["offtrack"][f"{lo}-{hi}"]["within_trusted"]["p50"]
        assert abs(got - gap) < 0.02, (lo, hi, got, gap)


def test_straight_detector_misses_by_the_circle_offset(tmp_path):
    r = _write(tmp_path, 0.0)
    x = 0.5 * (100 + 120)
    expected = RADIUS - np.sqrt(RADIUS ** 2 - x ** 2)    # lateral of the arc at forward distance x
    got = r["offtrack"]["100-120"]["within_trusted"]["p50"]
    assert abs(got - expected) < 0.05, (got, expected)


def test_gap_starts_a_new_segment(tmp_path):
    r = _write(tmp_path, 1.0 / RADIUS, gap_at=100)
    assert r["path_segments"] == 2
    assert r["offtrack"]["40-60"]["within_trusted"]["p90"] < 0.02      # gap at 50 m: 0.012 m


def test_driven_path_composes_poses():
    rows = [{"i": 0, "T": None}] + [{"i": k, "T": _step_transform()} for k in range(1, 5)]
    ps = G.driven_path(rows)
    assert [s for s, _ in ps] == [0] * 5
    a = 4 * STEP / RADIUS
    assert np.allclose(ps[4][1][:2, 3], [RADIUS * np.sin(a), RADIUS * (1 - np.cos(a))], atol=1e-9)



def _pose(x, y, th):
    W = np.eye(4)
    W[:2, :2] = [[np.cos(th), -np.sin(th)], [np.sin(th), np.cos(th)]]
    W[:2, 3] = [x, y]
    return W


def test_compensated_jitter_removes_real_heading_changes(tmp_path):
    """Straight track, the car's heading sways +-0.002 rad frame to frame and an exact detector reports it:
    the drawn edge at 120 m really moves 120 * 0.004 = 0.48 m per frame (raw jitter), while the track itself
    does not move, so the motion-compensated jitter is ~0. On a circle both are 0 (the view does not change)."""
    th = [0.002 * (-1) ** k for k in range(N)]
    W = [_pose(STEP * k, 0.0, th[k]) for k in range(N)]
    poses = [{"i": 0, "T": None, "fitness": 0.0}]
    poses += [{"i": k, "T": (np.linalg.inv(W[k - 1]) @ W[k]).tolist(), "fitness": 1.0} for k in range(1, N)]
    track = [{"i": k, "decision": "GO", "R": np.eye(3).tolist(), "center": 0.0, "tan_yaw": -np.tan(th[k]),
              "half_curv": 0.0, "axis_valid": 250.0} for k in range(N)]
    (tmp_path / "poses.json").write_text(json.dumps({"rows": poses}))
    (tmp_path / "track.json").write_text(json.dumps({"range_max": 250.0, "rows": track}))
    G.measure(SimpleNamespace(track=str(tmp_path / "track.json"), poses=str(tmp_path / "poses.json"),
                              out=str(tmp_path / "out.json")))
    r = json.loads((tmp_path / "out.json").read_text())
    assert abs(r["jitter"]["120m"]["all"]["p50"] - 0.48) < 0.01, r["jitter"]["120m"]
    assert r["jitter_compensated"]["120m"]["p90"] < 0.01, r["jitter_compensated"]["120m"]
    c = _write(tmp_path, 1.0 / RADIUS)
    # the moved parabola differs from the arc by ~2 cm at 120 m (the same parabola-vs-arc gap as above)
    assert c["jitter"]["120m"]["all"]["p90"] < 1e-6 and c["jitter_compensated"]["120m"]["p90"] < 0.03
