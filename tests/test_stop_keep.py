"""STOP hysteresis against shape signatures and scan-line frames (26.09, P3 range; EXPERIMENTS §1o,
docs/evidence/results/p3_range_2026-09-26.json). On since 26.09 (round 2, candidate B10):
``stop_keep_signature`` true, ``stop_keep_thin`` 1, ``stop_keep_min_voxels`` 10; the tests below set
the flags they test explicitly.

``tracking.stop_keep_signature``: a track reported as an obstacle (STOP) in the previous frame
counts a hit whose cluster has enough voxels inside the strict gauge but was demoted only by a
shape signature (``elevated``, ``floating``, ``edge``, ``wall_face``: ``Cluster.demoted``) as a hit
inside the gauge. A signature can keep a track from being confirmed; it does not take a confirmed
obstacle down. A column, the far-field reasons and ``overhead`` are not shape signatures here.

``tracking.stop_keep_thin``: a corridor cluster flatter than ``cluster.min_height`` (one scan line;
``Cluster.thin``) inside the strict gauge may continue a track that no other cluster matched,
within the same gate: mode 1 a track that was a STOP in the previous frame, mode 2 also a track
not yet reported whose last hit was inside the gauge. It never starts a track.

On set O the organizers' 2 x 2 m box at the envelope top (#8) is a STOP from 101.3 m, then reads
``elevated`` from 87 m (2.0-2.4 m wide, bottom 2.1-2.6 m up) and the zone vote takes the STOP
down at 77 m; at 46-33 m only one ring of it is below the envelope top (0.03-0.05 m tall) and the
track dies.
"""
from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from resense.clustering import SHAPE_SIGNATURES, Cluster, find_clusters
from resense.config import ClusterConfig, DetectorConfig, TrackingConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.tracking import Tracker


def _cl(x: float, zone: str = "gauge", reason: str = "", n_gauge: int = 20, thin: bool = False,
        lateral: float = 0.0) -> Cluster:
    c = np.array([x, lateral, 1.5])
    demoted = zone == "warning" and reason in SHAPE_SIGNATURES and n_gauge >= 3
    return Cluster(points_idx=np.arange(3), n=max(n_gauge, 5), n_raw=max(n_gauge, 5), centroid=c,
                   bbox_min=c - 0.5, bbox_max=c + 0.5, distance=x, lateral=lateral, height_min=2.2,
                   height_max=3.0, intensity=10.0, n_expected=10.0, score=1.0, zone=zone,
                   n_gauge=n_gauge, reason=reason, demoted=demoted, thin=thin)


def _run(seq, **kw):
    """seq: per frame a (clusters, thin clusters) pair; returns (reported, zone) of track 1."""
    kw = {"stop_keep_signature": False, "stop_keep_thin": 0, "stop_keep_min_voxels": 0, **kw}
    tr = Tracker(TrackingConfig(**kw))
    out = []
    for cls, thin in seq:
        tr.update(cls, ego_shift=0.0, frame_dt=0.1, thin=thin)
        t = [t for t in tr.tracks if t.id == 1]
        out.append((t[0].reported, t[0].zone) if t else (False, "gone"))
    return out


def _approach(n, x0=100.0, step=2.0):
    return [x0 - step * k for k in range(n)]


def test_shipped_defaults():
    """On since 26.09 (round 2, candidate B10): the signature keep, the scan-line keep of STOP
    tracks (mode 1), the 10-voxel bar."""
    for cfg in (DetectorConfig(), DetectorConfig.from_yaml("configs/default.yaml")):
        assert cfg.tracking.stop_keep_signature is True
        assert cfg.tracking.stop_keep_thin == 1
        assert cfg.tracking.stop_keep_min_voxels == 10


def test_signature_does_not_take_a_confirmed_stop_down():
    """6 obstacle hits (STOP from the 6th frame: 0.5 s), then 12 hits demoted as elevated: with the
    flag off the zone vote takes the STOP down once 5 of the last 10 hits are elevated (60 %
    needed); with it on the track stays a STOP."""
    xs = _approach(18)
    seq = [([_cl(x)], []) for x in xs[:6]] + [([_cl(x, "warning", "elevated")], []) for x in xs[6:]]
    off = _run(seq)
    on = _run(seq, stop_keep_signature=True)
    assert off[5] == (True, "gauge") and on[5] == (True, "gauge")
    assert off[-1] == (True, "warning")
    assert [z for _, z in off].index("warning", 5) == 10
    assert all(r == (True, "gauge") for r in on[5:])


@pytest.mark.parametrize("reason", ["elevated", "floating", "edge", "wall_face"])
def test_signature_never_makes_a_new_obstacle(reason):
    """A track demoted by a signature from its first hit stays advisory with the flag on."""
    seq = [([_cl(x, "warning", reason)], []) for x in _approach(15)]
    on = _run(seq, stop_keep_signature=True, stop_keep_thin=2)
    assert all(z == "warning" for _, z in on)


@pytest.mark.parametrize("reason", ["column", "beyond_height_ref", "beyond_axis", "overhead", "retro"])
def test_other_reasons_still_take_a_stop_down(reason):
    """Only the shape signatures are kept: a column (the column hold), the far-field reasons and
    overhead still take a confirmed STOP down."""
    xs = _approach(18)
    c = lambda x: _cl(x, "warning", reason)  # noqa: E731
    seq = [([_cl(x)], []) for x in xs[:6]] + [([c(x)], []) for x in xs[6:]]
    on = _run(seq, stop_keep_signature=True, column_hold=2)
    assert on[5] == (True, "gauge") and on[-1][1] == "warning"


def test_advisory_without_strict_voxels_is_not_kept():
    """A hit outside the strict gauge (no reason, zone warning) is not a demotion: it votes advisory."""
    xs = _approach(18)
    seq = [([_cl(x)], []) for x in xs[:6]] + [([_cl(x, "warning", "", n_gauge=1)], []) for x in xs[6:]]
    on = _run(seq, stop_keep_signature=True)
    assert on[-1] == (True, "warning")


def test_thin_continues_a_stop_track_only_in_mode_1():
    """4 frames of only a scan line inside the gauge: off, the track misses them (dropped after 3
    misses); mode 1 continues the STOP; a thin cluster never starts a track; mode 1 does not
    continue a track that is not reported."""
    xs = _approach(14)
    seq = ([([_cl(x)], []) for x in xs[:6]] + [([], [_cl(x, thin=True)]) for x in xs[6:10]]
           + [([_cl(x)], []) for x in xs[10:]])
    off = _run(seq)
    on = _run(seq, stop_keep_thin=1)
    assert off[6] == (True, "gauge") and off[7] == (False, "gauge") and off[10] == (False, "gone")
    assert all(r == (True, "gauge") for r in on[5:])
    # never starts a track
    only_thin = [([], [_cl(x, thin=True)]) for x in _approach(10)]
    tr = Tracker(TrackingConfig(stop_keep_thin=2, stop_keep_min_voxels=0))
    for cls, thin in only_thin:
        tr.update(cls, ego_shift=0.0, frame_dt=0.1, thin=thin)
    assert not tr.tracks
    # mode 1 does not help an unreported track to its confirmation
    seq2 = [([_cl(xs[0])], [])] + [([], [_cl(x, thin=True)]) for x in xs[1:4]] + [([_cl(x)], []) for x in xs[4:9]]
    m1 = _run(seq2, stop_keep_thin=1)
    m2 = _run(seq2, stop_keep_thin=2)
    first = lambda r: [k for k, (rep, z) in enumerate(r) if rep and z == "gauge"][:1]  # noqa: E731
    assert first(m2) == [4] and (first(m1) == [] or first(m1)[0] > 4)


def test_thin_outside_the_gauge_does_not_continue():
    xs = _approach(12)
    seq = [([_cl(x)], []) for x in xs[:6]] + [([], [_cl(x, "warning", "", n_gauge=1, thin=True)]) for x in xs[6:]]
    on = _run(seq, stop_keep_thin=2, stop_keep_signature=True)
    assert on[10] == (False, "gone")


def test_thin_beyond_the_gate_does_not_continue():
    xs = _approach(12)
    seq = [([_cl(x)], []) for x in xs[:6]] + [([], [_cl(x, lateral=5.0, thin=True)]) for x in xs[6:]]
    on = _run(seq, stop_keep_thin=1)
    assert on[10] == (False, "gone")


def test_find_clusters_keep_thin_and_demoted():
    """A scan line inside the envelope is dropped (min_height) without keep_thin and returned with
    ``thin`` set with it; the other clusters are unchanged. An elevated cluster with strict voxels
    is ``demoted``; a column is not."""
    cfg = ClusterConfig()
    rng = np.random.default_rng(3)
    line = np.stack([np.full(40, 60.0) + rng.uniform(0, 0.3, 40), np.linspace(-0.8, 0.8, 40),
                     np.full(40, 2.9) + rng.uniform(0, 0.02, 40)], axis=1).astype(np.float32)
    box = np.stack(np.meshgrid(np.linspace(30, 30.4, 5), np.linspace(-0.3, 0.3, 6), np.linspace(0.5, 1.5, 8),
                               indexing="ij"), axis=-1).reshape(-1, 3).astype(np.float32)
    beam = np.stack(np.meshgrid(np.linspace(45, 45.4, 4), np.linspace(-1.2, 1.2, 25), np.linspace(2.4, 2.9, 5),
                                indexing="ij"), axis=-1).reshape(-1, 3).astype(np.float32)
    col = np.stack(np.meshgrid(np.linspace(20, 20.3, 4), np.linspace(0.3, 0.6, 4), np.linspace(0.2, 2.9, 20),
                               indexing="ij"), axis=-1).reshape(-1, 3).astype(np.float32)
    pts = np.concatenate([line, box, beam, col])
    dy, h = pts[:, 1].astype(np.float64), pts[:, 2].astype(np.float64)
    ig = (np.abs(dy) <= 1.05) & (h >= 0.12) & (h <= 3.0)
    inten = np.full(pts.shape[0], 30.0, np.float32)
    a = find_clusters(pts, inten, dy, h, ig, cfg)
    b = find_clusters(pts, inten, dy, h, ig, cfg, keep_thin=True)
    assert all(not c.thin for c in a)
    thin = [c for c in b if c.thin]
    assert len(thin) == 1 and abs(thin[0].distance - 60.0) < 0.5 and thin[0].zone == "gauge"
    rest = [c for c in b if not c.thin]
    assert [(c.distance, c.zone, c.reason, c.n) for c in rest] == [(c.distance, c.zone, c.reason, c.n) for c in a]
    by = {round(c.distance): c for c in a}
    assert by[45].reason == "elevated" and by[45].demoted
    assert by[20].reason == "column" and not by[20].demoted
    assert by[30].reason == "" and not by[30].demoted


RAIL_HEAD_Z = -1.5 + 0.18      # synthetic_tunnel_frame: the bed at -1.5, rails 0.18 m tall


def _sequence(widths, cfg, x0=45.0, step=1.0):
    """Ray-cast frames of a box hanging with its bottom 2.5 m above the rail head, 0.4 m tall,
    approaching by ``step`` per frame; its width per frame from ``widths`` (a 1.6 m box is an
    obstacle, a 2.4 m one ``elevated``)."""
    from resense.synthetic import ObstacleSpec, synthetic_tunnel_frame
    det = Detector(cfg)
    out = []
    for k, w in enumerate(widths):
        spec = ObstacleSpec(kind="box", size=(0.6, w, 0.4), distance=x0 - step * k, lateral=0.0,
                            base_z=RAIL_HEAD_Z + 2.5)
        frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(5), specs=[spec])
        out.append(det.process(Frame(xyz=frame.xyz, intensity=frame.intensity, stamp=0.1 * k)))
    return out


def _cfg(sig: bool, thin: int = 0, escalation: bool = False, bar: int = 0) -> DetectorConfig:
    """The keep flags as given; the near escalation (``tracking.near_escalate_voxels``, where the
    code has it) off unless ``escalation``, so that it does not decide the box within 35 m."""
    cfg = DetectorConfig()
    extra = {} if escalation or not hasattr(cfg.tracking, "near_escalate_voxels") else {"near_escalate_voxels": 0}
    cfg.tracking = replace(cfg.tracking, stop_keep_signature=sig, stop_keep_thin=thin, stop_keep_min_voxels=bar,
                           **extra)
    return cfg


@pytest.mark.synthetic
def test_raycast_confirmed_stop_is_held_through_elevated_frames():
    """Ray-cast: a box at the envelope top (bottom 2.5 m up) 45 -> 34 m ahead is a STOP while it
    reads 1.6 m wide, then reads 2.4 m wide (``elevated``): with the flag off the zone vote takes
    the STOP down (CAUTION, ``elevated``) on the 5th elevated frame; with it on the STOP is held,
    reason ``stop_hold``."""
    widths = [1.6] * 6 + [2.4] * 6
    off = _sequence(widths, _cfg(False))
    on = _sequence(widths, _cfg(True))
    assert [r.obstacle for r in off] == [False] * 4 + [True] * 6 + [False] * 2
    assert off[-1].warning and {d.reason for d in off[-1].warnings} == {"elevated"}
    assert [r.obstacle for r in on] == [False] * 4 + [True] * 8
    assert on[-1].detections[0].reason == "stop_hold" and abs(on[-1].detections[0].distance - 34.0) < 0.6


@pytest.mark.synthetic
def test_raycast_scan_line_frames_hold_with_mode_1():
    """Ray-cast, the same box on to 26 m: at 31-33 m only one ring of it is below the envelope top
    (flatter than min_height), as for set O's box at 33-46 m; with the signature keep alone the
    STOP is lost for two frames there, with ``stop_keep_thin`` 1 it is held on every frame."""
    widths = [1.6] * 7 + [2.4] * 13
    a = _sequence(widths, _cfg(True))
    b = _sequence(widths, _cfg(True, 1))
    assert [k for k, r in enumerate(a) if not r.obstacle] == [0, 1, 2, 3, 13, 14]
    assert [k for k, r in enumerate(b) if not r.obstacle] == [0, 1, 2, 3]


@pytest.mark.synthetic
def test_raycast_elevated_structure_never_a_stop_stays_advisory():
    """Ray-cast: the same 2.4 m wide box (a beam across the corridor) from its first frame is
    advisory with both flags on: the keep rules never make a new obstacle."""
    res = _sequence([2.4] * 15, _cfg(True, 2))
    assert not any(r.obstacle for r in res)
    assert any(r.warning for r in res)


@pytest.mark.synthetic
def test_raycast_defaults_equal_the_shipped_candidate():
    widths = [1.6] * 6 + [2.4] * 6
    a = _sequence(widths, DetectorConfig())
    b = _sequence(widths, _cfg(True, 1, escalation=True, bar=10))
    assert [(r.obstacle, r.warning, r.nearest_distance) for r in a] == [(r.obstacle, r.warning, r.nearest_distance) for r in b]


def test_min_voxels_bar_round_2():
    """``tracking.stop_keep_min_voxels`` (round 2, 0 = no bar): a demoted or scan-line cluster
    keeps a STOP only with at least that many strict voxels. Round 1's ride cases: a `floating`
    cluster of 6 voxels and a bed scan line of 7 do not keep a STOP with the bar at 10; the box at
    the envelope top (16-66 strict voxels) does."""
    assert TrackingConfig().stop_keep_min_voxels == 10
    xs = _approach(18)
    few = [([_cl(x)], []) for x in xs[:6]] + [([_cl(x, "warning", "floating", n_gauge=6)], []) for x in xs[6:]]
    many = [([_cl(x)], []) for x in xs[:6]] + [([_cl(x, "warning", "elevated", n_gauge=20)], []) for x in xs[6:]]
    assert _run(few, stop_keep_signature=True)[-1] == (True, "gauge")
    assert _run(few, stop_keep_signature=True, stop_keep_min_voxels=10)[-1] == (True, "warning")
    assert _run(many, stop_keep_signature=True, stop_keep_min_voxels=10)[-1] == (True, "gauge")
    thin7 = [([_cl(x)], []) for x in xs[:6]] + [([], [_cl(x, n_gauge=7, thin=True)]) for x in xs[6:11]]
    thin20 = [([_cl(x)], []) for x in xs[:6]] + [([], [_cl(x, n_gauge=20, thin=True)]) for x in xs[6:11]]
    assert _run(thin7, stop_keep_thin=1)[10] == (True, "gauge")
    assert _run(thin7, stop_keep_thin=1, stop_keep_min_voxels=10)[10] == (False, "gone")
    assert _run(thin20, stop_keep_thin=1, stop_keep_min_voxels=10)[10] == (True, "gauge")


@pytest.mark.synthetic
def test_raycast_box_at_the_top_held_with_the_bar():
    """Ray-cast, round 2's candidate (signature keep, scan-line keep 1, bar 10): the box at the
    envelope top is held on every frame after its confirmation, as without the bar."""
    cfg = _cfg(True, 1, bar=10)
    res = _sequence([1.6] * 7 + [2.4] * 13, cfg)
    assert [k for k, r in enumerate(res) if not r.obstacle] == [0, 1, 2, 3]
