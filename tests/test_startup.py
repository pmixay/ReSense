"""Start-up of a fresh bag (26.09, P3; docs/evidence/results/p3_startup_2026-09-26.json,
EXPERIMENTS §1j). The jury plays every hidden bag from a fresh start, so the first frames of a
fresh ``Detector`` must not STOP on an empty track and must not delay a real object.

The judge's finding: from the gate's chunk-2 cut of the ride (``new_data_55_0013``, a standing
train) a fresh detector STOPped at 2.9-3.1 m on frames 12-15: a low track made of the rail heads
3.0-3.6 m ahead, 3-12 cm above the young model's rail-head plane, in front of the range the bed
cross-section is learned from (``lowobj.template_range`` 4-30 m). ``tracking.low_min_seen_distance``
(candidate c) reports a low track only once it has been matched at or beyond that distance.
Candidates a (low tracks advisory while the calibration is pending) and b (no new low STOP while
the track model is young) were not shipped: they delay or drop a real low object at a fresh start.
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
    ("organizers' 0.3 x 0.3 x 0.1 m on a rail head",
     ObstacleSpec(kind="box", size=(0.3, 0.3, 0.1), distance=20.0, lateral=0.8, base_z=RAIL_HEAD_Z), "low"),
])
def test_fresh_start_real_box_at_20_m_stops_on_its_usual_frame(name, spec, kind):
    """A real object 20 m ahead at a fresh start: STOP on the frame its persistence allows
    (the 5th: 0.5 s / 5 hits) and on every frame after it, at 20 m, with the shipped defaults;
    a low object also with the start-up candidates a and b off (they would delay it)."""
    cfg = DetectorConfig()
    res = _fresh_run([spec], cfg)
    stops = [k for k, r in enumerate(res) if r.obstacle]
    usual = (cfg.tracking.low_confirm_hits if kind == "low" else cfg.tracking.frames_to_confirm()) - 1
    assert stops == list(range(usual, N_FRAMES)), (name, stops)
    d = res[usual].detections[0]
    assert d.kind == kind and abs(d.distance - 20.0) < 0.6


def test_rejected_start_up_candidates_stay_off():
    """Candidates a and b failed the pre-registered ray-cast check (a real low object 20 / 40 m
    ahead at a fresh start: no STOP in 40 frames with a, the first STOP on frame 16 instead of 4
    with b); they stay off in the shipped configuration."""
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml"))):
        assert cfg.lowobj.pending_advisory is False
        assert cfg.lowobj.min_model_age == 0


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
def test_low_track_matched_only_in_front_of_the_template_range(near):
    """The finding's track: a low cluster at 3.0-3.6 m on every frame of a standing train. With
    ``tracking.low_min_seen_distance`` 4 m it is never reported; with 0 (off) it is from its 5th
    hit (frame 4)."""
    cfg = DetectorConfig()
    cfg.tracking.low_min_seen_distance = near
    xs = [3.0, 3.0, 3.6, 3.1, 3.1, 3.0, 3.0, 3.2, 3.1, 3.0]
    rep = _reported(cfg, xs)
    assert rep == ([False] * 4 + [True] * 6 if near == 0 else [False] * len(xs))


def test_approaching_low_object_keeps_its_stop_into_the_near_range():
    """A real low object approaching from 12 m to 2.5 m (the set O objects on the rail were
    reported down to 1.4 m): reported from its 5th hit on every frame all the way in, the same
    with ``low_min_seen_distance`` 4 m as without it."""
    xs = list(np.linspace(12.0, 2.5, 20))
    runs = []
    for near in (0.0, 4.0):
        cfg = DetectorConfig()
        cfg.tracking.low_min_seen_distance = near
        runs.append(_reported(cfg, xs))
    assert runs[0] == runs[1] == [False] * 4 + [True] * 16
