"""Compare retained raw rows against C, exercising loss/addition detectors."""
from collections import Counter
from copy import deepcopy
import argparse
import json
from pathlib import Path
import re
import runpy
import sys

from run_checks import ROOT, HERE, WORK, archived

sys.path.insert(0, str(ROOT / 'scripts'))
import regression_gate as gate  # noqa: E402
import robustness_battery as rb  # noqa: E402

OLD = ROOT / 'docs/evidence/h1_core_2026-10-19'
OLD_WORK = Path('/tmp/opencode/h1-core')
normalize = runpy.run_path(str(ROOT / 'docs/evidence/integration_2026-10-16/h3_selected/helpers/frame_diff.py'))['normalize']


def read(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def compare(left, right, key, payload):
    lost, changed = [], []
    old_stops, new_stops = set(), set()
    for a, b in zip(left, right, strict=True):
        assert a[key] == b[key]
        if a.get('obstacle', a.get('decision') == 'STOP'):
            old_stops.add(a[key])
        if b.get('obstacle', b.get('decision') == 'STOP'):
            new_stops.add(b[key])
        ca, cb = (Counter(json.dumps(d, sort_keys=True) for d in x[payload]) for x in [a, b])
        if ca - cb:
            lost.append(dict(frame=a[key], payloads=list((ca - cb).elements())))
        na, nb = (normalize(x)[0] if key == 'stamp' else node_normalize(x) for x in [a, b])
        if na != nb:
            changed.append(a[key])
    return dict(frames=len(left), previous_STOP=len(old_stops), candidate_STOP=len(new_stops),
                lost_STOP=sorted(old_stops - new_stops), added_STOP=sorted(new_stops - old_stops),
                lost_payloads=lost, changed_non_timing_rows=changed)


def node_normalize(row):
    result = deepcopy(row)
    for key in ['decode_ms', 'detect_ms', 'total_ms']:
        result.pop(key, None)
    msgs = result.get('msgs', [])
    result['msgs'] = [m for m in msgs if not re.fullmatch(r'latency p95 \d+ ms over the \d+ ms budget', m)]
    if msgs != result['msgs'] and result['level'] == 'warn' and result['dlevel'] == 'ok' and not result['msgs']:
        result['level'] = 'ok'
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--revision', default='d')
    parser.add_argument('--phase', choices=['gate', 'probes', 'x3'], required=True)
    args = parser.parse_args()
    name = args.revision
    report = dict(revision=name, phase=args.phase)
    if args.phase == 'gate':
        receipt = read(HERE / f'gate-{name}-candidate-execution.json')
        assert receipt['source_unchanged'] and receipt['source_sha256'] == archived.sources(ROOT)
        base, cur = OLD_WORK / 'gate-c-candidate-work', WORK / f'gate-{name}-candidate-work'
        assert {p.name for p in base.glob('*.jsonl')} == {p.name for p in cur.glob('*.jsonl')}
        report['bags'] = {}
        for path in sorted(base.glob('*.jsonl')):
            delta = compare(rows(path), rows(cur / path.name), 'stamp', 'detections')
            report['bags'][path.stem] = delta
        a, b = (read(p / 'setF_straight.json')['sequences'] for p in [base, cur])
        report['Set_F'] = dict(rows=sum(len(s['rows']) for s in a), identical=a == b)
        report['metrics'] = gate.compare(read(OLD / 'gate-c-candidate.json'), read(HERE / f'gate-{name}-candidate.json'), [])
        report['metric_verdicts'] = dict(Counter(x['verdict'] for x in report['metrics'] if not x['metric'].startswith('latency_ms.')))
        report['PASS'] = (all(not d['lost_STOP'] and not d['added_STOP'] and not d['lost_payloads']
                             and not d['changed_non_timing_rows'] for d in report['bags'].values()) and a == b
                          and all(not x['fails'] and not x['allowed'] for x in report['metrics']))
        # Known positive and planted differences test the exact same comparator.
        known = rows(base / 'doubleT_obstacle.jsonl')
        index = next(i for i, row in enumerate(known) if row['detections'])
        planted = deepcopy(known)
        planted[index]['detections'], planted[index]['obstacle'] = [], False
        control = compare(known, planted, 'stamp', 'detections')
        assert control['lost_STOP'] == [known[index]['stamp']] and len(control['lost_payloads']) == 1
        empty = rows(base / 'roundT_doubleT.jsonl')
        planted = deepcopy(empty)
        target = next(i for i, row in enumerate(empty) if not row['obstacle'])
        planted[target]['obstacle'], planted[target]['detections'] = True, deepcopy(known[index]['detections'])
        assert compare(empty, planted, 'stamp', 'detections')['added_STOP'] == [empty[target]['stamp']]
        changed = deepcopy(known[index])
        changed['track']['center'] += .01
        assert normalize(changed)[0] != normalize(known[index])[0]
        report['controls'] = dict(deleted_STOP_detected=True, added_STOP_detected=True, changed_axis_detected=True)
    elif args.phase == 'probes':
        report['ranges'] = {}
        for label in ['A-axis', 'C-person', 'E6']:
            before = read(OLD_WORK / 'supplement-c' / f'candidate-{label}.json')
            after = read(WORK / f'probes-{name}-candidate' / f'{label}.json')
            assert [(r['k'], r['X'], r['n_obj']) for r in before['rows']] == [(r['k'], r['X'], r['n_obj']) for r in after['rows']]
            # Full independent detection/assignment checks are in trace_ranges.py.
            old, new = ({r['k'] for r in obj['rows'] if r['X'] is not None and r['X'] > 3 and r['n_obj'] > 0 and r['hit']}
                        for obj in [before, after])
            report['ranges'][label] = dict(previous=before['summary'], candidate=after['summary'],
                lost_matches=sorted(old - new), added_matches=sorted(new - old),
                added_unmatched=[r for a, r in zip(before['rows'], after['rows'], strict=True)
                                 if r['decision'] == 'STOP' and not r['hit'] and a['decision'] != 'STOP'])
        a = rows(OLD_WORK / 'supplement-c/candidate-Falcon.jsonl')
        b = rows(WORK / f'probes-{name}-candidate/Falcon.jsonl')
        report['Falcon'] = compare(a, b, 'i', 'dets')
        report['PASS'] = (all(not r['lost_matches'] and not r['added_unmatched'] for r in report['ranges'].values())
                          and not any(report['Falcon'][k] for k in ['lost_STOP', 'added_STOP', 'lost_payloads', 'changed_non_timing_rows']))
    else:
        before, after = read(OLD / 'x3-c-candidate.json'), read(HERE / f'x3-{name}-candidate.json')
        for obj in [before, after]:
            rb.validated_entries(obj, Path('/tmp/opencode/resense-b4-data/decoded'), ROOT)
        assert before['sources'] == after['sources']
        report['cases'] = {}
        for key in before['entries']:
            a, b = (rows(Path(obj['entries'][key]['raw_path'])) for obj in [before, after])
            report['cases'][key] = compare(a, b, 'i', 'dets')
        report['PASS'] = after['status'] == 'PASS' and all(not any(d[k] for k in
            ['lost_STOP', 'added_STOP', 'lost_payloads', 'changed_non_timing_rows']) for d in report['cases'].values())
    with (HERE / f'audit-{name}-{args.phase}.json').open('x') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k not in ['metrics', 'bags', 'cases']}, indent=2))
    if args.phase == 'gate':
        print('bags', {k: (v['frames'], len(v['added_STOP']), len(v['lost_STOP'])) for k, v in report['bags'].items()})
    return int(not report['PASS'])


if __name__ == '__main__':
    sys.exit(main())
