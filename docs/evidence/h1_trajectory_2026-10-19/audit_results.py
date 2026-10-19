"""Re-derive reference validation and merged-source checks from captured rows."""
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/h1-trajectory')
sys.path.insert(0, str(ROOT / 'scripts'))
import regression_gate as gate  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def direct_valid(row):
    # Independent matrix trace rotation check, not the runner's Rotation API.
    a, b, r = [np.asarray(row[key]['T']) for key in ['primary', 'alternate', 'reverse']]
    point = np.array(row['near_point'])
    delta = a @ r
    angle = np.degrees(np.arccos(np.clip((np.trace(delta[:3, :3])-1)/2, -1, 1)))
    distance = np.linalg.norm((a @ point)[:3]-(b @ point)[:3])
    closure = np.linalg.norm(delta[:3, 3])
    fitness = min(row[key]['stages'][-1]['fitness'] for key in ['primary', 'alternate', 'reverse'])
    gates = [('seed_disagreement', distance <= .1), ('reverse_translation', closure <= .1),
             ('reverse_rotation', angle <= .05), ('common_fitness', fitness >= .7)]
    branch = next((name for name, accepted in gates if not accepted), 'accepted')
    return branch, dict(projected_disagreement_m=float(distance), reverse_translation_m=float(closure),
                        reverse_rotation_deg=float(angle), min_fitness=float(fitness))


def main():
    spec = importlib.util.spec_from_file_location('h1_source_receipts', ROOT / 'docs/evidence/h1_core_2026-10-19/run_checks.py')
    receipts = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(receipts)
    source = receipts.sources(ROOT)
    report = dict(status='H1_OPEN_REFERENCE_NOT_VALIDATED', source_files=source,
                  source_fingerprint=hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest())
    executions = sorted(HERE.glob('*execution.json'))
    assert len(executions) == 6, len(executions)
    for path in executions:
        record = read(path)
        assert record['source_unchanged'] and record['source_sha256'] == source
        assert receipts.sha(WORK / (record['name']+'.log')) == record['log_sha256']
    report['source_receipts_verified'] = [p.name for p in executions]
    direct = read(WORK / 'direct-gicp-regularized-all.json')['rows']
    assert len(direct) == 36
    validated = []
    for row in direct:
        branch, values = direct_valid(row)
        assert row['consistent'] == (branch == 'accepted')
        for key, value in values.items():
            assert abs(value-row[key]) < 1e-4, (key, value, row[key])
        validated.append(dict(sequence=row['sequence'], frame=row['frame'], station=row['station'], branch=branch, **values))
    report['direct_validation'] = dict(rows=validated, counts=dict(Counter(r['branch'] for r in validated)))
    control = read(WORK / 'validation-reconstruction.json')['controls']
    converted = dict(primary=control['primary'], alternate=control['alternate'], reverse=control['reverse'], near_point=[15., 0., -1., 1.])
    assert direct_valid(converted)[0] == 'accepted'
    changed = deepcopy(converted)
    changed['alternate']['T'][1][3] += .5
    assert direct_valid(changed)[0] == 'seed_disagreement'
    report['positive_control'] = dict(known_partial_overlap_80m_accepted=True, corrupted_half_metre_rejected=True)
    report['landmark_validation'] = {}
    for name in ['A', 'C']:
        proposals = read(WORK / f'landmark-tracks-{name}.json')
        result = read(WORK / f'landmark-bundle-{name}-converged.json')
        assert result['success']
        poses = np.array([row['pose'] for row in result['rows']])
        original = {row['id']: row for row in proposals['retained']}
        verified = []
        for saved in result['validation']:
            track = original[saved['id']]
            assert track['validation_only']
            obs = track['observations']
            raw = np.asarray([row['center'] for row in obs])
            index = np.array([row['frame'] for row in obs])
            mapped = np.matmul(poses[index, :3, :3], raw[:, :, None])[:, :, 0] + poses[index, :3, 3]
            anchor = np.median(mapped[:min(5, len(mapped))], axis=0)
            error = np.linalg.norm(mapped-anchor, axis=1)
            percentiles = np.percentile(error, [50, 95, 100])
            assert np.max(np.abs(percentiles-saved['after']['residual_p50_p95_max'])) < 1e-9
            verified.append(dict(id=track['id'], frames=len(obs), baseline=track['baseline'], p95=float(percentiles[1]), maximum=float(percentiles[2])))
        report['landmark_validation'][name] = dict(training_landmarks=result['training_landmarks'], validation_tracks=verified,
            tracks_p95_at_most_10cm=sum(row['p95'] <= .1 for row in verified),
            checked_observations=sum(row['frames'] for row in verified))
    candidate = read(HERE / 'merged-gate.json')
    baseline = read(ROOT / 'docs/evidence/results/regression_baseline_2026-09-29_shell_off.json')
    comparison = gate.compare(baseline, candidate, [])
    assert not any(row['fails'] or row['allowed'] for row in comparison)
    raw_counts = {}
    for path in sorted((WORK / 'merged-gate-work').glob('*.jsonl')):
        values = rows(path)
        count = sum(bool(row['obstacle']) for row in values)
        raw_counts[path.stem] = dict(frames=len(values), STOP_frames=count)
        if path.stem in candidate['recordings']:
            assert len(values) == candidate['recordings'][path.stem]['frames']
            assert count == candidate['recordings'][path.stem]['alarm_frames']
    assert sum(row['frames'] for row in raw_counts.values()) == 15269
    parts = [value for key, value in raw_counts.items() if key.startswith('new_data_')]
    assert sum(value['frames'] for value in parts) == candidate['ride']['frames']
    assert sum(value['STOP_frames'] for value in parts) == candidate['ride']['alarm_frames']
    report['gate'] = dict(metrics=comparison, raw_counts=raw_counts, passed=True,
                          non_timing_verdicts=dict(Counter(row['verdict'] for row in comparison if not row['metric'].startswith('latency_ms.'))))
    main_gate = read(ROOT / 'docs/evidence/integration_2026-10-19/runs/gate_final_4cf8e27.json')
    main_delta = [row for row in gate.compare(main_gate, candidate, []) if not row['metric'].startswith('latency_ms.')]
    assert all(row['verdict'] == 'same' for row in main_delta)
    report['gate']['main_non_timing_metric_identity'] = dict(rows=len(main_delta), identical=True,
        reference='docs/evidence/integration_2026-10-19/runs/gate_final_4cf8e27.json')
    report['probes'] = {}
    for label in ['A-axis', 'C-person', 'E6']:
        old = read(Path('/tmp/opencode/h1-reference/probes-e-candidate') / (label+'.json'))
        new = read(WORK / 'probes-merged-candidate' / (label+'.json'))
        assert old['rows'] == new['rows']
        visible = [r for r in new['rows'] if r['X'] is not None and r['X'] > 3 and r['n_obj'] > 0]
        assert sum(r['hit'] for r in visible) == new['summary']['stop_frames']
        report['probes'][label] = dict(rows=len(new['rows']), identical_to_E=True, matched=sum(r['hit'] for r in visible), visible=len(visible), summary=new['summary'])
    old_falcon = rows(Path('/tmp/opencode/h1-reference/probes-e-candidate/Falcon.jsonl'))
    new_falcon = rows(WORK / 'probes-merged-candidate/Falcon.jsonl')
    assert len(old_falcon) == len(new_falcon) == 4443
    lost, added, changed_payload = [], [], []
    for a, b in zip(old_falcon, new_falcon, strict=True):
        assert a['i'] == b['i']
        if a['decision'] == 'STOP' and b['decision'] != 'STOP':
            lost.append(a['i'])
        if a['decision'] != 'STOP' and b['decision'] == 'STOP':
            added.append(a['i'])
        if a['dets'] != b['dets']:
            changed_payload.append(a['i'])
    assert lost == list(range(4394, 4402)) and not added and changed_payload == lost
    report['Falcon'] = dict(rows=4443, old_STOP=sum(row['decision']=='STOP' for row in old_falcon),
        merged_STOP=sum(row['decision']=='STOP' for row in new_falcon), removed_STOP=lost, added_STOP=added,
        detection_payload_changes=changed_payload,
        attribution='Exactly the eight ceiling STOP frames removed by H-prime in origin/main integration; other detection payloads are identical.')
    suites = ET.parse(WORK / 'merged-tests.xml').getroot()
    tests = suites.findall('.//testcase')
    failures = [dict(name=row.attrib['name'], file=row.attrib.get('classname'), message=row.find('failure').attrib.get('message')) for row in tests if row.find('failure') is not None]
    report['tests'] = dict(junit_cases=len(tests), failures=failures, subtests_included=True)
    assert len(failures) == 1 and failures[0]['name'] == 'test_child_process_inherits_hook_and_bad_source_fails_closed'
    with (HERE / 'audit-final.json').open('x') as stream:
        json.dump(report, stream, indent=2)
    print('DIRECT', report['direct_validation']['counts'])
    print('LANDMARKS', {name: {key: value for key, value in result.items() if key != 'validation_tracks'} for name, result in report['landmark_validation'].items()})
    print('GATE', report['gate']['non_timing_verdicts'])
    print('PROBES', {key: (row['matched'], row['visible']) for key, row in report['probes'].items()})
    print('FALCON', report['Falcon'])
    print('TESTS', report['tests'])


if __name__ == '__main__':
    main()
