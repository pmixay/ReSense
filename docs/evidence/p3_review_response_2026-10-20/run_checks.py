"""Bounded P3 response checks; no production files or defaults are edited."""
from collections import Counter
from copy import deepcopy
from dataclasses import fields, is_dataclass
import hashlib
import inspect
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/p3-review-response-work')
SHIPPING = ROOT / 'docs/evidence/p4_review_shipping_2026-10-20/scripts'
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(SHIPPING))
sys.path.insert(0, str(ROOT / 'ros2_ws/src/resense_ros'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def exact(value):
    if isinstance(value, np.ndarray):
        return ('array', str(value.dtype), value.shape, hashlib.sha256(value.tobytes()).hexdigest())
    if is_dataclass(value):
        return [(f.name, exact(getattr(value, f.name))) for f in fields(value) if f.name != 'timing_ms']
    if isinstance(value, dict):
        return [(str(k), exact(v)) for k, v in sorted(value.items())]
    if isinstance(value, (list, tuple)):
        return [exact(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return ('float', float(value).hex())
    if isinstance(value, np.generic):
        return value.item()
    return value


def fingerprint(value):
    return hashlib.sha256(repr(exact(value)).encode()).hexdigest()


def install_runtime():
    manifest = json.loads((ROOT / 'docs/evidence/detector_freeze_2026-10-20_1.2.0_f1a.json').read_text())
    current = {name: sha(ROOT / name) for name in manifest['files']}
    assert current == manifest['files']
    original = Path('/home/aiops/resense')
    for name in ['native/resense_native.cpp', 'resense/_native.py', 'setup.py', 'pyproject.toml', 'scripts/build_native.sh']:
        assert sha(original / name) == current[name]
    native = original / 'resense/_resense_native.so'
    target = ROOT / 'resense/_resense_native.so'
    if not target.exists():
        shutil.copy2(native, target)
    assert sha(native) == sha(target)
    return {'seal': manifest['source_sha256'], 'files': current, 'native_sha256': sha(target)}


def controlled_cluster(x, heights, height=1.83, width=0.4):
    from resense.clustering import Cluster
    z = np.linspace(heights[0], heights[1], 12, dtype=np.float64) - height
    xyz = np.column_stack([x + np.linspace(0, 0.3, 12), np.linspace(-width / 2, width / 2, 12), z])
    c = Cluster(points_idx=np.arange(12), n=12, n_raw=12, centroid=xyz.mean(0),
                bbox_min=xyz.min(0), bbox_max=xyz.max(0), distance=x, lateral=0.,
                height_min=heights[0], height_max=heights[1], intensity=10.,
                n_expected=12., score=1., zone='gauge', n_gauge=12)
    return xyz, c


def b4_case(x, error, support, status='ok', delta=0., traced=False):
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.track import TrackModel
    xyz, cluster = controlled_cluster(x, support)
    det = Detector(DetectorConfig())
    det.track = TrackModel(np.array([0., 0., -1.83 - 0.35 + delta]), (3., 120.), 0., 0., 0., rail_offset=.35)
    det.calib.state.height = 1.83 + error if error is not None else None
    det.calib.state.status = status
    lines = []
    method = Detector._mount_cross_check
    source, first = inspect.getsourcelines(method)
    demote_line = next(first + i for i, s in enumerate(source) if 'cl.reason, cl.zone, cl.demoted =' in s)

    def trace(frame, event, arg):
        if frame.f_code is method.__code__:
            if event == 'line':
                lines.append(frame.f_lineno)
            return trace
        return None

    if traced:
        sys.settrace(trace)
    try:
        det._mount_cross_check([cluster], xyz)
    finally:
        sys.settrace(None)
    mount_height = det.calib.state.height
    rail_z = float(det.track.rail_z(x))
    threshold = det.cfg.cluster.mount_cross_tol + det.cfg.cluster.mount_cross_grade * x
    valid = mount_height is not None and np.isfinite(mount_height) and status in ('ok', 'identity')
    scalar = bool(valid and x <= det.cfg.cluster.mount_cross_range
                  and abs(rail_z + mount_height) > threshold
                  and all(float(point[2]) + mount_height > 3. for point in xyz))
    actual = cluster.reason == 'height_conflict'
    assert actual == scalar
    if traced:
        assert actual == (demote_line in lines)
    row = {'x': x, 'mount_error': error if error is None or np.isfinite(error) else str(error),
           'status': status, 'model_rail_delta': delta,
           'support': list(support), 'raw_xyz': xyz.tolist(),
           'mount_height': mount_height if mount_height is None or np.isfinite(mount_height) else str(mount_height),
           'model_rail_z': rail_z, 'disagreement_threshold': threshold, 'demoted': actual,
           'zone': cluster.zone, 'reason': cluster.reason, 'cluster_hash': fingerprint(cluster),
           'executed_lines': lines, 'demotion_line': demote_line}
    return row, cluster


def b4():
    from resense.calibration import MountCalibrator
    from resense.config import DetectorConfig
    from resense.tracking import Tracker
    errors = [-3.2, -1.6, -.8, 0., .3, .5, .749, .75, .750001, .8, .99, 1., 1.000001,
              1.5, 1.500001, 1.6, 2., 2.000001, 2.9, 3.2]
    supports = {'hanging': (2.7, 3.), 'person': (.2, 1.9), 'low': (.15, .25)}
    rows = []
    for x in [3., 5., 10., 20., 30., 30.001, 37.]:
        for label, support in supports.items():
            for error in errors:
                plain, a = b4_case(x, error, support)
                traced, b = b4_case(x, error, support, traced=True)
                assert exact(a) == exact(b)
                assert {k: v for k, v in plain.items() if k != 'executed_lines'} == {
                    k: v for k, v in traced.items() if k != 'executed_lines'}
                traced['shape'] = label
                rows.append(traced)
    guards = []
    for status in ['pending', 'provisional', 'fallback', 'disabled', 'identity', 'ok']:
        for error in [None, 1.6]:
            row, _ = b4_case(20., error, supports['hanging'], status=status, traced=True)
            guards.append(row)
    for error in [float('nan'), float('inf')]:
        row, _ = b4_case(20., error, supports['hanging'], traced=True)
        guards.append(row)
    ceiling, _ = b4_case(9.4, 0., (3.4, 3.7), delta=1.5, traced=True)
    assert ceiling['demoted']
    person, _ = b4_case(5., 3.2, supports['person'], traced=True)
    assert person['demoted']
    retention = []
    for label, error in [('valid_mount', 0.), ('wrong_mount', 1.6)]:
        _, clean = b4_case(20., 0., supports['hanging'])
        _, current = b4_case(20., error, supports['hanging'])
        for warm in [0, 12]:
            tracker = Tracker(DetectorConfig().tracking)
            history = []
            for k in range(warm + 12):
                tracker.update([deepcopy(clean if k < warm else current)], frame_dt=.1)
                history.append({'k': k, 'after_fault': k >= warm,
                                'STOP': any(t.zone == 'gauge' for t in tracker.confirmed()),
                                'tracks': [{'id': t.id, 'misses': t.misses, 'reported': t.reported,
                                            'zone': t.zone, 'zone_hist': list(t.zone_hist),
                                            'last_reason': t.last.reason} for t in tracker.tracks]})
            retention.append({'mount': label, 'warm_scans': warm, 'rows': history})
    lifecycle = []
    for error in [0., .8, 3.2]:
        detector_cfg = DetectorConfig()
        cal = MountCalibrator(detector_cfg.calibration, detector_cfg.track)
        cal._obs = [(0., 0., 0., 1.83 + error, 0.)] * detector_cfg.calibration.frames
        cal._frames = detector_cfg.calibration.frames * detector_cfg.calibration.obs_spacing
        cal._finish(False)
        lifecycle.append({'supplied_observation_height_error': error, 'state': cal.state.to_dict(),
                          'height_full_precision': cal.state.height,
                          'scope': 'consistent synthetic observation injection, not raw-cloud false-calibration exposure'})
        assert cal.state.status in ('ok', 'identity')
    return {'cases': rows, 'guards': guards, 'ceiling_positive_control': ceiling,
            'large_error_person_counterexample': person, 'retention': retention,
            'calibration_lifecycle': lifecycle, 'plain_traced_equal': len(rows)}


def deterministic(detector):
    if detector._previous_latency_ms is not None:
        detector._previous_latency_ms = 42.


def detection_rows(result):
    return [{'distance': float(d.distance), 'center': list(map(float, d.center)),
             'kind': d.kind, 'reason': d.reason, 'id': d.id} for d in result.detections]


def f1a():
    from f1a_capped_top import scene
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import Frame
    rows = []
    for rise in [0., .18, .20]:
        for top in [None, -.02, 0., .02, .05, .08, .10, .12, .17, .20, .25, .30]:
            frame, head = scene(rise, 40., top)
            for enabled in [False, True]:
                cfg = DetectorConfig()
                if not enabled:
                    cfg.lowobj.local_rail_margin = 0.
                det = Detector(cfg)
                records = []
                for k in range(12):
                    deterministic(det)
                    result = det.process(Frame(frame.xyz, frame.intensity, stamp=.1 * k))
                    detections = detection_rows(result)
                    matched = [d for d in detections if abs(d['distance'] - 40.) < .6 and abs(d['center'][1] - .25) < .5]
                    records.append({'k': k, 'detections': detections, 'hit': bool(matched),
                                    'global_STOP': bool(result.obstacle), 'result_hash': fingerprint(result)})
                rows.append({'rail_rise': rise, 'top_above_true_rail': top, 'enabled': enabled,
                             'true_rail_z': float(head), 'input_xyz_sha256': hashlib.sha256(frame.xyz.tobytes()).hexdigest(),
                             'input_points': len(frame.xyz), 'rows': records,
                             'matched_STOP_rows': sum(r['hit'] for r in records)})
    return rows


def r3_sequence(kind, carried, enabled, known, traced):
    import raycast as rc
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import Frame
    from resense.synthetic import effective_thickness
    from resense.tracking import Tracker
    cfg = DetectorConfig.from_yaml(ROOT / 'configs/default.yaml')
    if not enabled:
        cfg.tracking.cable_confirm_time_s = 0.
    detector = Detector(cfg)
    original = Tracker._qualifies
    events = []

    def qualifies(self, track, *args, **kwargs):
        result = original(self, track, *args, **kwargs)
        events.append({'id': track.id, 'distance': float(track.last.distance), 'hits': track.hits,
                       'span_s': track.span_s, 'cable_kind': track.cable_kind,
                       'cable_hits': track.cable_hits, 'cable_span_s': track.cable_span_s,
                       'n_raw': track.last.n_raw, 'current_points': len(track.last.points_idx),
                       'qualified': bool(result)})
        return result

    if traced:
        Tracker._qualifies = qualifies
    records = []
    count = 18 if carried else 62
    try:
        for k in range(count):
            distance = 37. if carried else 80. - k
            v = 15. if carried else 10.
            w = effective_thickness(.03, distance)
            bottom = 2.7 if kind == 'hanging' else .2
            box = (distance, distance + w, rc.AY - w / 2, rc.AY + w / 2,
                   rc.FLOOR + .18 + bottom, rc.AZ + rc.R + .5)
            frame = rc.frame(boxes=[box], seed=k)
            deterministic(detector)
            start = len(events)
            result = detector.process(Frame(frame.xyz, frame.intensity, stamp=.1 * k),
                                      ego_speed=v if known else None)
            detections = detection_rows(result)
            tracks = [t for t in detector.tracker.tracks if t.last is not None and t.misses == 0
                      and abs(t.last.distance - distance) < 1.5]
            records.append({'k': k, 'true_distance': distance, 'detections': detections,
                            'hit': any(abs(d['distance'] - distance) < 1. for d in detections),
                            'result_hash': fingerprint(result), 'tracker_hash': fingerprint(detector.tracker.tracks),
                            'input_xyz_sha256': hashlib.sha256(frame.xyz.tobytes()).hexdigest(),
                            'tracks': [{'id': t.id, 'cable_kind': t.cable_kind, 'cable_hits': t.cable_hits,
                                        'n_raw': t.last.n_raw, 'current_points': len(t.last.points_idx),
                                        'current_support': {name: getattr(t.last, name) for name in
                                                            ['current_n_gauge', 'current_height_min', 'current_height_max']
                                                            if hasattr(t.last, name)}} for t in tracks],
                            'qualification_calls': events[start:]})
    finally:
        Tracker._qualifies = original
    return {'kind': kind, 'carried': carried, 'enabled': enabled, 'speed_known': known, 'rows': records}


def r3():
    rows = []
    cases = [(kind, True, enabled, True) for kind in ['tall', 'hanging'] for enabled in [False, True]]
    cases += [('tall', False, enabled, known) for known in [False, True] for enabled in [False, True]]
    for case in cases:
        plain = r3_sequence(*case, traced=False)
        traced = r3_sequence(*case, traced=True)
        for a, b in zip(plain['rows'], traced['rows'], strict=True):
            assert {k: v for k, v in a.items() if k != 'qualification_calls'} == {
                k: v for k, v in b.items() if k != 'qualification_calls'}
        traced['plain_traced_equal'] = len(plain['rows'])
        rows.append(traced)
    return rows


def l16():
    import scene
    from resense.config import DetectorConfig
    from resense.detector import Detector
    from resense.frame import Frame
    from resense.calibration import directional_axes
    from resense_ros.decision_policy import evaluate_decision
    directions, ring = scene.rays(-104, 106)
    cases = []
    for label in ['open', 'tunnel', 'open_person']:
        extra = [(40., 0., .45, 1.9)] if label == 'open_person' else []
        source, labels = scene.frame(directions, ring, *scene.cast(directions, tunnel=label == 'tunnel',
                                                                 open_air=label != 'tunnel', specs=extra))
        detector = Detector(DetectorConfig())
        records = []
        for k in range(450):
            deterministic(detector)
            result = detector.process(Frame(source.xyz.copy(), source.intensity.copy(), ring=source.ring.copy(),
                                            stamp=.1 * k, frame_id='s'))
            detections = detection_rows(result)
            records.append({'k': k, 'decision': evaluate_decision(result).decision,
                            'detections': detections, 'hit': any(38. <= d['distance'] <= 42. for d in detections),
                            'mount': result.mount, 'result_hash': fingerprint(result)})
        cue = directional_axes(source.xyz)
        cases.append({'name': label, 'input_points': len(source.xyz),
                      'input_xyz_sha256': hashlib.sha256(source.xyz.tobytes()).hexdigest(),
                      'target_returns': int((labels >= 10).sum()),
                      'fraction_above_sensor': float((source.xyz[:, 2] > 0).mean()),
                      'cue': None if cue is None else [None if c is None else np.asarray(c).tolist() for c in cue],
                      'decisions': dict(Counter(r['decision'] for r in records)), 'rows': records})
    return cases


def existing_f1a_gate():
    original_work = Path('/tmp/opencode/f1a-completion-work')
    pairs = []
    losses, additions, total = [], [], 0
    candidate = original_work / 'gate-c-candidate'
    reference = original_work / 'gate-c-reference'
    for path in sorted(candidate.glob('*.jsonl')):
        old = reference / path.name
        a = [json.loads(line) for line in old.read_text().splitlines() if line.strip()]
        b = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        assert len(a) == len(b)
        total += len(a)
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            if x['obstacle'] and not y['obstacle']:
                losses.append([path.name, i])
            if y['obstacle'] and not x['obstacle']:
                additions.append([path.name, i])
        pairs.append({'name': path.name, 'rows': len(a), 'reference_sha256': sha(old),
                      'candidate_sha256': sha(path), 'reference_STOP': sum(bool(r['obstacle']) for r in a),
                      'candidate_STOP': sum(bool(r['obstacle']) for r in b)})
    assert total == 15269 and len(losses) == 9 and not additions
    reports = {}
    for side in ['reference', 'candidate']:
        path = ROOT / f'docs/evidence/f1a_completion_2026-10-20/gate-c-{side}.json'
        data = json.loads(path.read_text())
        reports[side] = {'sha256': sha(path), 'commit': data['code']['commit'],
                         'passed': data['gate']['passed'],
                         'ride': {name: data['ride'][name] for name in ['alarm_events', 'stop_episodes', 'alarm_frames']},
                         'set_O': data['set_O']['objects'], 'labelled_person': data['recordings']['doubleT_obstacle']['labelled']}
    assert reports['reference']['set_O'] == reports['candidate']['set_O']
    assert reports['reference']['labelled_person'] == reports['candidate']['labelled_person']
    return {'raw_rows': total, 'pairs': pairs, 'removed_STOP': losses, 'added_STOP': additions,
            'reports': reports, 'scope': 'recount of existing committed-source full-gate captures, not a new full gate'}


def main():
    assert os.environ['RESENSE_REPO'] == str(ROOT) and os.environ['PYTHONPATH'] == str(ROOT)
    assert WORK.parent.is_dir()
    WORK.mkdir(exist_ok=True)
    source = install_runtime()
    started = time.time()
    import resense
    assert Path(resense.__file__).resolve().is_relative_to(ROOT)
    report = {'measured_commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
              'source': source, 'numpy': np.__version__, 'protocol_sha256': sha(HERE / 'PROTOCOL.md'),
              'status': 'AUTHOR_RESPONSE_NOT_INDEPENDENT_ACCEPTANCE', 'phases': {}}
    for name, function in [('b4', b4), ('f1a', f1a), ('r3', r3), ('l16', l16), ('existing_f1a_gate', existing_f1a_gate)]:
        print('START', name, flush=True)
        value = function()
        save(HERE / f'{name}.json', value)
        report['phases'][name] = {'path': f'{name}.json', 'sha256': sha(HERE / f'{name}.json')}
        print('DONE', name, flush=True)
    assert {name: sha(ROOT / name) for name in source['files']} == source['files']
    report['source_unchanged'] = True
    report['wall_seconds'] = time.time() - started
    save(HERE / 'run.json', report)
    print(json.dumps({'status': report['status'], 'wall_seconds': report['wall_seconds'],
                      'phases': list(report['phases'])}, indent=2), flush=True)


if __name__ == '__main__':
    main()
