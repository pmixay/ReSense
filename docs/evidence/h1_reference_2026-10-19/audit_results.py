"""Independent E versus D raw gate/probe/X3 preservation audit."""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys

from run_checks import ROOT, HERE, WORK

spec = importlib.util.spec_from_file_location('h1_d_audit', ROOT / 'docs/evidence/h1_axis_range_2026-10-19/audit_results.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
BASE = Path('/tmp/opencode/h1-axis-range')


def read(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['gate', 'probes', 'x3'])
    phase = parser.parse_args().phase
    report = dict(phase=phase)
    if phase == 'gate':
        a, b = BASE / 'gate-d-candidate-work', WORK / 'gate-e-candidate-work'
        report['bags'] = {p.stem: old.compare(old.rows(p), old.rows(b / p.name), 'stamp', 'detections')
                          for p in sorted(a.glob('*.jsonl'))}
        sf_a, sf_b = (read(p / 'setF_straight.json')['sequences'] for p in [a, b])
        report['Set_F_equal'] = sf_a == sf_b
        report['Set_F_rows'] = sum(len(s['rows']) for s in sf_a)
        report['metrics'] = old.gate.compare(read(ROOT / 'docs/evidence/h1_axis_range_2026-10-19/gate-d-candidate.json'),
                                           read(HERE / 'gate-e-candidate.json'), [])
        report['metric_verdicts'] = dict(Counter(r['verdict'] for r in report['metrics'] if not r['metric'].startswith('latency_ms.')))
        report['PASS'] = sf_a == sf_b and all(not any(v[k] for k in ['lost_STOP', 'added_STOP', 'lost_payloads', 'changed_non_timing_rows'])
                                            for v in report['bags'].values())
    elif phase == 'probes':
        report['ranges'] = {}
        for label in ['A-axis', 'C-person', 'E6']:
            before, after = (read(p / f'{label}.json') for p in [BASE / 'probes-d-candidate', WORK / 'probes-e-candidate'])
            assert [(r['k'], r['X'], r['n_obj']) for r in before['rows']] == [(r['k'], r['X'], r['n_obj']) for r in after['rows']]
            a, b = ({r['k'] for r in d['rows'] if r['X'] is not None and r['X'] > 3 and r['n_obj'] > 0 and r['hit']}
                    for d in [before, after])
            report['ranges'][label] = dict(previous=before['summary'], candidate=after['summary'],
                lost=sorted(a - b), added=sorted(b - a),
                new_unmatched=[r for p, r in zip(before['rows'], after['rows'], strict=True)
                               if r['decision'] == 'STOP' and not r['hit'] and p['decision'] != 'STOP'])
        report['Falcon'] = old.compare(old.rows(BASE / 'probes-d-candidate/Falcon.jsonl'),
            old.rows(WORK / 'probes-e-candidate/Falcon.jsonl'), 'i', 'dets')
        report['PASS'] = (all(not v['lost'] and not v['new_unmatched'] for v in report['ranges'].values())
                          and not any(report['Falcon'][k] for k in ['lost_STOP', 'added_STOP', 'lost_payloads', 'changed_non_timing_rows']))
    else:
        a = read(ROOT / 'docs/evidence/h1_axis_range_2026-10-19/x3-d2-candidate.json')
        b = read(HERE / 'x3-e-candidate.json')
        for obj in [a, b]:
            old.rb.validated_entries(obj, Path('/tmp/opencode/resense-b4-data/decoded'), ROOT)
        report['cases'] = {key: old.compare(old.rows(Path(a['entries'][key]['raw_path'])),
            old.rows(Path(b['entries'][key]['raw_path'])), 'i', 'dets') for key in a['entries']}
        report['PASS'] = b['status'] == 'PASS' and all(not any(v[k] for k in
            ['lost_STOP', 'added_STOP', 'lost_payloads', 'changed_non_timing_rows']) for v in report['cases'].values())
    with (HERE / f'audit-e-{phase}.json').open('x') as stream:
        json.dump(report, stream, indent=2)
    print(phase, report['PASS'], flush=True)
    if 'ranges' in report:
        print({name: (r['previous']['stop_frames'], r['candidate']['stop_frames'], r['lost'], r['new_unmatched'])
               for name, r in report['ranges'].items()}, flush=True)
    return int(not report['PASS'])


if __name__ == '__main__':
    sys.exit(main())
