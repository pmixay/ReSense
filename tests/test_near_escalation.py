"""Near-field escalation (26.09, P3; judge B action 6; docs/evidence/results/p3_near_escalation_2026-09-26.json,
EXPERIMENTS §1l): ``tracking.near_escalate_voxels`` N > 0 makes a track whose last
``near_escalate_hits`` hits were each a corridor cluster with at least N voxels inside the strict
envelope within ``near_escalate_distance`` an obstacle (STOP), whatever demoted it - except a
column, and the column hold keeps precedence.

On set O the 2 x 2 m box at the envelope top (#8) is ``elevated`` (a 2 m wide cluster with its
bottom above 1.2 m) and advisory at 0-50 m although its bottom is 2.8 m above the rail head,
inside the 3.0 m envelope; the 0.3 m cube at the envelope edge (#4) is ``floating``.
"""
from __future__ import annotations

import numpy as np
import pytest

from resense.clustering import Cluster, find_clusters
from resense.config import ClusterConfig, DetectorConfig, GaugeConfig, TrackingConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.gauge import gauge_core_mask, point_in_polygon
from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
from resense.tracking import Tracker

RAIL_HEAD_Z = -1.5 + 0.18      # synthetic_tunnel_frame: the bed at -1.5, rails 0.18 m tall
N_FRAMES = 10


def _cfg(on: bool) -> DetectorConfig:
    cfg = DetectorConfig()
    cfg.tracking.near_escalate_voxels = 10 if on else 0
    cfg.tracking.near_escalate_distance = 35.0
    cfg.tracking.near_escalate_hits = 5
    return cfg


def _run(spec: ObstacleSpec, cfg: DetectorConfig):
    frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(5), specs=[spec])
    det = Detector(cfg)
    return [det.process(Frame(xyz=frame.xyz, intensity=frame.intensity, stamp=0.1 * k)) for k in range(N_FRAMES)]


def _box_at_envelope_top(distance: float) -> ObstacleSpec:
    """A 2.4 m wide box hanging from 2.6 m above the rail head: its bottom 0.4 m inside the 3.0 m
    envelope, the cluster ``elevated`` (bottom above 1.2 m, wider than 2.0 m)."""
    return ObstacleSpec(kind="box", size=(1.0, 2.4, 0.6), distance=distance, lateral=0.0,
                        base_z=RAIL_HEAD_Z + 2.6)


@pytest.mark.synthetic
@pytest.mark.parametrize("distance", [20.0, 25.0, 30.0])
def test_advisory_object_inside_the_envelope_near_the_train_becomes_a_stop(distance):
    """Ray-cast: the box inside the envelope top 20-30 m ahead is advisory (elevated) with the
    rule off, and a STOP from its 5th frame with it on, at its distance, marked ``near_envelope``."""
    spec = _box_at_envelope_top(distance)
    off = _run(spec, _cfg(False))
    assert not any(r.obstacle for r in off)
    assert all(r.warning for r in off[4:])
    assert {d.reason for r in off[4:] for d in r.warnings} == {"elevated"}
    on = _run(spec, _cfg(True))
    assert [k for k, r in enumerate(on) if r.obstacle] == list(range(4, N_FRAMES))
    d = on[4].detections[0]
    assert d.zone == "gauge" and d.reason == "near_envelope" and abs(d.distance - distance) < 0.6
    assert not on[4].warnings


@pytest.mark.synthetic
def test_advisory_structure_outside_the_strict_envelope_stays_advisory():
    """Ray-cast: a 0.3 m cube in the advisory zone just outside the strict envelope (the
    organizers' #5: 1.12-1.42 m off the axis, 1.0-1.3 m up) 25 m ahead is advisory with the rule
    on as off: none of its voxels is inside the strict envelope."""
    spec = ObstacleSpec(kind="box", size=(0.3, 0.3, 0.3), distance=25.0, lateral=1.27, base_z=RAIL_HEAD_Z + 1.0)
    for on in (False, True):
        res = _run(spec, _cfg(on))
        assert not any(r.obstacle for r in res), on
        assert all(r.warning for r in res[4:]), on


@pytest.mark.synthetic
def test_box_beyond_the_escalation_distance_stays_advisory():
    """The same box at the envelope top 45 m ahead: beyond ``near_escalate_distance`` (35 m) it
    stays advisory with the rule on."""
    res = _run(_box_at_envelope_top(45.0), _cfg(True))
    assert not any(r.obstacle for r in res)
    assert any(r.warning for r in res)


def _cluster(x: float, n_gauge: int, reason: str = "elevated", zone: str = "warning") -> Cluster:
    c = np.array([x, 0.0, 1.5])
    return Cluster(points_idx=np.arange(3), n=max(n_gauge, 5), n_raw=max(n_gauge, 5), centroid=c,
                   bbox_min=c - 0.5, bbox_max=c + 0.5, distance=x, lateral=0.0, height_min=2.7,
                   height_max=3.0, intensity=10.0, n_expected=10.0, score=1.0, zone=zone,
                   n_gauge=n_gauge, reason=reason)


def _track_zones(seq, **kw):
    cfg = TrackingConfig(near_escalate_voxels=10, near_escalate_distance=35.0, near_escalate_hits=5, **kw)
    tr = Tracker(cfg)
    out = []
    for k, (x, ng, reason) in enumerate(seq):
        tr.update([_cluster(x, ng, reason)], ego_shift=0.0, frame_dt=0.1)
        t = tr.tracks[0]
        out.append((t.reported, t.zone))
    return out


def test_escalation_needs_the_last_hits_in_a_row():
    """The last 5 hits must each have >= N strict voxels within D: one hit short of N (or beyond D)
    restarts the count; the zone vote alone keeps the track advisory until then."""
    seq = [(30.0, 12, "elevated")] * 4 + [(30.0, 9, "elevated")] + [(30.0, 12, "elevated")] * 5
    zones = [z for _, z in _track_zones(seq)]
    assert zones[:9] == ["warning"] * 9 and zones[9] == "gauge"
    far = [(40.0 - k, 50, "elevated") for k in range(10)]           # 40 -> 31 m: near from 35 m
    zones = [z for _, z in _track_zones(far)]
    assert zones.index("gauge") == 9                                 # hits at 35, 34, 33, 32, 31 m


@pytest.mark.parametrize("reason", ["beyond_axis", "beyond_height_ref"])
def test_untrusted_reference_is_never_escalated(reason):
    """Safety review of 26.09: a cluster demoted because the corridor's axis (``beyond_axis``) or
    height reference (``beyond_height_ref``) is not trusted there never counts as a near hit: its
    strict voxels are not trusted either."""
    assert set(z for _, z in _track_zones([(30.0, 120, reason)] * 10)) == {"warning"}
    assert not Tracker(TrackingConfig(near_escalate_voxels=10))._near(_cluster(30.0, 120, reason))


def test_column_is_never_escalated_and_the_column_hold_keeps_precedence():
    """A column (the ride's column row seen through a wrong axis at a crossover: 50-150 strict
    voxels at 20-40 m) never counts as a near hit, and a track held advisory by the column hold
    stays advisory even after 5 near hits of another demotion."""
    zones = [z for _, z in _track_zones([(30.0, 120, "column")] * 10)]
    assert set(zones) == {"warning"}
    seq = [(30.0, 120, "column")] * 2 + [(30.0, 120, "elevated")] * 7
    zones = [z for _, z in _track_zones(seq)]
    assert set(zones) == {"warning"}                                  # 2 column hits in the last 10
    zones = [z for _, z in _track_zones(seq, column_hold=0)]
    assert zones[6] == "gauge"


def _edge_face(x0: float, dy0: float):
    """A 1.95 m tall face at the corridor side (candidate D, set O #6): 0.4 m along X from x0,
    its points from dy0 to 1.38 m off the axis, 0.15-2.10 m above the rail head."""
    xs, ys, zs = np.meshgrid(np.arange(x0, x0 + 0.41, 0.05), np.arange(dy0, 1.39, 0.05),
                             np.arange(0.15, 2.11, 0.05), indexing="ij")
    xyz = np.stack([xs.ravel(), ys.ravel(), zs.ravel()], axis=1).astype(np.float32)
    dy, h = xyz[:, 1].astype(np.float64), xyz[:, 2].astype(np.float64)
    g = GaugeConfig()
    ing = point_in_polygon(dy, h, g.profile) & gauge_core_mask(dy, h, xyz[:, 0], g)
    return xyz, dy, h, ing, g


@pytest.mark.parametrize("x0,dy0,kept", [(10.0, 1.03, True), (25.0, 1.03, False), (10.0, 1.08, False)])
def test_wall_keep_spares_a_side_face_with_strict_voxels_near_the_train(x0, dy0, kept):
    """``cluster.wall_keep_gauge_voxels`` (candidate D): a face at the corridor side, taller than
    1.9 m with its centroid > 1.2 m off the axis, is dropped as a wall with the flag off; with it
    on it is kept (an obstacle) when it has >= 10 strict-envelope voxels within 20 m, and still
    dropped beyond 20 m or without strict voxels."""
    xyz, dy, h, ing, g = _edge_face(x0, dy0)
    assert dy.mean() > 1.2
    inten = np.full(len(xyz), 10.0, np.float32)
    assert find_clusters(xyz, inten, dy, h, ing, ClusterConfig(wall_keep_gauge_voxels=0), gauge=g) == []
    out = find_clusters(xyz, inten, dy, h, ing, ClusterConfig(wall_keep_gauge_voxels=10, wall_keep_distance=20.0), gauge=g)
    if kept:
        assert len(out) == 1 and out[0].zone == "gauge" and out[0].n_gauge >= 10 and out[0].wall_kept
    else:
        assert out == []


def test_wall_keep_counts_the_rails_envelope_only():
    """Safety review of 26.09: the wall keep counts the voxels inside the envelope measured from the
    rails (``in_rail``), not the strict membership widened by ``gauge.axis_union``: a face with
    none there is dropped as a wall however many a wider ``in_gauge`` gives it."""
    xyz, dy, h, ing, g = _edge_face(10.0, 1.08)
    assert not ing.any()
    inten = np.full(len(xyz), 10.0, np.float32)
    wide = np.abs(dy) <= 1.2
    ccfg = ClusterConfig(wall_keep_gauge_voxels=10, wall_keep_distance=20.0)
    assert len(find_clusters(xyz, inten, dy, h, wide, ccfg, gauge=g)) == 1          # in_rail = in_gauge
    assert find_clusters(xyz, inten, dy, h, wide, ccfg, gauge=g, in_rail=ing) == []


def _low_at(x: float, lateral: float) -> Cluster:
    c = np.array([x + 0.15, lateral, -1.25])
    return Cluster(points_idx=np.arange(3), n=8, n_raw=12, centroid=c, bbox_min=c - [0.15, 0.15, 0.05],
                   bbox_max=c + [0.15, 0.15, 0.05], distance=x, lateral=lateral, height_min=0.05,
                   height_max=0.15, intensity=10.0, n_expected=8.0, score=1.0, zone="gauge", n_gauge=8,
                   kind="low")


def _side_blob(x: float, wall_kept: bool) -> Cluster:
    c = np.array([x + 0.5, 1.3, 0.0])
    return Cluster(points_idx=np.arange(3), n=40, n_raw=60, centroid=c, bbox_min=c - [0.5, 0.25, 1.0],
                   bbox_max=c + [0.5, 0.25, 1.0], distance=x, lateral=1.3, height_min=0.2, height_max=2.2,
                   intensity=10.0, n_expected=30.0, score=1.0, zone="warning", n_gauge=12, reason="column",
                   wall_kept=wall_kept)


def test_a_demoted_wall_kept_blob_does_not_remove_a_low_object_beside_it():
    """Safety review of 26.09: a blob kept only by the wall keep and then demoted (here a column) is
    not a duplicate source for a low object beside it (it would have been dropped without the wall
    keep, and the low object reported); an ordinary advisory column still is, as before."""
    from resense.detector import Candidates
    det = Detector(DetectorConfig())
    low = _low_at(10.0, 0.7)
    empty = Candidates(xyz=np.zeros((0, 3), np.float32), dy=np.zeros(0), h=np.zeros(0),
                       in_gauge=np.zeros(0, bool), intensity=np.zeros(0, np.float32),
                       idx=np.zeros(0, np.int64), low=np.zeros(0, bool))
    assert det._not_part_of_corridor_objects([low], [], [_side_blob(10.0, True)], empty) == [low]
    assert det._not_part_of_corridor_objects([low], [], [_side_blob(10.0, False)], empty) == []


def test_shipped_defaults_are_candidates_a_and_d():
    """Shipped 26.09: candidate A of the pre-registration (N 10, D 35 m, 5 hits) and D (10 strict
    voxels within 20 m), the same in the dataclass and in configs/default.yaml."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(root / "configs/default.yaml"))):
        t = cfg.tracking
        assert (t.near_escalate_voxels, t.near_escalate_distance, t.near_escalate_hits) == (10, 35.0, 5)
        assert (cfg.cluster.wall_keep_gauge_voxels, cfg.cluster.wall_keep_distance) == (10, 20.0)


def test_off_changes_nothing():
    """With N = 0 (off) no track carries a near history and an advisory track stays advisory."""
    tr = Tracker(TrackingConfig(near_escalate_voxels=0))
    for _ in range(8):
        tr.update([_cluster(30.0, 120)], ego_shift=0.0, frame_dt=0.1)
    t = tr.tracks[0]
    assert t.near_hits == 0 and t.near_hist == [] and t.zone == "warning" and not t.escalated


def _low_rail(x: float) -> Cluster:
    """A low (bed-level) cluster that ``lowobj.mark_rail_line`` marked as rail geometry, with >= N
    strict voxels, where ``_cluster`` puts its cluster (so the tracker associates the two)."""
    c = _cluster(x, 12, reason="", zone="gauge")
    c.kind, c.rail_line = "low", True
    return c


def _mixed(rail_within: float):
    tr = Tracker(TrackingConfig(near_escalate_voxels=10, near_escalate_distance=35.0, near_escalate_hits=5))
    out = []
    for cl in [_cluster(3.5, 12)] * 6 + [_low_rail(3.5)] + [_cluster(3.5, 12)] * 6:
        tr.update([cl], ego_shift=0.0, frame_dt=0.1, rail_within=rail_within)
        out.append([(t.id, t.reported, t.zone, t.escalated) for t in tr.tracks])
    return out


def test_near_escalation_and_rail_start_act_on_disjoint_clusters():
    """Integration of 26.09 (EXPERIMENTS §1k, §1l): both rules decide in the tracker. A low cluster
    never counts as a near hit, so a track of rail-line clusters under 4 m is never escalated (the
    rail-start rule withholds it); and the rail-start rule only withholds a track not yet reported
    whose last hit is a rail-line cluster, in a frame where the escalation's last hits are broken
    anyway. A track escalated to a STOP whose clusters are once a rail-line cluster under 4 m
    behaves the same with the rail-start rule on as off."""
    tr = Tracker(TrackingConfig(near_escalate_voxels=10, near_escalate_distance=35.0, near_escalate_hits=5))
    assert not tr._near(_low_rail(3.0))
    for _ in range(8):
        tr.update([_low_rail(3.0)], ego_shift=0.0, frame_dt=0.1, rail_within=4.0)
    assert len(tr.tracks) == 1 and not tr.tracks[0].near_escalated and not tr.tracks[0].reported
    on, off = _mixed(4.0), _mixed(0.0)
    assert on == off
    assert on[5] == [(1, True, "gauge", True)] and on[-1] == [(1, True, "gauge", True)]
