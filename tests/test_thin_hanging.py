"""Thin objects hanging from above into the envelope (``cluster.hanging_enabled``, SCORECARD #11,
25.09; docs/EXPERIMENTS.md §1i, docs/evidence/results/p3_thin_hanging_2026-09-25.json).

The organizers' 5 cm object hanging from the roof of set O dips only 0.2-0.4 m below the 3.0 m
envelope top, with 1-3 returns there a frame: it never reaches the corridor clustering's 5-voxel
minimum and read GO down to 6.7 m. ``clustering.find_hanging`` links those returns to the
object's part above the envelope top (near the axis, thin along and across the track, within
``hanging_max_distance``) and reports it as a gauge obstacle of kind ``hanging``.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np

from resense.clustering import find_hanging
from resense.config import ClusterConfig, DetectorConfig
from resense.detector import Detector
from resense.frame import Frame

AXIS_Y = 0.25                   # synthetic_tunnel_frame: the track axis
RAIL_HEAD_Z = -1.5 + 0.18       # the bed at -1.5, rails 0.18 m tall
TOP = 3.0                       # the envelope top above the rail head


def _on(**kw) -> DetectorConfig:
    """The shipped configuration (the rule on since 25.09), with optional overrides."""
    cfg = DetectorConfig()
    assert cfg.cluster.hanging_enabled
    cfg.cluster = replace(cfg.cluster, **kw)
    return cfg


def _off() -> DetectorConfig:
    """The shipped configuration with the rule off (the output before 25.09)."""
    cfg = DetectorConfig()
    cfg.cluster = replace(cfg.cluster, hanging_enabled=False)
    return cfg


def _line(x: float, lateral: float, h0: float, h1: float, n: int, length: float = 0.0):
    """Points on a line (vertical, or tilted along X by ``length``) in track coordinates
    (axis at y = 0, rail head at z = 0): (xyz, dy, h, intensity)."""
    t = np.linspace(0.0, 1.0, n)
    xyz = np.stack([x + length * t, np.full(n, lateral), h0 + (h1 - h0) * t], 1).astype(np.float32)
    return xyz, xyz[:, 1].astype(np.float64), xyz[:, 2].astype(np.float64), np.full(n, 20.0, np.float32)


def _find(cfg: ClusterConfig, xyz, dy, h, inten):
    return find_hanging(xyz, inten, dy, h, cfg, TOP, 3.0, cfg.hanging_max_distance)


def test_shipped_defaults():
    """On since 25.09 with the pre-registered candidate A, in the code and in both parameter files."""
    import yaml
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(root / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(root / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        c = cfg.cluster
        assert c.hanging_enabled is True
        assert (c.hanging_min_voxels, c.hanging_max_lateral, c.hanging_max_size, c.hanging_max_distance) == (1, 0.8, 0.5, 60.0)
        assert (c.hanging_min_height, c.hanging_link_band) == (1.8, 0.6)
    assert yaml.safe_load((root / "configs/default.yaml").read_text())["resense"]["cluster"]["hanging_enabled"] is True


def test_find_hanging_shapes():
    """A vertical 5 cm object dipping 0.35 m into the envelope on the axis at 25 m is a hanging
    cluster; the same object entirely above the top, a duct along the track, one off the axis and
    one too far are not; one with a single return inside the envelope is one with the shipped
    minimum (candidate A) and not with two (candidate B)."""
    cfg = ClusterConfig()
    rod = _line(25.0, 0.05, TOP - 0.35, TOP + 0.55, 5)              # 0.225 m apart: 2 returns inside
    out = _find(cfg, *rod)
    assert len(out) == 1
    c = out[0]
    assert c.kind == "hanging" and c.zone == "gauge" and c.reason == ""
    assert c.n_gauge >= 2 and c.height_min < TOP < c.height_max and c.score > 0.5
    assert not _find(cfg, *_line(25.0, 0.05, TOP + 0.05, TOP + 0.55, 5))            # all above the top
    assert not _find(cfg, *_line(25.0, 0.05, TOP - 0.3, TOP + 0.3, 12, length=2.0))  # a duct along the track
    assert not _find(cfg, *_line(25.0, 0.95, TOP - 0.35, TOP + 0.55, 5))            # beside the axis
    assert not _find(cfg, *_line(75.0, 0.05, TOP - 0.35, TOP + 0.55, 5))            # beyond 60 m
    one = _line(25.0, 0.05, TOP - 0.15, TOP + 0.55, 4)                                # 1 return inside
    assert len(_find(cfg, *one)) == 1
    assert not _find(replace(cfg, hanging_min_voxels=2), *one)
    assert not _find(cfg, *_line(25.0, 0.05, TOP - 0.15, TOP - 0.05, 2))              # nothing above the top


def _cable(dist: float, bottom: float = 2.65, length: float = 1.5, lateral: float = 0.0):
    from resense.synthetic import ObstacleSpec
    return ObstacleSpec(kind="cable", size=(0.05, 0.05, length), distance=dist, lateral=lateral,
                        base_z=RAIL_HEAD_Z + bottom, reflectivity=30.0, label="thin_hanging")


def _approach(tunnel, cfg: DetectorConfig, specs_of, dists):
    """Ray-cast (occlusion-correct) the objects of every frame into the clear tunnel and run one
    detector over the sequence at 10 Hz; returns the per-frame results."""
    from resense.synthetic import inject_obstacles
    frame, _, gt = tunnel
    det = Detector(cfg)
    out = []
    for k, d in enumerate(dists):
        inj = inject_obstacles(frame, gt, specs_of(d), rng=np.random.default_rng(k))
        out.append(det.process(Frame(xyz=inj.frame.xyz, intensity=inj.frame.intensity, stamp=0.1 * k)))
    return out


# the train at 16.5 m/s (set O approaches the object at 16-17 m/s): 40 m -> 10 m in 19 frames
DISTS = [40.0 - 1.65 * k for k in range(19)]


def test_raycast_thin_hanging_object_stops(tunnel):
    """End to end on the ray-cast tunnel: the organizers' object (5 cm, 1.5 m long, its bottom
    0.35 m below the envelope top, on the axis) approached from 40 m: with the rule it STOPs
    from ~20 m on, reported as a hanging object at its distance; without it the detector never
    stops for it (the set O finding)."""
    res = _approach(tunnel, _on(), lambda d: [_cable(d)], DISTS)
    stops = [k for k, r in enumerate(res) if r.obstacle]
    assert stops, "the thin hanging object never STOPs"
    first = stops[0]
    assert DISTS[first] > 18.0 and stops == list(range(first, len(DISTS)))
    d = res[first].detections[0]
    assert abs(d.distance - DISTS[first]) < 0.5 and abs(d.lateral) < 0.2 and d.kind == "hanging"
    assert not any(r.obstacle for r in _approach(tunnel, _off(), lambda d: [_cable(d)], DISTS))


def test_raycast_real_obstacle_near_a_hanging_object_still_stops(tunnel):
    """A person-size obstacle on the axis 3 m beyond the hanging object, approached together:
    the person is a STOP on the same frame as without the rule and stays reported at its own
    distance; the hanging object is a second detection, not a replacement."""
    from resense.synthetic import ObstacleSpec

    def both(d):
        return [_cable(d), ObstacleSpec(kind="box", size=(0.4, 0.5, 1.7), distance=d + 3.0, lateral=0.0,
                                        base_z=RAIL_HEAD_Z - 0.15, reflectivity=30.0, label="person")]

    on = _approach(tunnel, _on(), both, DISTS)
    off = _approach(tunnel, _off(), both, DISTS)
    first_off = next(k for k, r in enumerate(off) if r.obstacle)
    first_on = next(k for k, r in enumerate(on) if r.obstacle)
    assert first_on <= first_off
    for k in range(first_off, len(DISTS)):
        assert on[k].obstacle
        person = [d for d in on[k].detections if d.kind != "hanging" and abs(d.distance - (DISTS[k] + 3.0)) < 1.0]
        assert person, (k, [(d.distance, d.kind) for d in on[k].detections])


def test_rail_lock_guard_on_by_default_and_skips_frames_without_rails(tunnel, monkeypatch):
    """``cluster.hanging_needs_rails`` (on since 25.09, round 2): on by default (code and both
    parameter files); the stage runs where the track model has the rail pair in the near range
    (the synthetic tunnel: the same STOP frames as without the guard) and is skipped on a frame
    without it (``track.rail_slabs == 0``: here forced after the track fit)."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(root / "configs/default.yaml")),
                DetectorConfig.from_yaml(str(root / "ros2_ws/src/resense_ros/config/detector.yaml"))):
        assert cfg.cluster.hanging_needs_rails is True
    plain = [r.obstacle for r in _approach(tunnel, _on(hanging_needs_rails=False), lambda d: [_cable(d)], DISTS)]
    guarded = _approach(tunnel, _on(), lambda d: [_cable(d)], DISTS)
    assert all(r.track.rail_slabs > 0 for r in guarded)
    assert [r.obstacle for r in guarded] == plain and any(plain)

    fit = Detector._fit_track

    def no_rails(self, *a, **kw):
        xyz = fit(self, *a, **kw)
        self.track.rail_slabs = 0
        return xyz

    monkeypatch.setattr(Detector, "_fit_track", no_rails)
    lost = _approach(tunnel, _on(), lambda d: [_cable(d)], DISTS)
    assert not any(d.kind == "hanging" for r in lost for d in r.detections)
    kept = _approach(tunnel, _on(hanging_needs_rails=False), lambda d: [_cable(d)], DISTS)
    assert any(d.kind == "hanging" for r in kept for d in r.detections)
