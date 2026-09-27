"""27.09 (P4, processing-history dependence): the opt-in rules that make a STOP depend less on
which frames the node happened to process - the zone vote over a minimum number of hits
(``tracking.zone_min_votes``), the approach allowance of the association gate along the track only
(``tracking.gate_along_only``), a STOP started only on a hit inside the gauge
(``tracking.start_clean``), the column width of the body (``cluster.column_width_trim``) and the
bounded disagreement hold of the axis trust (``track.axis_disagree_hold``). ``gate_along_only`` and
``column_width_trim`` are on since 27.09; the other defaults keep the earlier behaviour."""
from __future__ import annotations

import numpy as np

import resense.track as track_mod
from resense.clustering import Cluster, _advisory_reason, _Blob
from resense.config import ClusterConfig, TrackConfig, TrackingConfig
from resense.synthetic import synthetic_tunnel_frame
from resense.tracking import Track, Tracker


def _cluster(x: float, y: float = 0.0, zone: str = "gauge", n_gauge: int = 20) -> Cluster:
    c = np.array([x, y, 1.0])
    return Cluster(points_idx=np.arange(3), n=20, n_raw=20, centroid=c, bbox_min=c - 0.3, bbox_max=c + 0.3,
                   distance=x - 0.3, lateral=y, height_min=0.5, height_max=1.5, intensity=0.0, n_expected=10.0,
                   score=1.0, zone=zone, n_gauge=n_gauge if zone == "gauge" else 0)


def test_shipped_defaults_of_27_09():
    # shipped: the along-track gate and the column body width; the vote minimum, start_clean and the
    # axis hold stay off (they cost set F / set O positives or monitored range, docs/QUALITY_CYCLE_2026-09-27.md)
    t, k, c = TrackingConfig(), TrackConfig(), ClusterConfig()
    assert t.zone_min_votes == 0 and t.gate_along_only is True and t.start_clean is False
    assert k.axis_disagree_hold == 0 and c.column_width_trim == 0.05 and c.column_width_trim_min_cut == 0.25


def test_zone_vote_counts_a_minimum_number_of_hits():
    tr = Track(id=1, centroid=np.zeros(3), velocity=np.zeros(3), zone_hist=[True, True, False], zone_min_fraction=0.6)
    assert tr.vote_zone == "gauge"                      # 2 of 3 >= 60 %
    tr.zone_min_votes = 5
    assert tr.vote_zone == "warning"                    # 2 of (at least) 5 < 60 %
    tr.zone_hist = [True, True, True]
    assert tr.vote_zone == "gauge"                      # 3 of 5 = 60 %
    tr.zone_hist = [True, True, True, False, True, False]
    assert tr.vote_zone == "gauge"                      # more hits than the minimum: the plain vote


def _one_match(cfg: TrackingConfig, first: Cluster, second: Cluster, dt: float = 0.1) -> bool:
    tk = Tracker(cfg)
    tk.update([first], frame_dt=dt)
    tid = tk.tracks[0].id
    tk.update([second], frame_dt=dt)
    return any(t.id == tid and t.hits == 2 for t in tk.tracks)


def test_gate_along_only_keeps_the_approach_but_not_a_jump_across_the_track():
    base = TrackingConfig(gate_along_only=False)
    along = TrackingConfig(gate_along_only=True)
    # gate at 50 m: 1.5 + 0.02 * 50 = 2.5 m, approach allowance 25 m/s x 0.1 s = 2.5 m
    near_4m = (_cluster(50.0), _cluster(46.0))           # 4 m nearer, straight ahead: an approach
    assert _one_match(base, *near_4m) and _one_match(along, *near_4m)
    jump = (_cluster(50.0), _cluster(48.0, y=3.0))       # 2 m nearer and 3 m across the track
    assert _one_match(base, *jump)                       # 3.6 m <= 2.5 + 2.5: joined
    assert not _one_match(along, *jump)                  # 3.0 m across > 2.5 m: a new track
    # after two dropped frames (0.3 s) the old gate grows to 2.5 + 7.5 = 10 m in every direction
    far_jump = (_cluster(50.0), _cluster(47.0, y=5.0))
    assert _one_match(base, *far_jump, dt=0.3)
    assert not _one_match(along, *far_jump, dt=0.3)
    assert _one_match(along, _cluster(50.0), _cluster(43.0, y=0.5), dt=0.3)


def _run(cfg: TrackingConfig, zones):
    tk = Tracker(cfg)
    out = []
    for i, z in enumerate(zones):
        tk.update([_cluster(50.0, zone=z)], frame_dt=0.1)
        out.append([(t.zone, t.reported) for t in tk.tracks if t.reported])
    return out


def test_start_clean_waits_for_a_hit_inside_the_gauge():
    zones = ["gauge"] * 4 + ["warning", "gauge", "gauge"]
    base = _run(TrackingConfig(), zones)
    clean = _run(TrackingConfig(start_clean=True), zones)
    assert base[4] == [("gauge", True)]                 # the vote (4 of 5) confirms on an advisory hit
    assert clean[4] == []                               # not started on it ...
    assert clean[5] == [("gauge", True)]                # ... but on the next hit inside the gauge
    assert base[5:] == clean[5:]


def _column_blob(fragment: bool) -> tuple:
    rng = np.random.default_rng(0)
    n = 140
    body = np.column_stack([60.0 + rng.uniform(0, 0.5, n), rng.uniform(0.2, 0.9, n), rng.uniform(0.2, 2.9, n)])
    pts = body
    if fragment:                                        # 7 returns joined 1.5 m along and 0.4 m across
        frag = np.column_stack([61.9 + rng.uniform(0, 0.1, 7), rng.uniform(0.95, 1.3, 7), rng.uniform(2.5, 2.8, 7)])
        pts = np.vstack([body, frag])
    idx = np.arange(pts.shape[0])
    b = _Blob.of(pts, idx, pts.shape[0] // 2)
    dy = pts[:, 1].copy()
    h = pts[:, 2].copy()
    return b, dy, h


def test_column_width_of_the_body_not_of_a_joined_fragment():
    cfg = ClusterConfig(column_width_trim=0.0)
    trim = ClusterConfig(column_width_trim=0.05)
    b, dy, h = _column_blob(fragment=False)
    lat = float(dy.mean())
    assert _advisory_reason(b, 60.0, lat, "gauge", dy, h, cfg, 1e9, None) == "column"
    b, dy, h = _column_blob(fragment=True)
    lat = float(dy.mean())
    assert b.size[1] > cfg.column_max_width             # the box is 1.1 m wide
    assert _advisory_reason(b, 60.0, lat, "gauge", dy, h, cfg, 1e9, None) != "column"
    assert _advisory_reason(b, 60.0, lat, "gauge", dy, h, trim, 1e9, None) == "column"


def test_column_width_trim_leaves_a_dense_body_its_width():
    rng = np.random.default_rng(2)
    n = 400                                             # a dense 1.05 m wide, 2.8 m tall body: tails 0.1 m
    pts = np.column_stack([40.0 + rng.uniform(0, 0.4, n), rng.uniform(0.35, 1.4, n), rng.uniform(0.0, 2.8, n)])
    b = _Blob.of(pts, np.arange(n), n)
    on, off = ClusterConfig(column_width_trim=0.05), ClusterConfig(column_width_trim=0.0)
    lat = float(pts[:, 1].mean())
    assert (_advisory_reason(b, 40.0, lat, "gauge", pts[:, 1], pts[:, 2], on, 1e9, None)
            == _advisory_reason(b, 40.0, lat, "gauge", pts[:, 1], pts[:, 2], off, 1e9, None))


def test_column_width_trim_leaves_a_wide_object_wide():
    rng = np.random.default_rng(1)
    n = 200                                             # a 1.6 m wide, 2.5 m tall body: never a column
    pts = np.column_stack([40.0 + rng.uniform(0, 0.5, n), rng.uniform(-0.8, 0.8, n), rng.uniform(0.2, 2.7, n)])
    b = _Blob.of(pts, np.arange(n), n)
    trim = ClusterConfig(column_width_trim=0.05)
    assert _advisory_reason(b, 40.0, 0.0, "gauge", pts[:, 1], pts[:, 2], trim, 1e9, None) != "column"


def _axis_sequence(monkeypatch, cfg: TrackConfig, sides):
    """Run estimate_track on one synthetic frame per entry of ``sides`` with the boundary fit
    replaced: 2 = two disagreeing boundaries, 1 = one boundary, 3 = two agreeing ones."""
    frame, _, _ = synthetic_tunnel_frame(rng=np.random.default_rng(0), specs=[])
    real = track_mod.estimate_axis_from_walls
    state = {"n": 2}

    def fake(xyz, model, c, t_fixed, floor_z_all=None, far_support_run=0):
        r = real(xyz, model, c, t_fixed, floor_z_all=floor_z_all, far_support_run=far_support_run)
        tan_yaw, curv, q, _x, _n, _dis, _xm, run = r if r is not None else (0.0, 0.0, 0.0, 0, 0, 0.0, 0, 0)
        n = state["n"]
        dis = 0.01 if n == 2 else 0.0
        return (tan_yaw, 0.0, 0.05, 150.0, 1 if n == 1 else 2, dis, 150.0, run)

    monkeypatch.setattr(track_mod, "estimate_axis_from_walls", fake)
    prev, out = None, []
    for n in sides:
        state["n"] = n
        prev = track_mod.estimate_track(frame.xyz, cfg, prev=prev)
        out.append(prev.axis_valid)
    return out


def test_axis_disagree_hold_bounds_the_trust_after_a_lost_boundary(monkeypatch):
    seq = [3, 2, 1, 1, 1, 1, 3, 2, 1, 3]
    base = _axis_sequence(monkeypatch, TrackConfig(), seq)
    held = _axis_sequence(monkeypatch, TrackConfig(axis_disagree_hold=2), seq)
    assert base[1] == 60.0 and base[2] == 120.0         # the lost boundary raises the trust at once
    assert held[1] == 60.0 and held[2] == 60.0 and held[3] == 60.0   # held for 2 periods ...
    assert held[4] == 120.0 and held[5] == 120.0        # ... then released
    assert held[7] == 60.0 and held[8] == 60.0          # a new disagreement holds again ...
    assert held[9] == base[9]                           # ... two agreeing boundaries end it
    assert [a for i, a in enumerate(base) if i not in (2, 3, 8)] == [a for i, a in enumerate(held) if i not in (2, 3, 8)]
