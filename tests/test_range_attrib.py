"""X1 harness (scripts/range_attrib.py): the blob tracer names the rule that dropped a blob without
changing find_clusters' result, and the cause precedence gives each row exactly one cause."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import resense.clustering as C
from resense.config import DetectorConfig

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("range_attrib", ROOT / "scripts/range_attrib.py")
RA = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RA)


def _clusters(xyz, recorder=None):
    cfg = DetectorConfig().cluster
    n = len(xyz)
    args = (xyz.astype(np.float32), np.full(n, 10.0, np.float32), xyz[:, 1].astype(np.float64),
            xyz[:, 2].astype(np.float64), np.ones(n, bool), cfg)
    if recorder is None:
        return C.find_clusters(*args)
    orig = C._corridor_cluster, C._low_cluster
    C._corridor_cluster, C._low_cluster = recorder.corridor, recorder.low
    try:
        return C.find_clusters(*args)
    finally:
        C._corridor_cluster, C._low_cluster = orig


def _scene():
    rng = np.random.default_rng(0)
    box = rng.uniform([20.0, -0.3, 0.2], [20.5, 0.3, 1.6], (400, 3))           # kept: a person-sized box
    flat = rng.uniform([40.0, -0.4, 0.30], [40.6, 0.4, 0.33], (300, 3))         # flatter than min_height
    line = np.c_[np.linspace(60, 75, 600), np.full(600, 0.5), np.full(600, 0.4)]  # long thin line along X
    return np.vstack([box, flat, line])


def test_tracer_does_not_change_find_clusters_and_names_the_drops():
    xyz = _scene()
    plain = _clusters(xyz)
    rec = RA.Recorder(C)
    traced = _clusters(xyz, rec)
    key = [(round(c.distance, 3), c.zone, c.reason, c.n) for c in plain]
    assert key == [(round(c.distance, 3), c.zone, c.reason, c.n) for c in traced]
    fails = {b["fail"] for b in rec.blobs if "fail" in b}
    kept = [b for b in rec.blobs if "out" in b]
    assert kept and all(20.0 <= b["x0"] <= 20.5 for b in kept)
    assert "thin" in fails
    assert fails & {"infra_linear_thin", "infra_linear_side", "oversize", "oversize_split_refused"}
    assert not any(f.startswith("unmapped") for f in fails)


def _track(**kw):
    t = dict(misses=0, last=1, reported=False, zone="warning", rule_zone="warning", vote_zone="gauge",
             qualifies=False, hits=1, confidence=1.0, hit_fraction=1.0, span_s=1.0, last_kind="",
             history_max=50.0, zone_hist=[True], explained=False, provisional=False)
    t.update(kw)
    return t


CFG = SimpleNamespace(low_confirm_hits=3, confirm_hits=3, conf_threshold=0.5, min_hit_fraction=0.0,
                      confirm_time_s=0.2, low_min_seen_distance=0.0, start_clean=True)


def test_track_causes_follow_track_zone_precedence():
    assert RA.track_cause(_track(hits=1), CFG) == "track:confirm_hits"
    assert RA.track_cause(_track(hits=3, span_s=0.1), CFG) == "track:confirm_time"
    assert RA.track_cause(_track(hits=3, confidence=0.1), CFG) == "track:confidence"
    # exact floats: a span just short of the confirmation time is that rule, whatever 2-decimal rounding shows
    half = SimpleNamespace(**dict(vars(CFG), confirm_time_s=0.5))
    assert RA.track_cause(_track(hits=5, span_s=0.5 - 1e-6), half) == "track:confirm_time"
    assert RA.track_cause(_track(hits=5, span_s=0.5 - 1e-6, timed=False), half) == "unclassified:not_qualified"
    rep = dict(reported=True, qualifies=True, hits=5)
    assert RA.track_cause(_track(**rep, withheld=True, column_held=True), CFG) == "track:doubt"
    assert RA.track_cause(_track(**rep, fresh_blocked=True, explained=True), CFG) == "track:explained_run"
    assert RA.track_cause(_track(**rep, column_held=True, approach_block=True), CFG) == "track:column_hold"
    assert RA.track_cause(_track(**rep, approach_block=True), CFG) == "track:approach_block"
    assert RA.track_cause(_track(**rep, vote_zone="warning"), CFG) == "track:zone_vote"
    assert RA.track_cause(_track(**rep, zone="gauge"), CFG) == "stop_off_object"


def _snap(clusters=(), blobs=(), tracks=()):
    return {"clusters": {cid: c for cid, c in clusters}, "blobs": list(blobs), "tracks": list(tracks), "dets": []}


def _cl(d, **kw):
    c = dict(d=d, x0=d, x1=d + 0.5, y=0.0, zone="gauge", reason="", thin=False, weak=False, kind="",
             n=10, n_gauge=10, final=True)
    c.update(kw)
    return c


def test_row_cause_precedence():
    X, Y, L, W = 100.0, 0.0, 0.5, 0.5
    assert RA.cause(_snap(), X, Y, L, W, CFG) == "no_blob"
    blob = {"x0": 100.0, "x1": 100.4, "y": 0.0, "n_vox": 3, "fail": "min_points"}
    assert RA.cause(_snap(blobs=[blob]), X, Y, L, W, CFG) == "drop:min_points"
    far_away = dict(blob, y=5.0)
    assert RA.cause(_snap(blobs=[far_away]), X, Y, L, W, CFG) == "no_blob"
    col = (7, _cl(100.0, zone="warning", reason="column"))
    assert RA.cause(_snap([col], [blob]), X, Y, L, W, CFG) == "demoted:column"
    thin = (8, _cl(100.0, thin=True, final=False))
    assert RA.cause(_snap([thin]), X, Y, L, W, CFG) == "thin_scanline_only"
    clean = (9, _cl(100.0))
    assert RA.cause(_snap([clean, col]), X, Y, L, W, CFG) == "track:no_track"
    tr = _track(last=9, hits=1)
    assert RA.cause(_snap([clean, col], tracks=[tr]), X, Y, L, W, CFG) == "track:confirm_hits"


def _q(**kw):
    q = dict(value=False, line=1, guard="", hits=5, need_hits=3, confidence=1.0, conf_threshold=0.6, misses=0,
             span_s=0.5, need_span=0.5, hit_fraction=1.0, min_hit_fraction=0.6)
    q.update(kw)
    return q


def test_traced_cause_reads_the_recorded_branches():
    assert RA.qualifies_failure(_q(span_s=0.5 - 1e-6)) == "confirm_time"
    assert RA.qualifies_failure(_q(hits=2)) == "confirm_hits"
    assert RA.qualifies_failure(_q()) == "qualifies_mismatch"        # every clause true but the code said False
    unrep = _track(branch={"qualifies": _q(hits=1)})
    assert RA.traced_track_cause(unrep) == "track:confirm_hits"
    gate = {"line": 9, "text": "q = False", "guard": "if (q and c.explained_run > 0 and not earned_stop"}
    blocked = _track(branch={"qualifies": _q(value=True), "gates": [gate]})
    assert RA.traced_track_cause(blocked) == "track:explained_run"
    blocked["branch"]["carried"] = True
    assert RA.traced_track_cause(blocked) == "track:ego_veto"
    rz = {"value": "warning", "guard": "if not self.zone_hist or self.column_held or self.approach_block:",
          "zone_hist": 3, "column_held": True}
    z = {"value": "warning", "guard": ""}
    held = _track(reported=True, branch={"zone_eval": {"zone": z, "rule_zone": rz}})
    assert RA.traced_track_cause(held) == "track:column_hold"
    assert RA.traced_track_cause(_track(reported=True, branch={})) == "unclassified:no_zone_trace"


def test_tracker_trace_records_gates_only_inside_update():
    import resense.tracking as T
    tr = RA.TrackerTrace(T)
    texts = {text for (code, _), (text, _) in tr.guards.items() if code is T.Tracker.update.__code__}
    assert texts and texts <= set(RA.GATES)
