"""v0.6 behaviour required by the organizers' Q&A session (docs/organizers/QA_session.md):

* the monitored envelope is the train's 2.1 m x 3.0 m cross-section (an object 1.3 m off the
  axis is advisory, not an alarm);
* the size criterion is a 300 x 300 x 100 mm object on the track (the low-object stage);
* a broken cable hanging into the envelope must be detected (no column / floating / overhead
  demotion near the axis).
"""
from __future__ import annotations

import numpy as np
import pytest

from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.synthetic import ObstacleSpec, catalogue_spec, synthetic_tunnel_frame

FLOOR_Z = -1.5          # synthetic_tunnel_frame default: the bed (rails 0.18 m on top of it)


def _scene(specs, seed=5):
    frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(seed), specs=specs)
    return frame


def _run(frame: Frame, n: int = 6, cfg: DetectorConfig = None):
    det = Detector(cfg or DetectorConfig())
    res = None
    for k in range(n):
        res = det.process(Frame(xyz=frame.xyz, intensity=frame.intensity, stamp=0.1 * k))
    return res


def test_default_gauge_is_the_organizers_envelope():
    p = np.asarray(DetectorConfig().gauge.profile)
    assert p[:, 0].max() == pytest.approx(1.05) and p[:, 0].min() == pytest.approx(-1.05)
    assert p[:, 1].max() == pytest.approx(3.0)


def test_clear_tunnel_has_no_low_object_alarm(tunnel):
    frame, _, _ = tunnel
    res = _run(frame, 8)
    assert not res.obstacle, [d.to_dict() for d in res.detections]
    assert not any(c.kind == "low" for c in res.candidates)


RAIL_HEAD_Z = FLOOR_Z + 0.18    # synthetic rails are 0.18 m tall


@pytest.mark.parametrize("distance,lateral", [(10.0, -0.8), (16.0, 0.8), (20.0, -0.75)])
def test_organizers_minimum_object_on_a_rail(distance, lateral):
    """300 x 300 x 100 mm lying on a rail head: 0.1 m above the rail-head plane, below the
    0.12 m polygon bottom - found by the low-object stage (bumps above the learned bed)."""
    spec = ObstacleSpec(kind="box", size=(0.3, 0.3, 0.1), distance=distance, lateral=lateral, base_z=RAIL_HEAD_Z)
    res = _run(_scene([spec]))
    assert res.obstacle, [(c.kind, c.distance, c.size.round(2).tolist()) for c in res.candidates]
    d = res.detections[0]
    assert abs(d.distance - distance) < 0.6 and abs(d.lateral - lateral) < 0.3


@pytest.mark.parametrize("distance,lateral", [(12.0, 0.0), (20.0, 0.4), (28.0, -0.3)])
def test_minimum_object_below_the_rail_head_is_a_policy(distance, lateral):
    """The same object lying on the bed between the rails stays below the rail head: by default
    (``lowobj.min_top`` = 0.03) it is not an alarm - the metro bed carries fixtures of that size
    every few tens of metres (1 350 alarm events on the 20-minute ride with the bed-level policy,
    EXPERIMENTS.md §1d); ``min_top: -1`` reports any bump above the bed."""
    spec = ObstacleSpec(kind="box", size=(0.3, 0.3, 0.1), distance=distance, lateral=lateral, base_z=FLOOR_Z)
    assert not _run(_scene([spec])).obstacle
    cfg = DetectorConfig()
    cfg.lowobj.min_top = -1.0
    res = _run(_scene([spec]), cfg=cfg)
    assert res.obstacle and res.detections[0].kind == "low"
    assert abs(res.detections[0].distance - distance) < 0.6


def test_low_object_stage_can_be_switched_off():
    spec = ObstacleSpec(kind="box", size=(0.3, 0.3, 0.1), distance=15.0, lateral=0.8, base_z=RAIL_HEAD_Z)
    assert _run(_scene([spec])).obstacle
    cfg = DetectorConfig()
    cfg.lowobj.enabled = False
    assert not _run(_scene([spec]), cfg=cfg).obstacle


@pytest.mark.parametrize("distance,lateral,name", [(25.0, 0.0, "cable"), (40.0, 0.3, "cable"),
                                                   (30.0, -0.2, "cable_low")])
def test_hanging_cable_in_the_envelope_is_an_obstacle(distance, lateral, name):
    spec = catalogue_spec(name, distance, lateral, reflectivity=25.0)
    res = _run(_scene([spec]))
    assert res.obstacle, [(c.distance, c.zone, c.reason, c.size.round(2).tolist()) for c in res.candidates]
    assert abs(res.nearest_distance - distance) < 1.0


def test_object_outside_the_envelope_is_advisory():
    """A person 1.35 m off the axis: inside the v0.5 polygon (1.40 m), outside the 1.05 m envelope."""
    spec = catalogue_spec("person", 35.0, 1.35, reflectivity=30.0)
    res = _run(_scene([spec]))
    assert not res.obstacle
    assert res.warning


def test_person_in_the_envelope_still_alarms():
    spec = catalogue_spec("person", 60.0, 0.2, reflectivity=30.0)
    res = _run(_scene([spec]))
    assert res.obstacle and abs(res.nearest_distance - 60.0) < 1.0
