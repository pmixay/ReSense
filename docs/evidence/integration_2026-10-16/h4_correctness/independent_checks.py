"""Independent H4 oracles; invoked only against explicit Linux source checkouts."""
from __future__ import annotations

import ast
import copy
from dataclasses import fields, is_dataclass, replace
import hashlib
import importlib
import importlib.util
import itertools
import json
import math
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import open3d
import resense
from resense import _native
from resense.config import DetectorConfig, GaugeConfig, HealthConfig, TrackConfig, TrackingConfig
from resense.detector import Candidates, Detector, FrameResult, clear_cap_distance
from resense.frame import Frame
from resense.health import HealthMonitor
from resense.track import TrackModel, estimate_axis_from_walls, estimate_track, wall_drift_range
from resense.clustering import Cluster, FrameRays
from resense.tracking import Track, Tracker

ROOT = Path(resense.__file__).resolve().parents[1]
assert ROOT == Path.cwd() and ROOT in (Path('/work/target'), Path('/work/control'))
assert _native.enabled() and open3d.__version__ == '0.19.0'


def freeze(v):
    if isinstance(v, np.ndarray):
        return dict(dtype=str(v.dtype), shape=list(v.shape), sha256=hashlib.sha256(v.tobytes()).hexdigest())
    if is_dataclass(v):
        return {f.name: freeze(getattr(v, f.name)) for f in fields(v)}
    if isinstance(v, np.generic):
        return v.item()
    if isinstance(v, dict):
        return {k: freeze(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [freeze(x) for x in v]
    return v


def model(**kw):
    return TrackModel(np.array([0., 0., -1.5]), (4., 110.), **dict(dict(center=0., yaw=0., curvature=0.), **kw))


def boundaries():
    cfg, m = TrackConfig(), model()
    x = np.arange(8., 129., 4.)
    rows = []

    def case(name, a, expected, *, xx=x, cc=cfg, mm=m):
        # Values are signed absolute coordinates, as supplied by the wall-bin extractor.
        b = {'side': (xx, np.asarray(a, dtype=float))}
        got = wall_drift_range(b, mm, cc)
        rows.append(dict(name=name, got=got, expected=expected, passed=got == expected))

    for sign, offset in itertools.product((-1, 1), (1.5, 2.75, 3.5)):
        ref = np.full(x.size, offset)
        closing = ref - np.maximum(0., x - 48.) * (1. / 32.)
        first = x[np.flatnonzero(closing < offset - cfg.axis_wall_drift)[0]] - 2.
        case(f'closing_{sign}_{offset}', sign * closing, first)
        case(f'parallel_{sign}_{offset}', sign * ref, 1e9)
        case(f'diverging_{sign}_{offset}', sign * (ref + np.maximum(0., x - 48.) / 32.), 1e9)
        cm = model(center=0.125, yaw=0.006, curvature=sign / 1300.)
        case(f'curved_parallel_{sign}_{offset}', cm.center_y(x) + sign * ref, 1e9, mm=cm)
        case(f'curved_closing_{sign}_{offset}', cm.center_y(x) + sign * closing, first, mm=cm)
    # Strict threshold equality. Binary-exact values separate the mathematical boundary
    # from cancellation/float representation; default 0.8 is also exercised above.
    for sign in (-1, 1):
        for delta, label, expected in ((0., 'equal', 1e9), (-2.**-30, 'beyond', 78.), (2.**-30, 'inside', 1e9)):
            a = np.full(x.size, 2.5)
            a[(x >= 52) & (x < 80)] = 2.5 - (x[(x >= 52) & (x < 80)] - 52) / 32
            a[x >= 80] = 1.75 + delta
            case(f'threshold_{label}_{sign}', sign*a, expected, cc=replace(cfg, axis_wall_drift=.75))
    closing = 2.5 - np.maximum(0., x - 48.) / 32.
    case('far_reference_rejected', closing + 1.01, 1e9)
    case('near_zero_reference_rejected', np.where(x <= 30, 0., -1.), 1e9)
    for n in (0, 1, 2, 3):
        xx = np.r_[x[x <= 30][-n:] if n else [], x[x > 30]]
        aa = 2.5 - np.maximum(0., xx - 48.) / 32.
        case(f'near_count_{n}', aa, 74. if n == 3 else 1e9, xx=xx)
    for gap, expected in ((12., 74.), (12.0001, 1e9)):
        xx = np.r_[8., 12., 16., 20., 24., 28., 28.+gap, np.arange(44., 129., 4.)]
        aa = 2.5 - np.maximum(0., xx - 48.) / 32.
        case(f'gap_{gap}', aa, expected, xx=xx)
    for n in (1, 2, 3):
        a = np.full(x.size, 2.5)
        a[(x >= 52) & (x <= 76)] -= (x[(x >= 52) & (x <= 76)] - 52.) / 32.
        a[(x >= 80) & (x < 80 + 4*n)] = 1.6
        a[x >= 80 + 4*n] = 1.75
        case(f'consecutive_{n}', a, 78. if n >= 2 else 1e9)
    case('structure_step', np.where(x < 48., 2.5, 1.25), 1e9)
    stepped = np.where(x < 48., 2.5, 1.25) - np.maximum(0., x - 64.) / 32.
    case('structure_then_drift', stepped, 90.)
    noisy = closing.copy()
    noisy[:6] = [2., 3., 2., 3., 2., 3.]
    case('near_mad_reject', noisy, 1e9)
    sloped = closing.copy()
    sloped[:6] = 2.5 + .021 * (x[:6] - 18.)
    case('near_slope_reject', sloped, 1e9)
    # Inclusive MAD bar with three inliers, and a single rejected near outlier.
    for eps, expected in ((0., 74.), (1e-6, 1e9)):
        a = closing.copy()
        a[:6] = 2.5 + np.array([-.25-eps, .25+eps, -.25-eps, .25+eps, -.25-eps, .25+eps])
        case(f'mad_boundary_{eps}', a, expected)
    a = closing.copy(); a[0] = 4.
    case('near_outlier_ignored', a, 74.)
    # Exact rails upper bound supplies the third reference; just below excludes it.
    xx = np.r_[8., 12., 30., np.arange(34., 130., 4.)]
    aa = 2.5 - np.maximum(0., xx - 50.) / 32.
    case('rail_bound_inclusive', aa, 76., xx=xx)
    case('rail_bound_just_below', aa, 1e9, xx=xx, cc=replace(cfg, rails_range=(4., np.nextafter(30., 0.))))
    # Two unequal sides; earliest evidence wins independently of dictionary order.
    left = 2.2 - np.maximum(0., x-48.) / 32.
    right = -(3.2 - np.maximum(0., x-64.) / 32.)
    for b in ({'left': (x, left), 'right': (x, right)}, {'right': (x, right), 'left': (x, left)}):
        got = wall_drift_range(b, m, cfg)
        rows.append(dict(name='asymmetric_earliest', got=got, expected=74., passed=got == 74.))
    return dict(cases=len(rows), failures=[r for r in rows if not r['passed']], rows=rows)


def health_properties():
    # Full healthy angular coverage; visibility is independently controlled at its API
    # to cover algebraic combinations without fabricating different clouds per cap.
    az = np.radians(np.linspace(-34., 34., 3000))
    xyz = np.c_[np.full(az.size, 40.), 40.*np.tan(az), np.zeros(az.size)].astype(np.float32)
    track = model(rail_score=1.)
    count, failures, reductions = 0, [], 0
    values = itertools.product((0., 42., 150.), (0., 65., 200.), (0., 90., 250.),
                               (None, 0., 37., 180.), (None, 0., 51., 160.),
                               (None, 1e9, -3., 0., 22., 72., 300.))
    for trusted, vis, gauge_max, candidate, obstacle, drift in values:
        cfg = HealthConfig()
        gauge = GaugeConfig(range_max=gauge_max)
        with patch('resense.health.visibility_along_track', return_value=vis):
            base = HealthMonitor(cfg).update(xyz, {}, track, gauge, trusted, .05, None,
                                               obstacle_distance=obstacle, candidate_distance=candidate)
            got = HealthMonitor(cfg).update(xyz, {}, track, gauge, trusted, .05, None,
                                              obstacle_distance=obstacle, candidate_distance=candidate, wall_drift=drift)
        mon = max(0., min(vis, trusted, gauge_max, 1e9 if drift is None else drift))
        clear = min(mon, mon if obstacle is None else obstacle, mon if candidate is None else candidate)
        other = lambda d: {k: v for k, v in d.items() if k not in ('wall_drift', 'clear_distance', 'monitored_range')}
        ok = (got['monitored_range'] == round(mon, 1) and got['clear_distance'] == round(clear, 1)
              and 0 <= got['clear_distance'] <= got['monitored_range'] <= base['monitored_range']
              and got['clear_distance'] <= base['clear_distance'] and other(got) == other(base))
        count += 1; reductions += got['clear_distance'] < base['clear_distance']
        if not ok:
            failures.append(dict(inputs=[trusted, vis, gauge_max, candidate, obstacle, drift], base=base, got=got))
    # A hard input fault must zero both even with a generous cap.
    bad = HealthMonitor(HealthConfig()).update(xyz[:2], {}, track, GaugeConfig(), 200., .05, None, wall_drift=120.)
    assert bad['level'] == 'error' and bad['monitored_range'] == bad['clear_distance'] == 0.
    return dict(cases=count, clear_reductions=reductions, fault_checked=True, failures=failures)


def cluster(**kw):
    defaults = dict(points_idx=np.array([0, 1]), n=20, n_raw=30, centroid=np.array([40., 0., 0.]),
                    bbox_min=np.array([39., -.2, -1.]), bbox_max=np.array([41., .2, 1.8]), distance=39.,
                    lateral=0., height_min=.1, height_max=2.9, intensity=10., n_expected=20., score=1.,
                    zone='gauge', n_gauge=20)
    return Cluster(**dict(defaults, **kw))


def tracking_properties():
    count = 0
    for required, hist in itertools.product((0, 1, 2, 3), itertools.product((False, True), repeat=5)):
        cfg = TrackingConfig(column_free_min_spares=required)
        cl = cluster(spared=True)
        Tracker(cfg)._uncorroborated_spare(cl, list(hist))
        demote = required > 1 and sum(hist) < required-1
        assert (cl.reason, cl.zone, cl.demoted) == (('column', 'warning', False) if demote else ('', 'gauge', False))
        count += 1
    cand = Candidates(np.empty((0,3)), np.empty(0), np.empty(0), np.empty(0, bool), np.empty(0), np.empty(0, int), np.empty(0, bool))
    caps = 0
    for hist, hold, reported, missed, skip in itertools.product(itertools.product((False, True), repeat=5), (0, 1, 2, 6), (False, True), (0, 1), (False, True)):
        cl = cluster()
        t = Track(1, cl.centroid.copy(), np.zeros(3), last=cl, hits=5, misses=missed,
                  column_hist=list(hist), column_hold=hold, zone_hist=[True]*5, reported=reported, seen_reported=True)
        held = hold > 0 and sum(hist) >= hold
        assert t.column_held == held
        assert t.rule_zone == ('warning' if held else 'gauge')
        hcfg = HealthConfig(clear_cap_min_hits=2, clear_cap_skip_columns=skip, clear_cap_lost=True)
        got = clear_cap_distance([cl] if missed == 0 else [], [t], cand, np.empty(0), np.empty(0), GaugeConfig(), hcfg)
        expected = None if (skip and held) or (missed == 0 and reported and not held) else cl.distance
        assert got == expected, (hist, hold, reported, missed, skip, got, expected)
        caps += 1
    cfg = TrackingConfig(column_free_min_spares=2, column_hold=2)
    tr = Tracker(cfg)
    sequence = []
    for spared in (False, True, False, True, True, True, True, True):
        cl = cluster(spared=spared, reason='' if spared else 'column', zone='gauge' if spared else 'warning')
        tr.update([cl], frame_dt=.1)
        t = tr.tracks[0]
        sequence.append(dict(spared=spared, reason=cl.reason, zone=cl.zone, spare_hist=t.spare_hist[:],
                             column_hist=t.column_hist[:], vote=t.vote_zone, rule=t.rule_zone, reported=t.reported))
    assert sequence[1]['reason'] == 'column' and sequence[3]['reason'] == ''
    assert sequence[3]['rule'] == 'warning' and sequence[-1]['rule'] == 'gauge'
    return dict(spare_cases=count, actual_track_clear_cap_cases=caps, sequence=sequence, failures=[])


def cache_properties():
    rng = np.random.default_rng(40816)
    cases = 0
    for dtype in (np.float32, np.float64):
        xyz = rng.normal(size=(12000, 3)).astype(dtype) * 40
        xyz[:5, 0] = [0, -1, 1e-12, 1, 1]
        h, dy = rng.uniform(0., 4., len(xyz)), rng.uniform(-3., 3., len(xyz))
        rays = FrameRays(xyz, None, h, dy)
        keys = None
        for a0, width in zip(rng.uniform(-85., 80., 80), rng.uniform(.001, 4., 80)):
            a1 = min(89., a0+width)
            got = rays.window(a0, a1)
            t0, t1 = np.tan(np.radians([a0, a1]))
            expected = np.flatnonzero((xyz[:, 0] > 0) & (xyz[:, 1] >= t0*xyz[:, 0]) & (xyz[:, 1] <= t1*xyz[:, 0]))
            assert np.array_equal(got, expected)
            if keys is None: keys = rays._keys
            assert rays._keys is keys
            cases += 1
        first = rays.axis_band()
        assert rays.axis_band() is first
        idx = first[0]
        assert set(idx) == set(np.flatnonzero((np.abs(dy) <= .5) & (h > .5)))
        assert (np.diff(first[1]) >= 0).all()
    # Instrument actual process wiring across different clouds and a reset. No cached
    # coordinates from the prior frame may reach find_clusters in the next frame.
    import resense.detector as dm
    original = dm._clusters_of
    seen = []
    cfg = DetectorConfig(); cfg.calibration.enabled = False
    det = Detector(cfg)
    def spy(c, config, **kw):
        if config is cfg.cluster:
            assert kw['frame_xyz'] is det._frame_xyz
            assert kw['frame_h'] is det._frame_hd[1] and kw['frame_dy'] is det._frame_hd[0]
            assert kw['frame_ring'] is det._frame_ring
            seen.append((det._frame_xyz, det._frame_hd))
        return original(c, config, **kw)
    for i in range(2):
        xyz, _ = scene('transition', 1, bool(i))
        if i: xyz = np.vstack([xyz, [np.nan, 0, 0]]).astype(np.float32)
        with patch.object(dm, '_clusters_of', spy):
            det.process(Frame(xyz, np.full(len(xyz), 10., np.float32), None, i*.1, meta={}))
        assert np.isfinite(det._frame_xyz).all()
    assert len(seen) == 2 and seen[0][0] is not seen[1][0] and seen[0][1] is not seen[1][1]
    det.reset()
    assert det._frame_xyz is None and det._frame_hd is None and det._frame_ring is None
    return dict(exact_window_cases=cases, axis_band_reuse=True, process_frames=len(seen), reset_clears=True, failures=[])


def scene(kind, sign, obj):
    rng = np.random.default_rng(401617)
    def axis(x):
        base = -.125 + .001*x
        if kind == 'constant': return base + sign * x*x/(2.*900.)
        if kind == 'transition': return base + sign * np.maximum(x-30., 0.)**3/(6.*60000.)
        return base
    parts = []
    x = rng.uniform(3., 122., 34000)
    parts.append(np.c_[x, axis(x)+rng.uniform(-1.25, 1.25, len(x)), -1.5+rng.normal(0., .006, len(x))])
    for s in (-1, 1):
        x = rng.uniform(3., 59., 11000)
        parts.append(np.c_[x, axis(x)+s*.795+rng.uniform(-.035, .035, len(x)), -1.15+rng.normal(0., .003, len(x))])
        # Unequal offsets and asymmetric visibility; the inside of a transition
        # hides itself while the opposite wall continues beyond it.
        reach = 70. if kind == 'transition' and s == sign else 158.
        x = rng.uniform(6.1, reach, 26000)
        offset = 2.2 if s == sign else 2.75
        parts.append(np.c_[x, axis(x)+s*offset+rng.normal(0., .008, len(x)), rng.uniform(-1.4, 3.2, len(x))])
    if obj:
        # Dense resolved box face and sides, wholly in the near strict envelope.
        x = rng.uniform(21., 22., 2500)
        x[:1500] = 21.
        parts.append(np.c_[x, axis(x)+rng.uniform(-.6, .6, len(x)), rng.uniform(-1.14, .6, len(x))])
    return np.concatenate(parts).astype(np.float32), axis


def scenes(mode):
    rows = []
    target = ROOT.name == 'target'
    for kind, sign, obj in itertools.product(('straight', 'constant', 'transition'), (-1, 1), (False, True)):
        cfg = DetectorConfig()
        if target:
            # Only added non-axis mechanisms are switched off for the isolated A/B.
            cfg.cluster.column_free_max_top = 0.
            cfg.cluster.structure_cut_tol = 0.
            cfg.tracking.column_free_min_spares = 0
            cfg.track.axis_wall_drift = .8 if mode == 'on' else 0.
        det = Detector(cfg)
        xyz, axis = scene(kind, sign, obj)
        for i in range(8):
            r = det.process(Frame(xyz, np.full(len(xyz), 10., np.float32), None, i*.1, meta={}))
            raw = freeze(r)
            raw.pop('timing_ms')
            for k in ('latency_p95_ms', 'latency_basis', 'latency_sample_age_frames'):
                raw['health'].pop(k, None)
            assert not any(s.startswith('latency p95') for s in raw['health']['messages'])
            drift = getattr(r.track, 'wall_drift', 1e9)
            err = float(abs(r.track.center_y(drift+2.)-axis(drift+2.))) if drift < 1e9 else None
            rows.append(dict(key=[kind, sign, obj, i], wall_drift=drift, error_at_cap_bin=err, raw=raw))
        if obj: assert r.obstacle, (kind, sign, r.to_dict())
    return dict(root=str(ROOT), native=_native.status(), numpy=np.__version__, open3d=open3d.__version__, rows=rows)


def final_axis():
    rows = []
    for sign, periods in itertools.product((-1, 1), (1, 3)):
        xyz, _ = scene('transition', sign, False)
        cfg = TrackConfig()
        prior = model(curvature=-sign*.0002, age=20)
        original = wall_drift_range
        calls = []
        def spy(bounds, final, cc):
            calls.append((copy.deepcopy(bounds), copy.deepcopy(final)))
            return original(bounds, final, cc)
        with patch('resense.track.wall_drift_range', spy):
            got = estimate_track(xyz, cfg, prior, periods=periods)
        assert len(calls) == 1
        bounds, captured = calls[0]
        assert captured.center_coefs() == got.center_coefs()
        assert got.wall_drift == original(bounds, got, cfg)
        assert abs(got.curvature - prior.curvature) <= periods * cfg.axis_max_curvature_rate + 1e-15
        off = estimate_track(xyz, replace(cfg, axis_wall_drift=0.), prior, periods=periods)
        a, b = freeze(got), freeze(off)
        a.pop('wall_drift'); b.pop('wall_drift')
        assert a == b
        # Bins must survive a refused polynomial fit; cap evidence does not depend
        # on successful curvature fitting.
        bounds = {}
        fit = estimate_axis_from_walls(xyz, got, replace(cfg, walls_min_bins=1000), boundaries=bounds)
        assert fit is None and bounds
        no_wall = estimate_track(xyz[xyz[:, 2] < -.5], cfg, got)
        assert no_wall.wall_drift == 1e9
        disabled = estimate_track(xyz, replace(cfg, walls_enabled=False), got)
        assert disabled.wall_drift == 1e9
        rows.append(dict(sign=sign, periods=periods, drift=got.wall_drift, coefs=got.center_coefs(), fit_failed_bins={k:len(v[0]) for k,v in bounds.items()}))
    return dict(rows=rows, failures=[])


def node_properties():
    # Reuse only transport stand-ins; no existing test function or expected result.
    spec = importlib.util.spec_from_file_location('h4_transport', ROOT/'tests/test_node.py')
    transport = importlib.util.module_from_spec(spec); spec.loader.exec_module(transport)
    sys.modules.update(transport._stub_modules())
    sys.path.insert(0, str(ROOT/'ros2_ws/src/resense_ros'))
    nm = importlib.import_module('resense_ros.detector_node')
    policy = importlib.import_module('resense_ros.decision_policy')
    assert Path(nm.__file__).resolve().is_relative_to(ROOT)
    transport._Node.overrides = dict(freshness_mode='live', warmup=False, publish_markers=False, publish_corridor_cloud=False)
    n = nm.DetectorNode()
    statuses = []
    healths = ({}, None, {'level':'ok'}, {'level':'warn'}, {'level':'error'}, {'level':'bogus'},
               {'level':0}, {'decision_level':None}, [], 'ok', {'level':'warn', 'decision_level':'ok'})
    for obs, warning, health, latched, clock in itertools.product((False, True, 1, 'false', np.bool_(True)), (False, True, 'false'), healths, (False, True), ('fresh','stale','catchup')):
        n.stop_latch = dict(nearest_distance=17., detections=[], stamp=1., frame_id='prior') if latched else None
        n.stop_ros = None
        now, wall = time.perf_counter(), time.time()
        n.freshness_previous = (wall-.1, wall-(2. if clock == 'stale' else .05), now-.01, wall-.01)
        n.current_arrival = (now-.01, wall-.05)
        n.current_queue_lag = .1 if clock == 'catchup' else 0.
        n.frame_in_catchup = clock == 'catchup'; n.epoch_reason = ''
        r = FrameResult(1., obs, warning, 17. if isinstance(obs, (bool,np.bool_)) and bool(obs) else None, [], [], [], model(), np.empty(0, int), 0, health=copy.deepcopy(health), clear_distance=100.)
        before = freeze(r)
        strict_obs = isinstance(obs, (bool,np.bool_)) and bool(obs)
        flag_ok = isinstance(obs, (bool,np.bool_)) and isinstance(warning, bool)
        health_ok = health is None or (isinstance(health, dict) and health.get('level','ok') in ('ok','warn') and health.get('decision_level',health.get('level','ok')) in ('ok','warn'))
        fresh = clock == 'fresh' and flag_ok and health_ok
        held = not strict_obs and latched and not fresh
        expected = 'STOP' if strict_obs or held else ('FAULT' if not flag_ok or not health_ok or clock == 'stale' else ('CAUTION' if clock == 'catchup' or warning is True or (isinstance(health,dict) and health.get('decision_level',health.get('level','ok')) == 'warn') else 'GO'))
        header = transport._Msg(stamp=transport._Msg(sec=1, nanosec=0), frame_id='h4')
        n.publish(header, Frame(np.empty((0,3)), np.empty(0), None, 1., meta={}), r)
        out = json.loads(n.published['/resense/status'][-1].data)
        assert out['decision'] == expected, (obs, warning, health, latched, clock, out, expected)
        assert out['freshness']['valid'] == fresh
        assert out['clear_distance'] == (100. if fresh else 0.)
        assert out['decision_policy'] == 'v1'
        assert out['caution_reason'] == sorted(set(out['caution_reason']))
        assert (out['caution_reason'] == []) if expected != 'CAUTION' else bool(out['caution_reason'])
        assert freeze(r) == before
        statuses.append(expected)
    for call in (lambda: nm.DetectorNode.decision(SimpleNamespace(), 'v2'),):
        try: call()
        except ValueError: pass
        else: raise AssertionError('runtime v2 accepted')
    transport._Node.overrides['decision_policy'] = 'v2'
    try: nm.DetectorNode()
    except ValueError: pass
    else: raise AssertionError('constructor v2 accepted')
    for invalid in (1, 'true', [], {}):
        assert policy.decision({'obstacle': invalid}) == 'FAULT'
        assert policy.decision({'obstacle': True, 'health': invalid}) == 'STOP'
    return dict(cases=len(statuses), decisions={k:statuses.count(k) for k in set(statuses)}, source=nm.__file__, policy_source=policy.__file__, failures=[])


def ast_properties():
    rel = 'ros2_ws/src/resense_ros/resense_ros/detector_node.py'
    base = ast.parse(subprocess.check_output(['git','show',f'3fdc87957f5d09ff32573eabe6637924b91ea376:{rel}'], text=True))
    now = ast.parse((ROOT/rel).read_text())
    def defaults(tree):
        return {n.args[0].value: (-999. if isinstance(n.args[1],ast.Name) else ast.literal_eval(n.args[1])) for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr == 'declare_parameter'}
    a,b = defaults(base),defaults(now)
    assert len(a) == 39 and all(b[k] == v for k,v in a.items())
    assert {k:v for k,v in b.items() if k not in a} == dict(decision_policy='v1', caution_distance_m=80., caution_compact_max_size_m=3.)
    names = '_account_frame node_stats start_new_input check_continuity catchup_plan on_cloud on_pending take_waiting prune process_next track_catchup process_cloud begin_freshness on_watchdog subscribe remember_arrival'.split()
    def methods(tree):
        cl = next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name == 'DetectorNode')
        return {n.name:ast.dump(n,include_attributes=False) for n in cl.body if isinstance(n,ast.FunctionDef)}
    am,bm = methods(base),methods(now)
    assert all(am[n] == bm[n] for n in names)
    assert (ROOT/'configs/default.yaml').read_bytes() == (ROOT/'ros2_ws/src/resense_ros/config/detector.yaml').read_bytes()
    # All 36 core blobs also equal the H3 measured commit, independently of inventories.
    inv = json.loads((ROOT/'docs/evidence/integration_2026-10-16/h3/candidate/source_before.json').read_text())
    for path in inv['files']:
        assert subprocess.check_output(['git','show',f'f8c088dc4f3243fbd15a3aae9be0459e8a0aa941:{path}']) == (ROOT/path).read_bytes()
    return dict(published_defaults=len(a), unchanged_methods=names, additive_defaults={k:v for k,v in b.items() if k not in a}, h3_equal_blobs=len(inv['files']), failures=[])


def main():
    name, out = sys.argv[1:3]
    funcs = dict(boundaries=boundaries, health=health_properties, tracking=tracking_properties,
                 cache=cache_properties, final_axis=final_axis, node=node_properties, ast=ast_properties)
    answer = scenes(name[7:]) if name.startswith('scenes_') else funcs[name]()
    Path(out).write_text(json.dumps(answer, indent=2, sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in answer.items() if k not in ('rows','sequence')}, indent=2))
    if answer.get('failures'): raise SystemExit(1)


if __name__ == '__main__':
    main()
