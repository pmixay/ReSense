#!/usr/bin/env python3
"""Small independent geometry/state probes, including explicit known limits.

Observation stubs isolate state logic and are marked in the output. The real
late-ring replay uses unchanged observe_mount / Detector on original float32 data.
This is a diagnostic, not a new release acceptance protocol or timing benchmark.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

import resense.calibration as mod
from resense.config import DetectorConfig


def cones(elevations=(-.24, -.11, -.02, .04, .12, .22), rotation=None):
    azimuth = np.linspace(-1.1, 1.1, 180)
    a, e = np.meshgrid(azimuth, np.asarray(elevations))
    xyz = np.stack([np.cos(e) * np.cos(a), np.cos(e) * np.sin(a), np.sin(e)], -1).reshape(-1, 3)
    xyz *= np.linspace(4, 65, len(xyz))[:, None]
    if rotation is not None:
        xyz = xyz @ rotation.T
    return xyz.astype(np.float32), np.repeat(np.arange(len(elevations)), len(azimuth)).astype(np.int32)


def snapshot(cal):
    axis = getattr(cal, '_scan_axis', None)
    return {'periods': cal._frames, 'confirmed': cal._config_passed,
            'status': cal.state.status, 'conflict': getattr(cal.state, 'orientation_conflict', False),
            'observations': len(cal._obs), 'recent': len(cal._recent), 'since_obs': cal._since_obs,
            'scan_axis': None if axis is None else axis.tolist(),
            'R': cal.R.tolist()}


def state_probes():
    real_observe = mod.observe_mount
    passing = mod.MountObservation(ok=True, rail_score=.2, roll=np.radians(3), pitch=0,
                                  yaw=0, height=2, lateral=0, forward_ratio=20)
    side = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
    xyz, ring = cones(rotation=side)
    result = {'observation_stub': asdict(passing)}
    try:
        mod.observe_mount = lambda *a, **kw: passing
        # Reproduce supported opt-outs. A scan axis is not gravity.
        for name, keep, search, enabled in [('conflict_no_search', True, False, True),
                                            ('unconstrained_mode', False, False, True),
                                            ('disabled', True, True, False)]:
            cfg = DetectorConfig()
            cfg.calibration.keep_up_axis = keep
            cfg.calibration.search_orientations = search
            cfg.calibration.enabled = enabled
            cal = mod.MountCalibrator(cfg.calibration, cfg.track)
            for _ in range(4):
                cal.update(xyz, cal.apply(xyz), None, ring=ring)
            result[name] = snapshot(cal)
        assert result['conflict_no_search']['conflict']
        assert not result['unconstrained_mode']['conflict']
        assert result['unconstrained_mode']['confirmed']
        assert result['disabled']['status'] == 'disabled'
        # Actual frame samples: default cadence vs supported overrides.
        result['cadence'] = []
        for spacing in (1, 10):
            for periods in (1, 2, 5):
                for remounted in (False, True):
                    cfg = DetectorConfig()
                    cfg.calibration.frames = 5
                    cfg.calibration.obs_spacing = spacing
                    cal = mod.MountCalibrator(cfg.calibration, cfg.track)
                    p, ids = cones(rotation=side if remounted else None)
                    trace = []
                    for _ in range(45):
                        cal.update(p, cal.apply(p), None, periods=periods, ring=ids)
                        trace.append(snapshot(cal))
                        if cal.frozen:
                            break
                    result['cadence'].append({'spacing': spacing, 'periods_per_frame': periods,
                                              'remounted': remounted, 'trace': trace})
        # A conflict survives absent rings; evidence arriving after geometry
        # has passed is ignored (pre-existing confirmation latch).
        cfg = DetectorConfig()
        cfg.calibration.search_orientations = False
        cal = mod.MountCalibrator(cfg.calibration, cfg.track)
        cal.update(xyz, xyz, None, ring=ring)
        cal.update(xyz, xyz, None, ring=None)
        result['missing_after_conflict'] = snapshot(cal)
        assert cal.state.orientation_conflict and not cal._config_passed
        cal = mod.MountCalibrator(cfg.calibration, cfg.track)
        cal.update(xyz, xyz, None, ring=None)
        cal.update(xyz, xyz, None, ring=ring)
        result['late_after_false_geometry_confirmation'] = snapshot(cal)
        assert cal._config_passed and cal._scan_axis is None and not cal.state.orientation_conflict
    finally:
        mod.observe_mount = real_observe
    return result


def real_late_rings(repo, cache):
    sys.path.insert(0, str(repo / 'docs/evidence/rejudge_2026-10-16/scripts'))
    import os
    os.environ['RESENSE_REPO'] = str(repo)
    from judge_runner import NodeReplica, node_decision
    from range_test import run_frame
    meta = json.loads((cache / 'meta.json').read_bytes())
    rotation = mod.orientation_candidates()[4]
    result = {}
    for variant in ('normal_channels', 'first_frame_no_ring'):
        rep = NodeReplica()
        rows = []
        for i, m in enumerate(meta[:9]):
            with np.load(cache / f'f_{i:05d}.npz') as d:
                rvs = rep.R_vs.astype(np.float64)
                xyz = ((d['xyz'].astype(np.float64) @ rvs.T @ rotation.T) @ rvs).astype(np.float32)
                m = dict(m)
                if variant == 'first_frame_no_ring' and i == 0:
                    m['has_ring'] = False
                res = run_frame(rep, xyz, d['inten'], d['ring'], m, i)
            rows.append({'i': i, 'decision': node_decision(res), 'mount': res.mount,
                         'nearest': res.nearest_distance, **snapshot(rep.detector.calib)})
        result[variant] = rows
    assert not any(r['decision'] == 'STOP' for r in result['normal_channels'])
    assert any(r['decision'] == 'STOP' for r in result['first_frame_no_ring'])
    return result


def real_short_window(repo, cache):
    """Supported YAML overrides; compare corrected identity with new recovery.

    The high provisional threshold disables the early provisional correction so
    the final observation cadence is visible. No observation or detection stub.
    """
    import os
    os.environ['RESENSE_REPO'] = str(repo)
    sys.path.insert(0, str(repo / 'docs/evidence/rejudge_2026-10-16/scripts'))
    from judge_runner import NodeReplica, node_decision, det_dict
    from range_test import run_frame
    meta = json.loads((cache / 'meta.json').read_bytes())
    result = {'overrides': {'calibration.frames': 5, 'calibration.obs_spacing': 1,
                            'calibration.provisional_min_deg': 10.0}, 'cases': {}}
    for rotation_index in (0, 4):
        rep = NodeReplica(overrides=result['overrides'])
        rotation = mod.orientation_candidates()[rotation_index]
        rows = []
        for i, m in enumerate(meta[:15]):
            with np.load(cache / f'f_{i:05d}.npz') as d:
                rvs = rep.R_vs.astype(np.float64)
                xyz = d['xyz']
                if rotation_index:
                    xyz = ((xyz.astype(np.float64) @ rvs.T @ rotation.T) @ rvs).astype(np.float32)
                res = run_frame(rep, xyz, d['inten'], d['ring'], m, i)
            rows.append({'i': i, 'decision': node_decision(res), 'mount': res.mount,
                         'dets': [det_dict(d) for d in res.detections], **snapshot(rep.detector.calib)})
        result['cases'][str(rotation_index)] = rows
    from audit_evidence import hits
    labels = json.loads((repo / 'labels/doubleT_obstacle.json').read_bytes())
    before, _ = hits(result['cases']['0'], labels)
    after, _ = hits(result['cases']['4'], labels)
    result['matched_frame_sets'] = {
        'identity': {k: sorted(v) for k, v in before.items()},
        'rotation_4': {k: sorted(v) for k, v in after.items()}}
    result['lost_matched_stop_frames'] = {name: sorted(frames - after.get(name, set()))
                                          for name, frames in before.items()}
    result['preserves_matched_stop'] = not any(result['lost_matched_stop_frames'].values())
    return result


def geometry_probes():
    result = {}
    for name, el in [('six_distinct_cones', (-.24, -.11, -.02, .04, .12, .22)),
                     ('three_ids_two_distinct_cones', (-.2, -.2, .2)),
                     ('three_ids_one_cone', (.1, .1, .1))]:
        p, ids = cones(el)
        axis = mod.scan_axis(p, ids)
        result[name] = None if axis is None else axis.tolist()
    p, ids = cones()
    for name, bad in [('float_ids', ids.astype(float)), ('two_dimensional_ids', ids[:, None]),
                      ('missing', None), ('constant', np.zeros_like(ids)),
                      ('negative', -np.ones_like(ids)), ('short', ids[:10]),
                      ('mixed', np.random.default_rng(13).permutation(ids))]:
        axis = mod.scan_axis(p, bad)
        result[name] = None if axis is None else axis.tolist()
        assert axis is None, name
    # Shuffling point order must not introduce dependence on channel ordering.
    ix = np.random.default_rng(14).permutation(len(ids))
    axis = mod.scan_axis(p[ix], ids[ix])
    result['shuffled_points'] = None if axis is None else axis.tolist()
    assert axis is not None and abs(axis[2]) > .999
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', type=Path, default=Path('/home/aiops/resense'))
    ap.add_argument('--cache', type=Path, default=Path('/tmp/opencode/resense-b4-data/decoded/roundT_squareT_pressureGate_squareT'))
    ap.add_argument('--out', type=Path)
    ap.add_argument('--only-short-window', action='store_true', help='minimal real B1 reproduction (30 frames)')
    ap.add_argument('--assert-no-loss', action='store_true', help='exit 1 if the real B1 probe loses a matched STOP')
    a = ap.parse_args()
    import resense
    assert Path(resense.__file__).resolve().parent == (a.repo / 'resense').resolve()
    result = {'source_sha256': {f'resense/{name}.py': hashlib.sha256((a.repo / f'resense/{name}.py').read_bytes()).hexdigest()
                                for name in ('calibration', 'detector', 'health')},
              'real_short_window': real_short_window(a.repo, a.cache.parent / 'doubleT_obstacle')}
    if not a.only_short_window:
        result.update(geometry=geometry_probes(), state=state_probes(),
                      real_late_ring_replay=real_late_rings(a.repo, a.cache))
    text = json.dumps(result, indent=2)
    if a.out:
        a.out.write_text(text + '\n')
    print(json.dumps({'geometry': result.get('geometry'),
                      'real_late_ring_decisions': {k: [r['decision'] for r in v] for k, v in result.get('real_late_ring_replay', {}).items()},
                      'real_short_window_decisions': {k: [r['decision'] for r in v] for k, v in result['real_short_window']['cases'].items()},
                      'lost_matched_stop_frames': result['real_short_window']['lost_matched_stop_frames'],
                      'cadence': [{k: v for k, v in c.items() if k != 'trace'} |
                                  {'frozen_frame': len(c['trace']) - 1}
                                  for c in result.get('state', {}).get('cadence', [])]}, indent=2))
    if a.assert_no_loss and not result['real_short_window']['preserves_matched_stop']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
