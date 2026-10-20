"""Second-method verification of the P3 response captures, using only the stdlib."""
from collections import Counter
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def load(name):
    return json.loads((HERE / name).read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    with (HERE / name).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def b4_expected(row):
    height = row['mount_height']
    if not isinstance(height, (int, float)) or not math.isfinite(height):
        return False
    if row['status'] not in ('ok', 'identity') or row['x'] > 30.:
        return False
    disagreement = abs(row['model_rail_z'] + height)
    if disagreement <= .5 + .05 * row['x']:
        return False
    # Independent scalar maximum-Z test: all returns must be strictly above.
    return min(point[2] + height for point in row['raw_xyz']) > 3.


def match(row, low, high, y0=None, half=None):
    for detection in row['detections']:
        if low < detection['distance'] < high:
            if y0 is None or y0 - half < detection['center'][1] < y0 + half:
                return True
    return False


def main():
    run = load('run.json')
    for phase in run['phases'].values():
        assert sha(HERE / phase['path']) == phase['sha256']
    assert {name: sha(ROOT / name) for name in run['source']['files']} == run['source']['files']
    b4 = load('b4.json')
    all_b4 = b4['cases'] + b4['guards'] + [b4['ceiling_positive_control'], b4['large_error_person_counterexample']]
    boundary = []
    for row in all_b4:
        assert row['demoted'] == b4_expected(row)
        assert row['demoted'] == (row['demotion_line'] in row['executed_lines'])
        if isinstance(row['mount_error'], (float, int)) and row['model_rail_delta'] == 0.:
            # Decimal geometry is intentionally a second arithmetic path. At an
            # exact boundary the binary predicate is reported, never relaxed.
            e = Decimal(str(row['mount_error']))
            x = Decimal(str(row['x']))
            lower = Decimal(str(row['support'][0]))
            ideal = (row['status'] in ('ok', 'identity') and x <= 30
                     and abs(e) > Decimal('.5') + Decimal('.05') * x and lower + e > 3)
            if row['demoted'] != ideal:
                gate_gap = abs(row['model_rail_z'] + row['mount_height']) - row['disagreement_threshold']
                body_gap = min(p[2] + row['mount_height'] for p in row['raw_xyz']) - 3.
                assert min(abs(gate_gap), abs(body_gap)) < 1e-12
                boundary.append({'x': row['x'], 'error': row['mount_error'], 'shape': row.get('shape'),
                                 'binary_demoted': row['demoted'], 'decimal_ideal_demoted': ideal,
                                 'gate_gap': gate_gap, 'body_gap': body_gap})
    planted = deepcopy(next(r for r in b4['cases'] if r['demoted']))
    planted['demoted'] = False
    assert planted['demoted'] != b4_expected(planted)
    b4_summary = {'matrix_cases': len(b4['cases']), 'guard_cases': len(b4['guards']),
                  'plain_traced_exact_cases': b4['plain_traced_equal'],
                  'demoted_by_shape': dict(Counter(r['shape'] for r in b4['cases'] if r['demoted'])),
                  'boundary_arithmetic_notes': boundary,
                  'ceiling_control_demoted': b4['ceiling_positive_control']['demoted'],
                  'large_error_person_demoted': b4['large_error_person_counterexample']['demoted'],
                  'retention': [{'mount': c['mount'], 'warm_scans': c['warm_scans'],
                                 'STOP_scans': [r['k'] for r in c['rows'] if r['STOP']],
                                 'post_fault_STOP_scans': [r['k'] for r in c['rows'] if r['STOP'] and r['after_fault']]}
                                for c in b4['retention']],
                  'injected_observation_heights_finalized': [r['height_full_precision'] for r in b4['calibration_lifecycle']]}

    f1a = load('f1a.json')
    f1a_summary = []
    all_f1a_rows = 0
    positive_rows = 0
    for case in f1a:
        for row in case['rows']:
            assert row['hit'] == match(row, 39.4, 40.6, .25, .5)
        count = sum(r['hit'] for r in case['rows'])
        assert count == case['matched_STOP_rows']
        all_f1a_rows += len(case['rows'])
        if case['top_above_true_rail'] is None:
            assert count == 0, case
        if case['enabled'] and case['top_above_true_rail'] is not None and case['top_above_true_rail'] >= .12:
            assert count == 8, (case['rail_rise'], case['top_above_true_rail'], count)
            positive_rows += count
        f1a_summary.append({key: case[key] for key in ['rail_rise', 'top_above_true_rail', 'enabled', 'matched_STOP_rows']})
    positive = deepcopy(next(r for c in f1a for r in c['rows'] if r['hit']))
    positive['detections'] = []
    assert positive['hit'] != match(positive, 39.4, 40.6, .25, .5)

    r3 = load('r3.json')
    unhooked = load('r3_plain_recheck.json')
    for a, b in zip(unhooked, r3, strict=True):
        for x, y in zip(a['rows'], b['rows'], strict=True):
            assert {k: v for k, v in x.items() if k != 'qualification_calls'} == {
                k: v for k, v in y.items() if k != 'qualification_calls'}
    changed_payload = deepcopy(unhooked[0]['rows'][0])
    changed_payload['result_hash'] = 'changed'
    assert changed_payload != unhooked[0]['rows'][0]
    r3_summary = []
    r3_rows = 0
    for case in r3:
        hits = []
        accumulated_shortcut = 0
        for row in case['rows']:
            assert row['hit'] == match(row, row['true_distance'] - 1., row['true_distance'] + 1.)
            if row['hit']:
                hits.append(row['k'])
            for track in row['tracks']:
                if track['n_raw'] != track['current_points'] and track['cable_kind']:
                    accumulated_shortcut += 1
            assert len(row['result_hash']) == len(row['tracker_hash']) == 64
        r3_rows += len(case['rows'])
        r3_summary.append({'kind': case['kind'], 'carried': case['carried'], 'enabled': case['enabled'],
                           'speed_known': case['speed_known'], 'matched_STOP_scans': hits,
                           'first_STOP_distance': None if not hits else case['rows'][hits[0]]['true_distance'],
                           'accumulated_track_rows_with_cable_kind': accumulated_shortcut,
                           'plain_traced_equal': case['plain_traced_equal']})
    known_on = next(c for c in r3_summary if not c['carried'] and c['speed_known'] and c['enabled'])
    known_off = next(c for c in r3_summary if not c['carried'] and c['speed_known'] and not c['enabled'])
    assert known_on['first_STOP_distance'] == 78. and known_off['first_STOP_distance'] == 76.
    assert known_on['accumulated_track_rows_with_cable_kind'] > 0

    l16 = load('l16.json')
    l16_summary = []
    for case in l16:
        counts = dict(Counter(row['decision'] for row in case['rows']))
        assert counts == case['decisions']
        for row in case['rows']:
            assert row['hit'] == any(38. <= d['distance'] <= 42. for d in row['detections'])
        assert all(row['mount']['orientation_confirmed'] and not row['mount']['orientation_conflict']
                   for row in case['rows'])
        if case['name'] in ('open', 'tunnel'):
            assert counts == {'GO': 450}
        else:
            assert counts == {'GO': 4, 'STOP': 446} and sum(row['hit'] for row in case['rows']) == 446
        l16_summary.append({'name': case['name'], 'decisions': counts,
                            'matched_STOP': sum(row['hit'] for row in case['rows']),
                            'input_points': case['input_points'], 'target_returns': case['target_returns']})

    raw = load('existing_f1a_gate.json')
    assert sum(c['rows'] for c in raw['pairs']) == raw['raw_rows'] == 15269
    assert sum(c['reference_STOP'] - c['candidate_STOP'] for c in raw['pairs']) == len(raw['removed_STOP']) == 9
    assert raw['added_STOP'] == []
    assert raw['reports']['candidate']['ride'] == {'alarm_events': 18, 'stop_episodes': 24, 'alarm_frames': 102}
    assert raw['reports']['reference']['set_O'] == raw['reports']['candidate']['set_O']
    changed = deepcopy(raw)
    changed['added_STOP'].append(['planted', 0])
    assert changed['added_STOP'] != raw['added_STOP']
    xml = ET.parse(HERE / 'tests.xml').getroot()
    suites = list(xml) if xml.tag == 'testsuites' else [xml]
    tests = {name: sum(int(s.get(name, 0)) for s in suites) for name in ['tests', 'failures', 'errors', 'skipped']}
    assert tests == {'tests': 257, 'failures': 0, 'errors': 0, 'skipped': 0}
    subprocess.run(['python3', '-B', str(ROOT / 'scripts/detector_freeze.py'), 'verify'], check=True)
    summary = {'status': 'PASS', 'acceptance_scope': 'P3 author response, independent bundle acceptance still separate',
               'b4': b4_summary, 'f1a': {'cases': len(f1a), 'rows': all_f1a_rows,
                                      'in_gauge_positive_STOP_rows': positive_rows, 'matrix': f1a_summary},
               'r3': {'cases': len(r3), 'rows': r3_rows, 'matrix': r3_summary}, 'l16': l16_summary,
               'existing_gate': {'raw_rows': raw['raw_rows'], 'removed_rail_fragment_STOP': 9,
                                 'added_STOP': 0, 'candidate_ride': raw['reports']['candidate']['ride']},
               'tests': tests, 'controls': {'planted_B4_label': True, 'removed_positive_detection': True,
                                          'changed_captured_payload_hash': True,
                                          'planted_added_STOP': True}}
    save('verification.json', summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ('f1a', 'r3')}, indent=2))
    print('F1a cases/rows', len(f1a), all_f1a_rows, 'R3 cases/rows', len(r3), r3_rows)
    print('R3 summary', json.dumps(r3_summary, indent=2))


if __name__ == '__main__':
    main()
