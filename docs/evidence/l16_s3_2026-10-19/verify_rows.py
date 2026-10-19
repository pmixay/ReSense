"""Re-derive author results from raw rows; summaries are checked, not trusted."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

repo = Path('/home/aiops/resense')
here = repo / 'docs/evidence/l16_s3_2026-10-19'
work = Path('/tmp/opencode/l16-s3/run4')
sys.path.insert(0, str(repo))
from resense.calibration import orientation_candidates  # noqa: E402


def read_rows(directory, case):
    path = directory / f'case_{case:02d}.jsonl'
    summary = json.loads((directory / f'case_{case:02d}.json').read_text())
    assert summary['numpy_version'] == '1.26.4'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == summary['raw_sha256']
    rows = [json.loads(line) for line in path.open()]
    assert [r['i'] for r in rows] == list(range(summary['frames']))
    stops = [r['i'] for r in rows if r['result']['obstacle']]
    assert stops == summary['stops']
    for row in rows:
        result = row['result']
        assert bool(result['detections']) == result['obstacle']
        assert np.isfinite(row['R']).all()
    # Independent matrix check rather than trusting the runner's internal label.
    rotation = orientation_candidates()[case]
    wrong = [r['i'] for r in rows if r['mapping_confirmed'] and
             np.degrees(np.arccos(np.clip((np.trace(np.asarray(r['R']) @ rotation) - 1) / 2, -1, 1))) > 45]
    assert wrong == summary['accepted_wrong']
    return rows, summary


def normalized(result):
    result = deepcopy(result)
    result.pop('timing_ms', None)
    health = result.get('health', {})
    health.pop('latency_p95_ms', None)
    health['messages'] = [m for m in health.get('messages', []) if not m.startswith('latency p95')]
    # latency_affects_decision=false: decision_level retains all non-timing health causes.
    health['level'] = health.get('decision_level', health.get('level'))
    replay = result.get('mount', {}).get('orientation_replay', {})
    for key in ('replay_ms', 'physical_call_ms', 'physical_cpu_ms'):
        replay.pop(key, None)
    return result


def object_matches(rows):
    labels = json.loads((repo / 'labels/doubleT_obstacle.json').read_text())
    matched = {}
    for row in rows:
        for obj in labels.get(f"{row['i']:05d}", []):
            if not obj.get('in_gauge') or not obj.get('plausible', True) or obj.get('n_points', 1) == 0:
                continue
            length, width = obj.get('size', [.5, .5, .5])[:2]
            lateral = (sum(p[1] for p in obj['bbox']) / 2 if 'bbox' in obj
                       else obj.get('lateral_sensor', obj.get('lateral', 0)))
            hits = [d for d in row['result']['detections']
                    if abs(d['distance'] - obj['distance']) <= max(2, .03 * obj['distance']) + length / 2
                    and abs(d['center'][1] - lateral) <= 1 + width / 2]
            if hits:
                name = obj.get('label', obj.get('name'))
                matched.setdefault(name, set()).add(row['i'])
    return matched


report = {'scope': 'P3 author verification; not independent P4 acceptance', 'groups': {}, 'failures': []}
for name, expected_frames in [('pandar-empty-ringfree', 545), ('pandar-positive-ringfree', 201),
                              ('falcon', 4443), ('pandar-positive-ring', 201), ('pandar-empty-ring', 545)]:
    candidate = work / (name + '-candidate')
    summary = json.loads((candidate / 'summary.json').read_text())
    assert summary['source_unchanged']
    assert {s['index'] for s in summary['cases']} == set(range(24))
    control_rows, control = read_rows(candidate, 0)
    control_stops = set(control['stops'])
    positive_control = object_matches(control_rows) if 'positive' in name else {}
    if 'positive' in name:
        assert len(control_stops) == 193
        assert {'person_crossing', 'object_on_rail'} <= positive_control.keys()
    if name == 'falcon':
        assert len(control_stops) == 1387
    ambiguous = name == 'pandar-positive-ringfree'
    group = {'frames_per_case': expected_frames, 'cases': [], 'candidate_source': summary['source'],
             'scope': ('Unresolved 360-degree ring-free control: abstention is intentional; inherited L16 remains.'
                       if ambiguous else 'Directional-FOV recovery or existing B4 channel support')}
    reference = work / (name + '-reference')
    if reference.exists():
        original, _ = read_rows(reference, 0)
        assert len(original) == expected_frames
        diff = [i for i, (a, b) in enumerate(zip(original, control_rows))
                if normalized(a['result']) != normalized(b['result'])]
        group['unrotated_reference_diff_frames'] = diff
        if diff:
            report['failures'].append({'group': name, 'unrotated_source_diff': diff})
        if 'empty' in name or name == 'falcon':
            group['old_sideways_controls'] = []
            for index in (4, 5):
                old_rows, old = read_rows(reference, index)
                group['old_sideways_controls'].append({'case': index, 'STOP_frames': len(old['stops']),
                                                      'wrong_accepted': len(old['accepted_wrong'])})
    for index in range(24):
        rows, s = read_rows(candidate, index)
        assert len(rows) == expected_frames
        side = abs(orientation_candidates()[index][2, 2]) != 1
        item = {'case': index, 'sideways': bool(side), 'STOP_frames': len(s['stops']),
                'first_STOP': s['first_stop'], 'first_correct_mapping': s['first_mapping'],
                'wrong_accepted_frames': len(s['accepted_wrong']),
                'lost_vs_correct_control': sorted(control_stops - set(s['stops'])),
                'added_vs_correct_control': sorted(set(s['stops']) - control_stops)}
        if positive_control:
            matches = object_matches(rows)
            item['lost_matched_object_frames'] = {label: sorted(frames - matches.get(label, set()))
                                                  for label, frames in positive_control.items()}
        # Existing upright nonidentity startup timing is not compared with a new
        # correctly-oriented control. It has its same-rotation ring reference.
        if not ambiguous and side and (item['lost_vs_correct_control'] or
                     any(item.get('lost_matched_object_frames', {}).values())):
            report['failures'].append({'group': name, **item})
        if not ambiguous and (s['accepted_wrong'] or s['first_mapping'] != (0 if index == 0 else 1)):
            report['failures'].append({'group': name, 'mapping': item})
        if 'empty' in name and s['stops']:
            report['failures'].append({'group': name, 'empty_STOP': item})
        if ambiguous and index in (0, 4, 5, 12):
            old_rows, old = read_rows(reference, index)
            item['changed_rows_vs_same_rotation_reference'] = [
                i for i, (a, b) in enumerate(zip(old_rows, rows))
                if normalized(a['result']) != normalized(b['result'])]
            if item['changed_rows_vs_same_rotation_reference']:
                report['failures'].append({'group': name, 'changed_ambiguous_control': item})
        if name == 'pandar-positive-ring':
            old_rows, old = read_rows(reference, index)
            old_matches, new_matches = object_matches(old_rows), object_matches(rows)
            item['lost_vs_same_rotation_reference'] = sorted(set(old['stops']) - set(s['stops']))
            item['lost_objects_vs_same_rotation_reference'] = {
                label: sorted(frames - new_matches.get(label, set())) for label, frames in old_matches.items()}
            if item['lost_vs_same_rotation_reference'] or any(item['lost_objects_vs_same_rotation_reference'].values()):
                report['failures'].append({'group': name, 'same_rotation_loss': item})
        group['cases'].append(item)
    report['groups'][name] = group
    print(name, Counter(c['STOP_frames'] for c in group['cases']), flush=True)

report['instrumentation'] = []
for index in (0, 4):
    plain, _ = read_rows(work / 'instrumentation-plain', index)
    traced, stats = read_rows(work / 'instrumentation-traced', index)
    assert len(plain) == len(traced) == 100
    differences = []
    for a, b in zip(plain, traced):
        a, b = deepcopy(a), deepcopy(b)
        a['result'], b['result'] = normalized(a['result']), normalized(b['result'])
        if a != b:
            differences.append(a['i'])
    item = {'case': index, 'frames': 100, 'different_non_timing_rows': differences, 'counts': stats['counts']}
    report['instrumentation'].append(item)
    assert not differences
    assert stats['counts']['search'] == (0 if index == 0 else 2)
    assert stats['counts']['max_search_points'] <= 60000
report['passed'] = not report['failures']
node_old = [json.loads(line) for line in (work / 'falcon-node-reference/baseline.jsonl').open()]
node_new = [json.loads(line) for line in (work / 'falcon-node-candidate/baseline.jsonl').open()]
assert len(node_old) == len(node_new) == 4443
assert [r['i'] for r in node_old] == [r['i'] for r in node_new] == list(range(4443))
for side, source in [('reference', Path('/tmp/opencode/l16-s3/reference')), ('candidate', repo)]:
    identity = json.loads((work / f'falcon-node-{side}/summary.json').read_text())
    for name in ('resense/calibration.py', 'resense/detector.py', 'resense/_resense_native.so'):
        assert identity['source_hashes'][name] == hashlib.sha256((source / name).read_bytes()).hexdigest()
node_check = {'frames': 4443, 'decision_changes': [], 'detection_changes': [], 'warning_changes': [],
              'legacy_default_replay_events': []}
for old, new in zip(node_old, node_new):
    assert old['i'] == new['i'] and old['stamp'] == new['stamp']
    if old['decision'] != new['decision']:
        node_check['decision_changes'].append(old['i'])
    if old['dets'] != new['dets']:
        node_check['detection_changes'].append(old['i'])
    if old['warns'] != new['warns']:
        node_check['warning_changes'].append(old['i'])
    if 'orientation_replay' in new['mount_detail']:
        node_check['legacy_default_replay_events'].append(new['i'])
assert not any(node_check[k] for k in ('decision_changes', 'detection_changes', 'warning_changes',
                                     'legacy_default_replay_events'))
report['normal_falcon_node_replica'] = node_check
report['not_closed'] = ['General L16 without resolved directional/channel evidence',
                        'Physical sideways scanning plane / gravity inference',
                        'Formal committed-source X3 and independent P4 review']
(here / 'raw_review.json').write_text(json.dumps(report, indent=2) + '\n')
print('PASSED', report['passed'], 'failures', len(report['failures']))
if report['failures']:
    print(json.dumps(report['failures'][:5], indent=2))
sys.exit(0 if report['passed'] else 1)
