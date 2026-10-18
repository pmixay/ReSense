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
