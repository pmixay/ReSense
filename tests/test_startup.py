"""Start-up of a fresh bag (26.09, P3; docs/evidence/results/p3_startup_2026-09-26.json,
EXPERIMENTS §1j). The jury plays every hidden bag from a fresh start, so the first frames of a
fresh ``Detector`` must not STOP on an empty track and must not delay a real object.

The judge's finding: from the gate's chunk-2 cut of the ride (``new_data_55_0013``, a standing
train) a fresh detector STOPped at 2.9-3.1 m on frames 12-15: a low track made of the rail heads
3.0-3.6 m ahead, 3-12 cm above the young model's rail-head plane. The census shows the
start-window STOPs are the ride's ordinary false alarms, not caused by the start. Three rules were
tried and none is shipped (all off by default):

* a, ``lowobj.pending_advisory``: low tracks advisory while the calibration is pending - a real
  low object 20 / 40 m ahead of a fresh detector never STOPs;
* b, ``lowobj.min_model_age``: no new low STOP while the track model is young - the same object's
  first STOP moves from frame 4 to 16;
* c, ``tracking.low_min_seen_distance`` 4 m: a low track reported only once matched at >= 4 m -
  removes the finding, but a real low object that stays within 4 m (a standing train, or one that
  falls there) is never reported: a blind zone (addendum_blind_zone).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from resense.clustering import Cluster
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
from resense.tracking import Tracker

FLOOR_Z = -1.5                 # synthetic_tunnel_frame default: the bed
RAIL_HEAD_Z = FLOOR_Z + 0.18   # the synthetic rails are 0.18 m tall
N_FRAMES = 40                  # the census window: 4 s at 10 Hz
ROOT = Path(__file__).resolve().parents[1]


def _organizers_object(distance: float) -> ObstacleSpec:
    """The organizers' size criterion, 300 x 300 x 100 mm, lying on a rail head."""
    return ObstacleSpec(kind="box", size=(0.3, 0.3, 0.1), distance=distance, lateral=0.8, base_z=RAIL_HEAD_Z)


def _fresh_run(specs, cfg: DetectorConfig = None, n: int = N_FRAMES):
    """A fresh detector over ``n`` frames of a stationary ray-cast tunnel (the train stands)."""
    frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(5), specs=specs)
    det = Detector(cfg or DetectorConfig())
    return [det.process(Frame(xyz=frame.xyz, intensity=frame.intensity, stamp=0.1 * k)) for k in range(n)]


@pytest.mark.synthetic
def test_fresh_start_in_an_empty_tunnel_never_stops():
    """The first 4 s of a fresh bag in an empty tunnel: no STOP on any frame, while the mount
    calibration is still pending (the state every hidden bag starts in on an untilted rig)."""
    res = _fresh_run([])
    assert not any(r.obstacle for r in res), [(k, [d.to_dict() for d in r.detections])
                                              for k, r in enumerate(res) if r.obstacle]
    assert {r.mount["status"] for r in res} == {"pending"}


@pytest.mark.synthetic
@pytest.mark.parametrize("name,spec,kind", [
    ("box 0.5 m on the bed", ObstacleSpec(kind="box", size=(0.5, 0.5, 0.5), distance=20.0), ""),
    ("organizers' 0.3 x 0.3 x 0.1 m on a rail head", _organizers_object(20.0), "low"),
])
def test_fresh_start_real_box_at_20_m_stops_on_its_usual_frame(name, spec, kind):
    """A real object 20 m ahead at a fresh start: STOP on the frame its persistence allows
    (the 5th: 0.5 s / 5 hits) and on every frame after it, at 20 m, with the shipped defaults."""
    cfg = DetectorConfig()
    res = _fresh_run([spec], cfg)
    stops = [k for k, r in enumerate(res) if r.obstacle]
    usual = (cfg.tracking.low_confirm_hits if kind == "low" else cfg.tracking.frames_to_confirm()) - 1
    assert stops == list(range(usual, N_FRAMES)), (name, stops)
    d = res[usual].detections[0]
    assert d.kind == kind and abs(d.distance - 20.0) < 0.6


@pytest.mark.synthetic
def test_low_object_3_m_ahead_of_a_standing_fresh_start_stops():
    """No blind zone near the train: the organizers' object 3 m ahead of a standing train, from a
    fresh start, is a low STOP from frame 4 with the defaults. With the tried 4 m rule
    (``tracking.low_min_seen_distance``) it is never reported: why the rule is not shipped."""
    res = _fresh_run([_organizers_object(3.0)])
    stops = [k for k, r in enumerate(res) if r.obstacle]
    assert stops and stops[0] == 4, stops
    assert res[stops[0]].detections[0].kind == "low" and abs(res[stops[0]].nearest_distance - 3.0) < 0.3
    cfg = DetectorConfig()
    cfg.tracking.low_min_seen_distance = 4.0
    assert not any(r.obstacle for r in _fresh_run([_organizers_object(3.0)], cfg))


def test_tried_start_up_rules_are_off_by_default():
    """Candidates a, b and c were tried on 26.09 and none is shipped."""
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        assert cfg.lowobj.pending_advisory is False
        assert cfg.lowobj.min_model_age == 0
        assert cfg.tracking.low_min_seen_distance == 0.0


def _low(x: float, lateral: float = -0.85) -> Cluster:
    c = np.array([x + 0.2, lateral, -1.2])
    return Cluster(points_idx=np.arange(3), n=10, n_raw=20, centroid=c, bbox_min=c - [0.2, 0.1, 0.04],
                   bbox_max=c + [0.2, 0.1, 0.04], distance=x, lateral=lateral, height_min=0.04, height_max=0.12,
                   intensity=20.0, n_expected=8.0, score=1.0, zone="gauge", n_gauge=5, kind="low")


def _reported(cfg: DetectorConfig, xs) -> list:
    tr = Tracker(cfg.tracking)
    out = []
    for x in xs:
        tr.update([_low(x)], frame_dt=0.1)
        out.append(any(t.reported for t in tr.tracks))
    return out


@pytest.mark.parametrize("near", [0.0, 4.0])
def test_low_min_seen_distance_on_the_findings_track(near):
    """The rule itself, with the flag set explicitly. The finding's track: a low cluster at
    3.0-3.6 m on every frame of a standing train. With ``tracking.low_min_seen_distance`` 4 m it
    is never reported; with 0 (the default) it is from its 5th hit (frame 4)."""
    cfg = DetectorConfig()
    cfg.tracking.low_min_seen_distance = near
    xs = [3.0, 3.0, 3.6, 3.1, 3.1, 3.0, 3.0, 3.2, 3.1, 3.0]
    rep = _reported(cfg, xs)
    assert rep == ([False] * 4 + [True] * 6 if near == 0 else [False] * len(xs))


def test_low_min_seen_distance_keeps_an_approaching_object():
    """The rule itself, set explicitly: a low object approaching from 12 m to 2.5 m is reported
    from its 5th hit on every frame all the way in, with the 4 m rule as without it (the rule only
    loses objects never seen at 4 m or farther)."""
    xs = list(np.linspace(12.0, 2.5, 20))
    runs = []
    for near in (0.0, 4.0):
        cfg = DetectorConfig()
        cfg.tracking.low_min_seen_distance = near
        runs.append(_reported(cfg, xs))
    assert runs[0] == runs[1] == [False] * 4 + [True] * 16
