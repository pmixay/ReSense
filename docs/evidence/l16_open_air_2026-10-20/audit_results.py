"""Independent row-level acceptance audit, with positive controls for losses."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/l16-open-air-work')
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
import regression_gate as gate  # noqa: E402
import robustness_battery as battery  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.calibration import orientation_candidates  # noqa: E402


def load(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(line) for line in path.open()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normal(value):
    value = deepcopy(value)
    value.pop('timing_ms', None)
    health = value.get('health', {})
    if health:
        # The inherited replay producer already omits p95 and its message. In
        # full gate rows, validate the diagnostic explanation before removing it.
        if 'latency_p95_ms' in health:
            timed = [m for m in health['messages'] if m.startswith('latency p95 ')]
            assert len(timed) <= 1
            for message in timed:
                match = re.fullmatch(r'latency p95 (\d+) ms over the (\d+) ms budget', message)
                assert match and abs(int(match[1]) - health['latency_p95_ms']) <= .551
                assert int(match[2]) == DetectorConfig().health.latency_budget_ms
            ranks = {'ok': 0, 'warn': 1, 'error': 2}
            assert ranks[health['level']] == max(ranks[health['decision_level']], int(bool(timed)))
        assert (health['level'] == 'error') == (health['decision_level'] == 'error')
        health.pop('latency_p95_ms', None)
        health['messages'] = [m for m in health['messages'] if not m.startswith('latency p95 ')]
        health['level'] = health['decision_level']
    replay = value.get('mount', {}).get('orientation_replay', {})
    for key in ('replay_ms', 'physical_call_ms', 'physical_cpu_ms'):
        replay.pop(key, None)
    return value


def decide(result):
    health = result['health']
    return ('STOP' if result['obstacle'] else
            'FAULT' if 'error' in (health['level'], health['decision_level']) else
            'CAUTION' if result['warning'] or health['decision_level'] == 'warn' else 'GO')


def analytic():
    before, after = [load(WORK / f'analytic-a-{side}.json') for side in ('reference', 'candidate')]
    traced = load(WORK / 'trace-a-candidate.json')
    report = {}
    for name in ('open', 'tunnel', 'positive'):
        a, b = [d['cases'][name] for d in (before, after)]
        assert a['xyz_sha256'] == b['xyz_sha256']
        assert len(a['rows']) == len(b['rows']) == 450
        for entry in (a, b):
            assert [r['frame'] for r in entry['rows']] == list(range(450))
            assert all(decide(r['result']) == r['decision'] for r in entry['rows'])
        old_stop, new_stop = [{r['frame'] for r in e['rows'] if r['decision'] == 'STOP'} for e in (a, b)]
        assert not old_stop - new_stop
        report[name] = {'before': dict(Counter(r['decision'] for r in a['rows'])),
                        'after': dict(Counter(r['decision'] for r in b['rows'])),
                        'lost_STOP': sorted(old_stop - new_stop), 'added_STOP': sorted(new_stop - old_stop),
                        'positive_fraction': b['positive_fraction'], 'cue': b['cue']}
        if name == 'open':
            assert report[name]['before'] == {'FAULT': 450}
            assert report[name]['after'] == {'GO': 450}
            assert all(r['state']['config_passed'] and r['state']['forward'] is None for r in b['rows'])
            trace_rows = traced['cases'][name]['rows']
            for x, y in zip(b['rows'], trace_rows, strict=True):
                assert normal(x['result']) == normal(y['result']) and x['state'] == y['state']
            # Actual executed rejecting return, not a reconstructed cause label.
            assert ['directional_axes', 312] in trace_rows[0]['trace_lines']
        elif name == 'tunnel':
            assert report[name]['before'] == report[name]['after'] == {'GO': 450}
            assert all(normal(x['result']) == normal(y['result']) for x, y in zip(a['rows'], b['rows'], strict=True))
        else:
            def matched(entry):
                return {r['frame'] for r in entry['rows'] if any(
                    abs(d['distance'] - 40.) < 2.5 and abs(d['center'][1] - .25) < 1.
                    for d in r['result']['detections'])}
            ma, mb = matched(a), matched(b)
            assert ma and not ma - mb
            report[name].update(before_matched=len(ma), after_matched=len(mb))
    report['instrumentation_rows_equal'] = 450
    return report


def same_recorded_row(a, b):
    assert a['i'] == b['i']
    assert normal(a['result']) == normal(b['result'])
    assert a['R'] == b['R'] and a['mapping_confirmed'] == b['mapping_confirmed']


def recordings(phases=('prefix', 'full')):
    report = {}
    total = 0
    for phase in phases:
        for group in ('falcon', 'empty-ringfree', 'positive-ringfree', 'empty-ring', 'positive-ring'):
            case_ids = range(24) if phase == 'prefix' else (0, 4, 5, 12)
            dirs = [WORK / f'{phase}-{group}-a-{side}' for side in ('reference', 'candidate')]
            summaries = [load(d / 'summary.json') for d in dirs]
            assert all(s['source_unchanged'] for s in summaries)
            assert summaries[0]['meta_sha256'] == summaries[1]['meta_sha256']
            details = []
            for case in case_ids:
                paths = [d / f'case_{case:02d}.jsonl' for d in dirs]
                data = [rows(p) for p in paths]
                metrics = [load(d / f'case_{case:02d}.json') for d in dirs]
                for path, rr, m in zip(paths, data, metrics, strict=True):
                    assert sha(path) == m['raw_sha256']
                    assert [r['i'] for r in rr] == list(range(m['frames']))
                    assert [r['i'] for r in rr if r['result']['obstacle']] == m['stops']
                    assert all(bool(r['result']['detections']) == r['result']['obstacle'] for r in rr)
                    rotation = orientation_candidates()[case]
                    wrong = [r['i'] for r in rr if r['mapping_confirmed'] and np.degrees(np.arccos(
                        np.clip((np.trace(np.asarray(r['R']) @ rotation) - 1) / 2, -1, 1))) > 45]
                    assert wrong == m['accepted_wrong']
                assert len(data[0]) == len(data[1])
                for a, b in zip(*data, strict=True):
                    try:
                        same_recorded_row(a, b)
                    except AssertionError as exc:
                        raise AssertionError((phase, group, case, a['i'])) from exc
                assert metrics[0]['accepted_wrong'] == metrics[1]['accepted_wrong']
                if group != 'positive-ringfree':
                    assert metrics[1]['first_mapping'] is not None and not metrics[1]['accepted_wrong']
                details.append({'case': case, 'rows': len(data[1]), 'STOP': len(metrics[1]['stops']),
                                'first_mapping': metrics[1]['first_mapping'],
                                'inherited_ambiguous_rows': len(metrics[1]['accepted_wrong'])})
                total += len(data[1])
            report[f'{phase}/{group}'] = details
    report['paired_rows_exact_except_registered_timing'] = total
    # Exercise the exact row comparator with an actual detection removed.
    rr = rows(WORK / f'{phases[0]}-positive-ring-a-candidate/case_00.jsonl')
    actual = next(r for r in rr if r['result']['detections'])
    damaged = deepcopy(actual)
    damaged['result']['detections'].pop()
    try:
        same_recorded_row(actual, damaged)
    except AssertionError:
        pass
    else:
        raise AssertionError('planted detection loss was not detected')
    report['planted_detection_loss_detected'] = True
    return report


def gate_results():
    a, b = [load(HERE / f'gate-a-{side}.json') for side in ('reference', 'candidate')]
    for value in (a, b):
        assert value['gate']['passed'] and not value['gate']['allow']
        assert not value['code']['uncommitted_detector_changes'] and not value['config']['set']
        assert value['native']['path'] == 'native'
    ma, mb = [gate.metrics(v) for v in (a, b)]
    ma, mb = [{k: v for k, v in m.items() if not k.startswith('latency_ms.')} for m in (ma, mb)]
    assert ma == mb
    dirs = [WORK / f'gate-a-{side}' for side in ('reference', 'candidate')]
    names = sorted(p.name for p in dirs[0].glob('*.jsonl'))
    assert names == sorted(p.name for p in dirs[1].glob('*.jsonl')) and len(names) == 15
    total, stops = 0, 0
    for name in names:
        aa, bb = [rows(d / name) for d in dirs]
        assert len(aa) == len(bb)
        for index, (x, y) in enumerate(zip(aa, bb, strict=True)):
            assert normal(x) == normal(y), (name, index)
            stops += bool(y['obstacle'])
        total += len(bb)
    sf = [load(d / 'setF_straight.json') for d in dirs]
    for value in sf:
        value['summary'].pop('wall_s')
    assert sf[0] == sf[1]
    return {'passed': True, 'non_timing_metric_tuples_equal': len(ma), 'ordinary_rows_equal': total,
            'STOP_rows': stops, 'set_F_sequences': len(sf[1]['sequences']),
            'set_F_rows_equal': sum(len(s['rows']) for s in sf[1]['sequences'])}


def x3():
    a, b = [load(WORK / f'x3-a-{side}.json') for side in ('reference', 'candidate')]
    for value in (a, b):
        battery.validated_entries(value, Path('/tmp/opencode/resense-b4-data/decoded'), ROOT)
    assert b['status'] == 'PASS' and len(b['entries']) == 40 and not b['errors']
    total, comparisons = 0, 0
    for key, entry in b['entries'].items():
        aa, bb = [rows(Path(e['entries'][key]['raw_path'])) for e in (a, b)]
        assert len(aa) == len(bb)
        for x, y in zip(aa, bb, strict=True):
            assert x['i'] == y['i'] and x['decision'] == y['decision']
            assert x['dets'] == y['dets'] and x['warns'] == y['warns']
        calc = battery.compare_metrics(a['entries'][key]['metrics'], entry['metrics'])
        assert calc == b['comparison']['cases'][key] and all(r['passed'] for r in calc)
        total += len(bb)
        comparisons += len(calc)
    positive = a['entries']['doubleT_obstacle/nominal']['metrics']
    bad = deepcopy(positive)
    bad['stop_frames'] -= 3
    assert any(not r['passed'] for r in battery.compare_metrics(positive, bad))
    return {'passed': True, 'cases': 40, 'rows': total, 'comparisons': comparisons,
            'lost_STOP_or_detection_rows': 0, 'planted_loss_detected': True}


def t1():
    data = load(WORK / 't1-a-candidate.json')
    assert len(data['bags']) == 12
    details = {}
    exposed = []
    for name, entry in data['bags'].items():
        assert len(entry['rows']) == 10 and [r['i'] for r in entry['rows']] == list(range(10))
        for r in entry['rows']:
            assert r['independent_raw_numpy_decode_equal']
            if r['before_cue'][0] == [0., 0., -1.]:
                exposed.append([name, r['i']])
            assert r['after_cue'][0] != [0., 0., -1.]
            if name == 'ride_start':
                assert r['prior_verified_ride_cache_exact']
        details[name] = {'minimum_above_fraction': min(r['positive_fraction'][2] for r in entry['rows']),
                         'first_before_cue': entry['rows'][0]['before_cue'],
                         'first_after_cue': entry['rows'][0]['after_cue'],
                         'confirmed_by_frame9': entry['rows'][-1]['mount']['orientation_confirmed']}
    assert data['positive_control']['before'][0] == [0., 0., -1.]
    assert data['positive_control']['after'] == [None, None]
    return {'raw_frames': 120, 'bags': details, 'old_A1_exposed_frames': exposed,
            'known_positive_detected_and_fixed': True, 'raw_ride_cache_checks': 10}


def sources():
    result = {}
    for path in HERE.glob('*-execution.json'):
        r = load(path)
        assert r['source_unchanged'] and sha(WORK / f"{r['name']}.log") == r['log_sha256']
        archive = WORK / f"{r['name']}-source.tar.gz"
        assert sha(archive) == r['source_archive_sha256']
        with tarfile.open(archive) as t:
            assert all(hashlib.sha256(t.extractfile(n).read()).hexdigest() == h for n, h in r['source_sha256'].items())
        result[r['name']] = {'commit': r['commit'], 'returncode': r['returncode'],
                             'source_unchanged': True, 'source_snapshot_reopened': True}
    assert result
    a, b = [load(HERE / f'analytic-a-{side}-execution.json')['source_sha256']
            for side in ('reference', 'candidate')]
    assert a.keys() == b.keys()
    changed = [name for name in a if a[name] != b[name]]
    assert changed == ['resense/calibration.py']  # positive control for source-difference detection
    result['paired_source_difference'] = changed
    return result


def tests():
    def cases(path):
        return {(c.get('classname'), c.get('name')):
                'failed' if c.find('failure') is not None else
                'error' if c.find('error') is not None else
                'skipped' if c.find('skipped') is not None else 'passed'
                for c in ET.parse(path).iter('testcase')}
    full = cases(WORK / 'tests-a-candidate.xml')
    failed = sorted(n for (_, n), status in full.items() if status == 'failed')
    assert failed == sorted(['test_timing_with_accumulation',
                            'test_child_process_inherits_hook_and_bad_source_fails_closed',
                            'test_status_marker_says_the_decision_and_publishing_errors_are_contained'])
    diagnosed = [cases(WORK / f'diagnose-a-{side}.xml') for side in ('reference', 'candidate')]
    assert diagnosed[0] == diagnosed[1]
    assert Counter(diagnosed[0].values()) == {'failed': 2, 'passed': 1}
    nodes = [cases(WORK / f'nodes-b-{side}.xml') for side in ('reference', 'candidate')]
    assert nodes[0] == nodes[1] and Counter(nodes[1].values()) == {'passed': 146}
    affected_source = Path('/tmp/opencode/l16-open-air-affected.xml')
    affected_target = WORK / 'affected-candidate.xml'
    if not affected_target.exists():
        with affected_target.open('xb') as stream:
            stream.write(affected_source.read_bytes())
    assert sha(affected_target) == sha(affected_source)
    affected = cases(affected_target)
    assert Counter(affected.values()) == {'passed': 242}
    assert affected.keys() <= full.keys() and all(full[key] == 'passed' for key in affected)
    red = cases(WORK / 'red-a-reference.xml')
    assert 'failed' in red.values()  # positive control for JUnit failure parsing
    return {'full_case_statuses_including_subtests': dict(Counter(full.values())),
            'full_failure_names': failed, 'affected_passed': 242,
            'paired_diagnosis_case_statuses_equal': True, 'paired_node_tests_passed': 146,
            'node_a_candidate_ring_field_test_failed':
                dict(Counter(cases(WORK / 'nodes-a-candidate.xml').values())),
            'node_transient_cause': 'unverified; exact test and complete later node suites pass',
            'all_green_suite_claim': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    checks = {'analytic': analytic, 'prefix': lambda: recordings(('prefix',)),
              'recordings': recordings, 'gate': gate_results, 'x3': x3, 't1': t1, 'sources': sources, 'tests': tests}
    parser.add_argument('phase', choices=list(checks))
    parser.add_argument('--quiet', action='store_true')
    args = parser.parse_args()
    report = checks[args.phase]()
    (HERE / f'audit-{args.phase}.json').write_text(json.dumps(report, indent=2) + '\n')
    if not args.quiet:
        print(json.dumps(report, indent=2))
