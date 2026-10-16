"""Independent boundary/reachability checks; supplied-coordinate scenes are labelled as such."""
import ast
import copy
import hashlib
import itertools
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

import resense
from resense import _native, clustering as cl
from resense.config import DetectorConfig, GaugeConfig, HealthConfig, TrackConfig
from resense.detector import Detector
from resense.frame import Frame
from resense.health import HealthMonitor
from resense.track import TrackModel
from resense.tracking import Tracker

MODE, DEST = sys.argv[1:3]
ROOT = Path.cwd()
assert Path(resense.__file__).resolve() == ROOT / "resense/__init__.py"
assert _native.enabled(), _native.status()
RESULT = dict(mode=MODE, imported=resense.__file__, numpy=np.__version__, native=_native.status())


def digest(a):
    return hashlib.sha256(a.tobytes()).hexdigest()


def model():
    return TrackModel(np.array([0., 0., -1.83]), (4., 150.), 0., 0., 0., rail_score=1.)


def cluster(reason="", distance=71.):
    c = np.array([distance, .17, .8])
    return cl.Cluster(points_idx=np.arange(12), n=12, n_raw=12, centroid=c,
                      bbox_min=c - [.2, .2, .6], bbox_max=c + [.2, .2, .6],
                      distance=distance, lateral=.17, height_min=.2, height_max=1.4,
                      intensity=20., n_expected=12., score=1., n_gauge=12,
                      zone="warning" if reason else "gauge", reason=reason)


def tracker_sequences():
    rows = []
    # Exhaust all 3-hit prefixes over clean/column/other-explanation/missing,
    # then force an earned STOP, two misses and clean returning evidence.
    for prefix in itertools.product(["", "column", "floating", None], repeat=3):
        tr = Tracker(DetectorConfig().tracking)
        sequence = list(prefix) + [""] * 12 + [None, None] + [""] * 4
        frames = []
        for reason in sequence:
            tr.update([] if reason is None else [cluster(reason)], frame_dt=.1)
            frames.append([dict(reported=t.reported, zone=t.zone, hits=t.hits, misses=t.misses,
                                column=list(t.column_hist), explained=list(t.explained_hist),
                                clean=t.clean_run, blocked=t.fresh_blocked) for t in tr.tracks])
            assert not any(any(getattr(t, "spare_hist", [])) or
                           any(getattr(t, "provisional_explained_hist", [])) for t in tr.tracks)
        rows.append(dict(prefix=prefix, frames=frames))
    return rows


def components():
    rows = []
    for top in (1.7, 2.72, 3.22):
        for sign in (-1, 1):
            y, h = np.meshgrid(np.linspace(.45, .91, 5), np.arange(.12, min(top, 2.95), .12))
            xyz = np.column_stack([np.full(y.size, 67.), sign * y.ravel(), h.ravel()]).astype(np.float32)
            strict = (np.abs(xyz[:, 1]) < 1.05) & (xyz[:, 2] < 3.)
            cs = cl.find_clusters(xyz, np.full(len(xyz), 20., np.float32), xyz[:, 1], xyz[:, 2], strict,
                                  DetectorConfig().cluster)
            assert len(cs) == 1
            c = cs[0]
            assert not getattr(c, "spared", False)
            tr, stop = Tracker(DetectorConfig().tracking), []
            for i in range(20):
                tr.update([copy.deepcopy(c)] if i not in (9, 10) else [], frame_dt=.1)
                if any(t.reported and t.zone == "gauge" for t in tr.tracks):
                    stop.append(i)
            assert bool(stop) == (top == 1.7)
            rows.append(dict(top=top, side=sign, input_sha256=digest(xyz), n=c.n, n_gauge=c.n_gauge,
                             reason=c.reason, zone=c.zone, stop_frames=stop,
                             truth="in-envelope supplied-coordinate face; top>2.95 uses known corridor cut"))
    return rows


def h2():
    cfg = DetectorConfig().cluster
    rows = []
    X, H = np.meshgrid(np.arange(102., 137., .31), np.arange(.13, 2.95, .21))
    wall = np.column_stack([X.ravel(), np.full(X.size, 1.88), H.ravel()])
    for n, span, sign, echoes in itertools.product((7, 8, 9), (.099999, .1, .100001), (-1, 1), (1, 2)):
        y = np.where(np.arange(n) % 2, 118. * np.tan(np.arctan2(.31, 118.) + np.radians(span)), .31)
        part = np.column_stack([np.full(n, 118.), y, .23 + .25 * np.arange(n)])
        xyz = np.concatenate([wall, np.repeat(part, echoes, axis=0)]) * [1., sign, 1.]
        strict = (np.abs(xyz[:, 1]) < 1.05) & (xyz[:, 2] > 0) & (xyz[:, 2] < 3.)
        vox, inv = cl.voxelize(xyz, cfg)
        blob = cl._Blob.of(xyz, np.arange(len(xyz)), len(vox))
        out = cl._off_structure_parts(blob, xyz, xyz[:, 2], strict, vox, inv, cfg)
        # Independent physical angle calculation, not a corridor dy approximation.
        physical = float(np.ptp(np.arctan2(part[:, 1], part[:, 0])))
        nvox = len(np.unique(inv[len(wall):]))
        expected = nvox >= 8 and physical >= np.radians(.1)
        assert bool(out) == expected, (n, span, sign, echoes, nvox, physical, out)
        assert all(strict[o.idx].any() for o in out)
        rows.append(dict(n=n, nvox=nvox, span_requested_deg=span, span_measured_rad=physical,
                         side=sign, echoes=echoes, accepted=bool(out), input_sha256=digest(xyz)))
    # Robust-fit residual boundary: equal values are recorded rather than rounded
    # into an invented exact arithmetic oracle; +/-10 micrometres have firm oracles.
    residuals = []
    for residual, sign in itertools.product((1.3 - 1e-5, 1.3, 1.3 + 1e-5), (-1, 1)):
        Y = 2.05 + .32 * H - .08 * H * H
        w = np.column_stack([X.ravel(), Y.ravel(), H.ravel()])
        hh = .21 + .14 * np.arange(16)
        p = np.column_stack([np.full(len(hh), 119.), 2.05 + .32 * hh - .08 * hh * hh - residual, hh])
        xyz = np.concatenate([w, p]) * [1., sign, 1.]
        strict = (np.abs(xyz[:, 1]) < 1.05) & (xyz[:, 2] < 3.)
        vox, inv = cl.voxelize(xyz, cfg)
        out = cl._off_structure_parts(cl._Blob.of(xyz, np.arange(len(xyz)), len(vox)), xyz,
                                     xyz[:, 2], strict, vox, inv, cfg)
        if residual != 1.3:
            assert bool(out) == (residual > 1.3), (residual, out)
        residuals.append(dict(residual=residual, side=sign, accepted=bool(out),
                              input_sha256=digest(xyz), parts=[o.idx.tolist() for o in out]))
    return dict(angular_voxel=rows, residual=residuals)


def axis_health():
    from resense.track import wall_drift_range
    cfg, m = TrackConfig(), model()
    x = np.arange(8., 132., 4.)
    rows = []
    for sign, ref, final in itertools.product((-1, 1), (3.5 - 1e-8, 3.5, 3.5 + 1e-8), (.8 - 1e-8, .8, .8 + 1e-8)):
        drop = np.clip((x - 48.) / 32., 0., 1.) * final
        y = sign * (ref - drop)
        got = wall_drift_range({"independent": (x, y)}, m, cfg)
        # Plateau is exact for this float representation; threshold uses strict <.
        cross = np.flatnonzero((x > cfg.rails_range[1]) & ((ref - drop) < ref - .8))
        expected = float(x[cross[0]] - 2.) if ref <= 3.5 and len(cross) >= 2 else 1e9
        assert got == expected, (sign, ref, final, got, expected)
        rows.append(dict(side=sign, reference=ref, final_drift=final, got=got))
    # A single threshold-crossing bin cannot create a two-bin cap.
    y = np.full(len(x), 2.5); y[x == 84.] = 1.6
    assert wall_drift_range({"one": (x, y)}, m, cfg) == 1e9
    # Too few near anchors cannot establish a reference, even with far drift.
    keep = (x > cfg.rails_range[1]) | (x <= 12.)
    assert wall_drift_range({"short": (x[keep], (2.5 - np.clip((x - 48.) / 32., 0., 1.))[keep])}, m, cfg) == 1e9
    rng = np.random.default_rng(16102641)
    xx = rng.uniform(5., 210., 24000)
    cloud = np.column_stack([xx, xx * np.tan(np.radians(rng.uniform(-29., 29., len(xx)))), rng.uniform(-1., 2., len(xx))]).astype(np.float32)
    cloud = np.concatenate([cloud, np.column_stack([np.linspace(5., 200., 500), np.zeros(500), np.zeros(500)])])
    checks = []
    for fault, trust, cap, obstacle, candidate in itertools.product((False, True), (55., 150.),
            (None, 1e9, -1., 0., 63., 180.), (None, 31., 99.), (None, 22., 110.)):
        points = cloud[:100] if fault else cloud
        base = HealthMonitor(HealthConfig()).update(points, {}, m, GaugeConfig(), trust, .05, None,
                                                    obstacle_distance=obstacle, candidate_distance=candidate)
        got = HealthMonitor(HealthConfig()).update(points, {}, m, GaugeConfig(), trust, .05, None,
                obstacle_distance=obstacle, candidate_distance=candidate, wall_drift=cap)
        expected_m = 0. if fault else max(0., min(base["monitored_range"], cap if cap is not None else 1e9))
        expected_c = max(0., min(base["clear_distance"], cap if cap is not None else 1e9))
        assert got["monitored_range"] == round(expected_m, 1)
        assert got["clear_distance"] == round(expected_c, 1)
        excluded = {"wall_drift", "monitored_range", "clear_distance"}
        assert {k:v for k,v in got.items() if k not in excluded} == {k:v for k,v in base.items() if k not in excluded}
        checks.append(dict(fault=fault, trust=trust, cap=cap, obstacle=obstacle, candidate=candidate,
                           monitored=got["monitored_range"], clear=got["clear_distance"]))
    return dict(boundaries=rows, isolated_negative_controls=2, health=checks)


def reachability():
    called = []
    original = cl.top_is_free
    def forbidden(*a, **k):
        raise AssertionError("withdrawn observer reached with shipping config")
    cl.top_is_free = forbidden
    # Analytic supplied-coordinate cloud: floor and rails plus two full walls;
    # random density is independent of the authored synthetic helper.
    rng = np.random.default_rng(16102643)
    xx = rng.uniform(4., 150., 24000)
    floor = np.column_stack([xx, rng.uniform(-1.3, 1.3, len(xx)), np.full(len(xx), -1.83)])
    parts = [floor]
    for sign in (-1, 1):
        xr = rng.uniform(4., 55., 5000)
        parts.append(np.column_stack([xr, sign * .795 + rng.normal(0., .015, len(xr)), np.full(len(xr), -1.48)]))
        xw = rng.uniform(4., 160., 9000)
        parts.append(np.column_stack([xw, np.full(len(xw), sign * 2.43), rng.uniform(-1.7, 2.29, len(xw))]))
    yy, zz = np.meshgrid(np.linspace(-.3, .3, 9), np.linspace(-1.48, .22, 18))
    parts.append(np.column_stack([np.full(yy.size, 29.), yy.ravel(), zz.ravel()]))
    xyz = np.concatenate(parts).astype(np.float32)
    reports = []
    for entry in ("class", "yaml"):
        cfg = DetectorConfig() if entry == "class" else DetectorConfig.from_yaml(str(ROOT / "configs/default.yaml"))
        assert cfg.cluster.column_free_max_top == 0.
        det = Detector(cfg)
        frames, candidates, stops = 0, 0, []
        for i in range(8):
            r = det.process(Frame(xyz=xyz, intensity=np.full(len(xyz), 20., np.float32), stamp=i*.1, meta={}))
            assert all(not c.spared for c in r.candidates)
            assert not any(any(t.spare_hist) or any(t.provisional_explained_hist) for t in det.tracker.tracks)
            candidates += len(r.candidates); frames += 1
            if r.obstacle: stops.append(i)
        assert candidates > 0
        reports.append(dict(entry=entry, frames=frames, candidates=candidates, stop_frames=stops))
    # Positive control deliberately replaces the observer answer: prove routing,
    # not claim physical free-top correctness.
    cfg = DetectorConfig().cluster
    cfg.column_free_max_top = 2.95
    yy, zz = np.meshgrid(np.linspace(.45, .91, 5), np.arange(.12, 2.73, .12))
    p = np.column_stack([np.full(yy.size, 67.), yy.ravel(), zz.ravel()]).astype(np.float32)
    cl.top_is_free = lambda *a, **k: called.append(1) or True
    cs = cl.find_clusters(p, np.full(len(p), 20., np.float32), p[:,1], p[:,2], np.ones(len(p), bool), cfg, frame_xyz=p)
    assert called and any(c.spared for c in cs)
    cl.top_is_free = original
    return dict(full_detector=reports, forbidden_calls=0, explicit_on_mock_observer_calls=len(called),
                input_sha256=digest(xyz))


def runtime():
    path = "ros2_ws/src/resense_ros/resense_ros/detector_node.py"
    old = ast.parse(subprocess.check_output(["git", "show", "3fdc87957f5d09ff32573eabe6637924b91ea376:" + path], text=True))
    new = ast.parse((ROOT / path).read_text())
    def methods(tree):
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "DetectorNode")
        return {n.name: ast.dump(n, include_attributes=False) for n in cls.body if isinstance(n, ast.FunctionDef)}
    a, b = methods(old), methods(new)
    identical = sorted(k for k in a if k in b and a[k] == b[k])
    required = ["freshness_accept", "on_cloud", "process_next", "new_epoch"]
    # Name the actual unchanged methods rather than assume adapter names.
    def defaults(tree):
        out = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "declare_parameter":
                v = n.args[1]
                out[n.args[0].value] = -999. if isinstance(v, ast.Name) and v.id == "UNSET" else ast.literal_eval(v)
        return out
    da, db = defaults(old), defaults(new)
    assert all(db[k] == v for k,v in da.items())
    assert len(da) == 39
    changes = sorted(k for k in a if k in b and a[k] != b[k])
    assert set(changes) == {"__init__", "result_freshness", "publish_fault", "decision", "publish", "make_markers"}, changes
    return dict(preserved_defaults=len(da), added_defaults={k:v for k,v in db.items() if k not in da},
                identical_methods=identical, changed_methods=changes)


try:
    if "--runtime-only" not in sys.argv:
        RESULT["tracker"] = tracker_sequences()
        RESULT["gt_components"] = components()
    if MODE == "selected" and "--runtime-only" not in sys.argv:
        RESULT["h2"] = h2()
        RESULT["axis_health"] = axis_health()
        RESULT["reachability"] = reachability()
    if MODE == "selected":
        RESULT["runtime"] = runtime()
    RESULT["success"] = True
finally:
    Path(DEST).write_text(json.dumps(RESULT, indent=2) + "\n")
