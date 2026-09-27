"""The learned track opinion and the along-track association gate (27.09, P2 ride).

``tracking.doubt_extra_hits`` with ``tracking.doubt_model``: a track about to become a STOP whose
opinion (``resense/opinion.py``) is below ``doubt_threshold`` and whose cluster is beyond
``doubt_near`` stays advisory (reason 'doubt') for that many more matched STOP-qualifying frames;
never within ``doubt_near``, never taking a STOP down. ``tracking.gate_along_only`` (the same fix
found independently by the P4 history work): the approach allowance widens the association gate
along X only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

from resense.clustering import Cluster
from resense.config import DetectorConfig, TrackingConfig
from resense.opinion import FEATURES, OBS_FIELDS, TrackOpinion, observation, track_features
from resense.tracking import Tracker

ROOT = Path(__file__).resolve().parents[1]
OFF = {"doubt_model": "", "doubt_extra_hits": 0}      # the opinion is on by default since 27.09


def _cl(x: float, lateral: float = 0.0, z: float = 1.0, zone: str = "gauge", top: float = 1.1) -> Cluster:
    c = np.array([x, lateral, z])
    return Cluster(points_idx=np.arange(3), n=20, n_raw=20, centroid=c, bbox_min=c - 0.3, bbox_max=c + 0.3,
                   distance=x, lateral=lateral, height_min=0.5, height_max=top, intensity=10.0,
                   n_expected=10.0, score=1.0, zone=zone, n_gauge=20)


def _model(tmp_path, far_p_low: bool = True) -> str:
    """One stump on the distance: p ~ 0.007 beyond 50 m (``far_p_low``), ~0.993 within."""
    v = [0.0, 5.0, -5.0] if far_p_low else [0.0, 5.0, 5.0]
    spec = {"features": FEATURES, "init": 0.0, "learning_rate": 1.0,
            "trees": [{"feature": [0, -2, -2], "threshold": [50.0, -2.0, -2.0], "left": [1, -1, -1],
                       "right": [2, -1, -1], "value": v}]}
    p = tmp_path / f"m{int(far_p_low)}.json"     # load_opinion caches per path
    p.write_text(json.dumps(spec))
    return str(p)


def _run(x0: float, n: int, top: float = 1.1, **kw):
    """A static object approaching at 1 m / frame; per frame (reported, zone) of track 1."""
    tr = Tracker(TrackingConfig(**kw))
    out = []
    for k in range(n):
        tr.update([_cl(x0 - k, top=top)], ego_shift=1.0, frame_dt=0.1)
        t = [t for t in tr.tracks if t.id == 1][0]
        out.append((t.reported, t.zone))
    return out, tr


def test_shipped_default_and_both_yaml():
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        t = cfg.tracking
        assert (t.doubt_model, t.doubt_extra_hits, t.doubt_near, t.doubt_sticky) == ("track_opinion.json", 10, 25.0, True)
        assert (t.doubt_body_height, t.doubt_body_range) == (1.0, 40.0)
        assert 0.0 < t.doubt_threshold < 0.5 and t.doubt_threshold == TrackingConfig().doubt_threshold
        assert t.gate_along_only is True
    tr = Tracker(TrackingConfig())                   # the model ships in resense/models/
    assert tr.opinion is not None and tr.record is True
    tr = Tracker(TrackingConfig(**OFF))
    assert tr.opinion is None and tr.record is False
    tr.update([_cl(80.0)], ego_shift=1.0, frame_dt=0.1)
    assert tr.tracks[0].obs == []


def test_doubtful_far_track_waits_extra_hits(tmp_path):
    base, _ = _run(80.0, 9, **OFF)
    first = next(i for i, (r, z) in enumerate(base) if r and z == "gauge")
    out, tr = _run(80.0, 9, doubt_model=_model(tmp_path), doubt_extra_hits=2, doubt_near=30.0)
    assert out[:first] == base[:first]
    assert out[first] == (True, "warning") and out[first + 1] == (True, "warning")
    assert out[first + 2] == (True, "gauge")
    assert all(o == (True, "gauge") for o in out[first + 2:])


def test_near_or_confident_track_is_not_delayed(tmp_path):
    base, _ = _run(80.0, 9, **OFF)
    near, _ = _run(80.0, 9, doubt_model=_model(tmp_path), doubt_extra_hits=2, doubt_near=100.0)
    assert near == base
    conf, _ = _run(80.0, 9, doubt_model=_model(tmp_path, far_p_low=False), doubt_extra_hits=2)
    assert conf == base
    within, _ = _run(45.0, 9, doubt_model=_model(tmp_path), doubt_extra_hits=2)   # p high within 50 m
    assert within == _run(45.0, 9, **OFF)[0]
    assert _run(80.0, 9)[0] == base                  # the shipped model: this clean approach is not delayed


def test_opinion_never_takes_a_stop_down(tmp_path):
    """A STOP confirmed within 50 m (p high) stays a STOP when the track recedes beyond it (p low)."""
    tr = Tracker(TrackingConfig(doubt_model=_model(tmp_path), doubt_extra_hits=3, doubt_near=0.0))
    for k in range(9):
        tr.update([_cl(45.0 + k)], ego_shift=-1.0, frame_dt=0.1)
    t = tr.tracks[0]
    assert t.reported and t.zone == "gauge" and t.last.distance > 50.0


def test_withheld_detection_is_advisory_with_reason(tmp_path):
    from resense.detector import Detector
    cfg = DetectorConfig()
    cfg.tracking.doubt_model, cfg.tracking.doubt_extra_hits = _model(tmp_path), 2
    det = Detector(cfg)
    det.track = type("T", (), {"age": 100})()
    for k in range(5):
        gauge, warn = det._confirm([_cl(80.0 - k)], speed=10.0, dt=0.1)
    assert not gauge and warn and warn[0].reason == "doubt"


def test_features_and_observation_shapes():
    obs = [observation(_cl(80.0 - k, lateral=0.1 * (k % 2))) for k in range(6)]
    assert len(obs[0]) == len(OBS_FIELDS)
    f = track_features(obs, hits=6, hit_fraction=1.0)
    assert f.shape == (len(FEATURES),)
    assert f[FEATURES.index("distance")] == pytest.approx(75.0)
    assert f[FEATURES.index("dist_step")] == pytest.approx(1.0)
    assert f[FEATURES.index("lat_jump")] == pytest.approx(0.1)
    assert f[FEATURES.index("dist_rough")] == pytest.approx(0.0)


def test_exported_trees_match_scikit_learn():
    pytest.importorskip("sklearn")
    sys.path.insert(0, str(ROOT / "scripts"))
    from track_opinion import export_gbm
    from sklearn.ensemble import GradientBoostingClassifier
    rng = np.random.default_rng(0)
    X = rng.normal(size=(300, len(FEATURES)))
    y = (X[:, 0] + 0.5 * X[:, 3] > 0).astype(int)
    clf = GradientBoostingClassifier(n_estimators=10, max_depth=2, random_state=0).fit(X, y)
    op = TrackOpinion(export_gbm(clf, FEATURES))
    for i in range(20):
        assert op.prob(X[i]) == pytest.approx(clf.predict_proba(X[i:i + 1])[0, 1], abs=1e-9)


def test_gate_along_only_rejects_transverse_jump_bought_by_the_approach_allowance():
    """Base gate 1.5 + 0.02 x 20 = 1.9 m at 20 m; step 25 m/s x 0.1 s = 2.5 m. A candidate 1 m closer
    and 2.2 m to the side is 2.4 m away: inside the widened sphere (4.4 m), outside the base radius
    around the approach segment."""
    for along_x, expect in ((False, 1), (True, 2)):
        tr = Tracker(TrackingConfig(gate_along_only=along_x))
        tr.update([_cl(20.0)], ego_shift=0.0, frame_dt=0.1)
        tr.update([_cl(19.0, lateral=2.2)], ego_shift=0.0, frame_dt=0.1)
        assert len(tr.tracks) == expect
    # a pure approach of the full allowance and a small transverse move stay matched
    for along_x in (False, True):
        tr = Tracker(TrackingConfig(gate_along_only=along_x))
        tr.update([_cl(20.0)], ego_shift=0.0, frame_dt=0.1)
        tr.update([_cl(20.0 - 1.9 - 2.4, lateral=0.3)], ego_shift=0.0, frame_dt=0.1)
        assert len(tr.tracks) == 1 and tr.tracks[0].hits == 2


def _stump(tmp_path, name: str, split: float, below: float, above: float) -> str:
    spec = {"features": FEATURES, "init": 0.0, "learning_rate": 1.0,
            "trees": [{"feature": [0, -2, -2], "threshold": [split, -2.0, -2.0], "left": [1, -1, -1],
                       "right": [2, -1, -1], "value": [0.0, below, above]}]}
    p = tmp_path / name
    p.write_text(json.dumps(spec))
    return str(p)


def test_sticky_doubt_ignores_a_rising_opinion(tmp_path):
    """p low beyond 76 m, high within: the non-sticky rule releases the track as soon as the opinion
    rises; the sticky one keeps it withheld for all its extra frames (released by doubt_near only)."""
    m = _stump(tmp_path, "rise.json", 75.5, 5.0, -5.0)
    base, _ = _run(80.0, 14, **OFF)
    first = next(i for i, (r, z) in enumerate(base) if r and z == "gauge")       # at 76 m
    loose, _ = _run(80.0, 14, doubt_model=m, doubt_extra_hits=6, doubt_near=30.0, doubt_sticky=False)
    sticky, _ = _run(80.0, 14, doubt_model=m, doubt_extra_hits=6, doubt_near=30.0, doubt_sticky=True)
    assert loose[first] == (True, "warning") and loose[first + 1] == (True, "gauge")
    assert all(z == "warning" for _, z in sticky[first:first + 6]) and sticky[first + 6] == (True, "gauge")
    near, _ = _run(80.0, 14, doubt_model=m, doubt_extra_hits=6, doubt_near=74.5, doubt_sticky=True)
    assert near[first + 1] == (True, "warning") and near[first + 2] == (True, "gauge")     # 74 m <= 74.5


def test_a_standing_body_within_the_body_range_is_not_delayed(tmp_path):
    """p low everywhere: a flat track (0.6 m tall) at 38 m is withheld, a standing one (1.5 m tall)
    is not; beyond doubt_body_range both are."""
    m = _stump(tmp_path, "low.json", 1000.0, -5.0, -5.0)
    kw = dict(doubt_model=m, doubt_extra_hits=3, doubt_near=10.0)
    for x0, top, delayed in ((40.0, 1.1, True), (40.0, 2.0, False), (60.0, 2.0, True)):
        base, _ = _run(x0, 9, top=top, **OFF)
        out, _ = _run(x0, 9, top=top, **kw)
        first = next(i for i, (r, z) in enumerate(base) if r and z == "gauge")
        assert (out[first] == (True, "warning")) is delayed, (x0, top)
        if not delayed:
            assert out == base


def test_the_extra_frames_are_a_budget_for_the_track_life(tmp_path):
    """A track whose rule zone flickers (gauge / warning) after its doubtful onset does not get its
    extra frames back: it is withheld for doubt_extra_hits frames in all, misses included."""
    m = _stump(tmp_path, "low.json", 1000.0, -5.0, -5.0)
    tr = Tracker(TrackingConfig(doubt_model=m, doubt_extra_hits=4, doubt_near=10.0))
    zones = ["gauge"] * 6 + ["warning"] * 3 + ["gauge"] * 3 + ["warning"] * 3 + ["gauge"] * 8   # rule zone: out at 13-16
    withheld = 0
    for k, z in enumerate(zones):
        tr.update([_cl(80.0 - k, zone=z)], ego_shift=1.0, frame_dt=0.1)
        t = tr.tracks[0]
        withheld += int(t.withheld)
    assert t.reported and t.zone == "gauge"
    assert 0 < withheld <= 4 and t.doubt >= 4
