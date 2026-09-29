"""Checks for the far rail evidence (resense/farrails.py), its opt-in use in the track check
(``track.rails_far_rings``) and its yield tool (scripts/far_rail_yield.py).

The analytic scene (a bed plane and two rail heads intersected with the real Pandar128 ring grid)
needs nothing; the ray-cast tunnel tests use the ``tunnel`` fixture (Open3D).
"""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from resense import farrails as fr
from resense.sensor import ray_directions

_script = Path(__file__).resolve().parents[1] / "scripts" / "far_rail_yield.py"
_spec = importlib.util.spec_from_file_location("far_rail_yield", _script)
assert _spec is not None and _spec.loader is not None
tool = importlib.util.module_from_spec(_spec)
sys.modules["far_rail_yield"] = tool
_spec.loader.exec_module(tool)

FLOOR_Z = -1.5
HEAD = 0.07


def _scene(center=0.25, gauge=1.6, bumps=(), head=HEAD, rails=True):
    """Rays of the real ring grid onto a bed plane, with the two rail heads (and any extra bump
    ``(lateral_centre, height)``) standing on it: (xyz, ring index of the points)."""
    d = ray_directions().astype(np.float64)
    d = d[d[:, 2] < -1e-4]
    t_bed = FLOOR_Z / d[:, 2]
    p = d * t_bed[:, None]
    tops = [(center - gauge / 2, head), (center + gauge / 2, head)] if rails else []
    tops += list(bumps)
    for lateral, height in tops:
        t_top = (FLOOR_Z + height) / d[:, 2]
        y_top = d[:, 1] * t_top
        hit = (np.abs(y_top - lateral) < 0.045) & (t_top > 0)
        p[hit] = d[hit] * t_top[hit, None]
    ok = (p[:, 0] > 1.0) & (p[:, 0] < 120.0)
    return p[ok].astype(np.float32), fr.ring_index(p[ok])


def _model(center=0.25):
    return SimpleNamespace(center=center, yaw=0.0, rail_z=lambda x: np.full_like(np.asarray(x, float), FLOOR_Z + HEAD),
                           center_y=lambda x: center + 0.0 * np.asarray(x, float))


def test_ring_index_finds_every_ring_of_the_grid():
    d = ray_directions().astype(np.float64) * 50.0
    ring = fr.ring_index(d)
    assert np.all(ring >= 0)
    assert np.unique(ring).size == 128


def test_ring_index_band_only_labels_the_far_corridor():
    d = ray_directions().astype(np.float64) * 50.0
    full = fr.ring_index(d)
    band = (20.0, 100.0, 6.0, 0.5)
    inside = (d[:, 0] > 20.0) & (d[:, 0] < 100.0) & (np.abs(d[:, 1]) < 6.0) & (d[:, 2] < 0.5)
    got = fr.ring_index(d, band=band)
    assert got.shape == full.shape
    assert np.array_equal(got[inside], full[inside])
    assert np.all(got[~inside] == -1)


def test_a_tilted_frame_loses_its_rings():
    """Why ring identity is taken before the mount correction: 3 deg of roll smears every ring across
    the azimuth and most returns fall between two ring elevations."""
    d = ray_directions().astype(np.float64) * 50.0
    roll = np.radians(3.0)
    rot = np.array([[1, 0, 0], [0, np.cos(roll), -np.sin(roll)], [0, np.sin(roll), np.cos(roll)]])
    assert np.mean(fr.ring_index(d) >= 0) == 1.0
    assert np.mean(fr.ring_index(d @ rot.T) >= 0) < 0.6


@pytest.mark.parametrize("center", [0.25, -0.4])
def test_far_rails_recover_the_analytic_rails(center):
    xyz, ring = _scene(center=center)
    out = fr.far_rails(xyz, ring, _model(center), (28.0, center))
    assert out.n >= 8
    assert out.x.max() > 50.0
    assert np.max(np.abs(out.y - center)) < 0.05


def test_without_rail_heads_there_are_no_stations():
    xyz, ring = _scene(rails=False)
    out = fr.far_rails(xyz, ring, _model(), (28.0, 0.25))
    assert out.n == 0


def test_bumps_at_the_wrong_gauge_do_not_make_pairs():
    """A platform edge and a kerb 1.2 m apart (and not 1.59 m) are not a rail pair."""
    xyz, ring = _scene(rails=False, bumps=[(0.25 - 0.6, 0.10), (0.25 + 0.6, 0.10)])
    assert fr.far_rails(xyz, ring, _model(), (28.0, 0.25)).n == 0


def test_a_second_rail_pair_off_the_axis_does_not_steer_the_result():
    """A parallel pair 0.7 m to the side on part of the track (a switch blade) is one more source of
    candidates; the rails that agree on one smooth curve from the anchor win."""
    xyz, ring = _scene(bumps=[(0.25 + 0.7 - 0.8, 0.09), (0.25 + 0.7 + 0.8, 0.09)])
    out = fr.far_rails(xyz, ring, _model(), (28.0, 0.25))
    assert out.n >= 8
    assert np.median(np.abs(out.y - 0.25)) < 0.05


def test_consensus_rejects_inconsistent_candidates():
    p = fr.FarRailParams()
    s = np.array([32.0, 38.0, 44.0, 50.0, 56.0, 41.0, 47.0, 53.0])
    e = np.array([0.02, 0.03, 0.02, 0.04, 0.03, 0.55, -0.60, 0.50])     # the last three are outliers
    mask, curve = fr.consensus(s, e, 28.0, 0.0, p)
    assert mask.tolist() == [True] * 5 + [False] * 3
    assert curve is not None and abs(curve[0]) <= p.max_slope and abs(curve[1]) <= p.max_curv


def test_consensus_of_nothing_is_nothing():
    mask, curve = fr.consensus(np.empty(0), np.empty(0), 28.0, 0.0, fr.FarRailParams())
    assert mask.size == 0 and curve is None


def test_one_station_is_not_enough():
    xyz, ring = _scene()
    # between the anchor (28 m) and 29.5 m the scene holds a single ring crossing
    assert fr.far_rails(xyz, ring, _model(), (28.0, 0.25), fr.FarRailParams(x_max=29.5)).n == 0
    assert fr.far_rails(xyz, ring, _model(), (28.0, 0.25), fr.FarRailParams(x_max=34.0, min_stations=5)).n == 0
    assert fr.far_rails(xyz, ring, _model(), (28.0, 0.25), fr.FarRailParams(x_max=34.0, min_stations=3)).n >= 3


def test_axis_disagreement_rule_of_check_far_rails():
    model = SimpleNamespace(center_y=lambda x: 0.0 * np.asarray(x, float))
    x = np.array([40.0, 60.0])

    def rails(y):
        return fr.FarRails(x=x, y=np.asarray(y, float))

    assert fr.would_correct_axis(rails([0.4, 0.5]), model, 0.05, 0.3)         # same side, one beyond 0.3 m
    assert not fr.would_correct_axis(rails([0.1, 0.2]), model, 0.05, 0.3)     # within the tolerance
    assert not fr.would_correct_axis(rails([0.4, -0.5]), model, 0.05, 0.3)    # opposite sides: noise
    assert not fr.would_correct_axis(rails([0.02, 0.5]), model, 0.05, 0.3)    # one within half a bin
    assert not fr.would_correct_axis(fr.FarRails(), model, 0.05, 0.3)


def test_far_rails_in_the_raycast_tunnel(tunnel):
    frame, _, gt = tunnel
    out = fr.far_rails(frame.xyz, fr.ring_index(frame.xyz), gt, (28.0, gt.center))
    assert out.n >= 8
    assert out.x.max() > 50.0
    assert np.max(np.abs(out.y - gt.center)) < 0.06


def test_measure_reports_far_rails_on_the_raycast_tunnel(tunnel):
    from resense.config import DetectorConfig
    frame, _, _ = tunnel
    frames = []
    for k in range(2):
        f = type(frame)(xyz=frame.xyz.copy(), intensity=frame.intensity.copy(), ring=None, stamp=0.1 * k,
                        frame_id=frame.frame_id, meta=dict(frame.meta))
        frames.append((k, f))
    res = tool.measure(iter(frames), DetectorConfig(), fr.FarRailParams())
    assert res["frames"] == 2
    assert res["frames_with_near_rails"] == 2
    assert res["frames_with_far_rails"] == 2
    assert res["frames_where_check_far_rails_would_act"] == 0
    assert res["median_abs_axis_error_m_median"] < 0.1


def _setup(tunnel, **flags):
    from dataclasses import replace

    from resense.config import TrackConfig
    from resense.track import estimate_rails, estimate_track
    frame, _, _ = tunnel
    off = TrackConfig()
    cfg = replace(off, **flags)
    model = estimate_track(frame.xyz, off, prev=None)
    near = estimate_rails(frame.xyz, model, cfg, model.center, prior=model)
    return frame, off, cfg, model, near


def test_the_ring_argument_changes_nothing_while_the_flags_are_off(tunnel):
    from resense.track import estimate_track
    frame, off, _, _, _ = _setup(tunnel)
    ring = fr.ring_index(frame.xyz)
    plain = estimate_track(frame.xyz, off, prev=None).to_dict()
    assert estimate_track(frame.xyz, off, prev=None, ring=ring).to_dict() == plain


def test_walls_that_agree_with_the_rails_are_left_alone_with_the_flags_on(tunnel):
    from dataclasses import replace

    from resense.track import estimate_track
    frame, off, _, _, _ = _setup(tunnel)
    on = replace(off, rails_far_check_enabled=True, rails_far_rings=True)
    ring = fr.ring_index(frame.xyz)
    assert estimate_track(frame.xyz, on, prev=None, ring=ring).to_dict() == \
        estimate_track(frame.xyz, off, prev=None).to_dict()


def test_ring_evidence_replaces_a_wall_bend_the_rails_contradict(tunnel):
    from dataclasses import replace

    from resense.track import _check_far_rails
    frame, _, cfg, model, near = _setup(tunnel, rails_far_check_enabled=True, rails_far_rings=True)
    bent = replace(model, curvature=0.0015, axis_sides=2, axis_valid=200.0)     # a station hall's wall bend
    slab = replace(model, curvature=0.0015, axis_sides=2, axis_valid=200.0)
    _check_far_rails(frame.xyz, slab, replace(cfg, rails_far_rings=False), near, None)
    assert slab.curvature == 0.0015                                          # the slab profile never finds the far pair
    _check_far_rails(frame.xyz, bent, cfg, near, fr.ring_index(frame.xyz))
    assert abs(bent.curvature) < 2e-4
    assert bent.axis_valid < 200.0
    assert abs(bent.center_y(60.0) - tunnel[2].center) < 0.15               # the axis follows the straight rails


def test_no_ring_index_no_ring_evidence(tunnel):
    """Without the per-point ring index the ring source has nothing to work with: the slab path runs, as before."""
    from dataclasses import replace

    from resense.track import _check_far_rails
    frame, _, cfg_on, model, near = _setup(tunnel, rails_far_check_enabled=True, rails_far_rings=True)
    cfg_slab = replace(cfg_on, rails_far_rings=False)
    a = replace(model, curvature=0.0015, axis_sides=2, axis_valid=200.0)
    b = replace(model, curvature=0.0015, axis_sides=2, axis_valid=200.0)
    _check_far_rails(frame.xyz, a, cfg_on, near, None)
    _check_far_rails(frame.xyz, b, cfg_slab, near, fr.ring_index(frame.xyz))
    assert (a.center, a.yaw, a.curvature, a.axis_valid) == (b.center, b.yaw, b.curvature, b.axis_valid)


def test_the_experimental_profile_turns_both_flags_on():
    from resense.config import DetectorConfig
    root = Path(__file__).resolve().parents[1]
    exp = DetectorConfig.from_yaml(str(root / "configs" / "experimental_far_rail_rings.yaml"))
    base = DetectorConfig()
    assert (base.track.rails_far_check_enabled, base.track.rails_far_rings) == (False, False)
    assert (exp.track.rails_far_check_enabled, exp.track.rails_far_rings) == (True, True)


def test_the_detector_runs_with_the_experimental_profile_and_matches_the_default_on_a_clean_tunnel(tunnel):
    """The whole detector with both flags on: the ring index is taken from the uncorrected frame,
    the far evidence agrees with the walls, so the track model is what the default gives."""
    from resense.config import DetectorConfig
    from resense.detector import Detector
    frame, _, _ = tunnel
    root = Path(__file__).resolve().parents[1]
    cfgs = (DetectorConfig(), DetectorConfig.from_yaml(str(root / "configs" / "experimental_far_rail_rings.yaml")))
    models = []
    for cfg in cfgs:
        det = Detector(cfg)
        for k in range(2):
            f = type(frame)(xyz=frame.xyz.copy(), intensity=frame.intensity.copy(), ring=None, stamp=0.1 * k,
                            frame_id=frame.frame_id, meta=dict(frame.meta))
            res = det.process(f)
        models.append(res.track.to_dict())
    assert models[0] == models[1]
