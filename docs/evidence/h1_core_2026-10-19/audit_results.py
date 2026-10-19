"""Independent row/payload audit, with planted nonzero controls."""
from collections import Counter
import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import runpy
import sys

from run_checks import DATA, HERE, ROOT, WORK, sources

sys.path.insert(0, str(ROOT / 'scripts'))
import regression_gate as gate  # noqa: E402
import robustness_battery as rb  # noqa: E402

fd = runpy.run_path(str(ROOT / 'docs/evidence/integration_2026-10-16/h3_selected/helpers/frame_diff.py'))
parser = argparse.ArgumentParser()
parser.add_argument('--revision', default='b')
args = parser.parse_args()
revision = args.revision
suffix = '' if revision == 'b' else '-' + revision


def read(p):
    return json.loads(p.read_text())


def rows(p):
    return [json.loads(x) for x in p.read_text().splitlines()]


def pair_delta(b, c, key, payload):
    bs = {r[key] for r in b if r.get('obstacle', r.get('decision') == 'STOP')}
    cs = {r[key] for r in c if r.get('obstacle', r.get('decision') == 'STOP')}
    lost = []
    for x, y in zip(b, c, strict=True):
        assert x[key] == y[key]
        bc = Counter(json.dumps(d, sort_keys=True) for d in x[payload])
        cc = Counter(json.dumps(d, sort_keys=True) for d in y[payload])
        if bc - cc:
            lost.append(dict(frame=x[key], payloads=list((bc - cc).elements())))
    return dict(frames=len(b), baseline_STOP=len(bs), candidate_STOP=len(cs),
                lost_STOP=sorted(bs - cs), added_STOP=sorted(cs - bs), lost_payloads=lost)


latency = re.compile(r'^latency p95 \d+ ms over the \d+ ms budget$')


def node_normalize(row):
    r = deepcopy(row)
    for key in ['decode_ms', 'detect_ms', 'total_ms']:
        r.pop(key, None)
    timing_msgs = [m for m in r.get('msgs', []) if latency.fullmatch(m)]
    if timing_msgs:
        r['msgs'] = [m for m in r['msgs'] if not latency.fullmatch(m)]
        if r['level'] == 'warn' and r['dlevel'] == 'ok' and not r['msgs']:
            r['level'] = 'ok'
    return r


result = dict(gate={}, X3={}, probes={}, physical={}, positive_controls={})
before = read(HERE / f'gate-{revision}-candidate-execution.json')
assert before['source_sha256'] == sources(ROOT) and before['source_unchanged']
result['measured_snapshot_equal_current_committed_source'] = True
result['current_source'] = rb.git(ROOT, 'rev-parse', 'HEAD')
base, cur = (WORK / f'gate-{name}-work' for name in ['a-reference', f'{revision}-candidate'])
assert {p.name for p in base.glob('*.jsonl')} == {p.name for p in cur.glob('*.jsonl')}
for path in sorted(base.glob('*.jsonl')):
    b, c = rows(path), rows(cur / path.name)
    delta = pair_delta(b, c, 'stamp', 'detections')
    delta['changed_non_timing_rows'] = [i for i, (x, y) in enumerate(zip(b, c, strict=True))
                                        if fd['normalize'](x)[0] != fd['normalize'](y)[0]]
    result['gate'][path.stem] = delta
    assert not delta['lost_STOP'] and not delta['lost_payloads']
    assert not delta['added_STOP']
    assert not delta['changed_non_timing_rows'], (path, delta['changed_non_timing_rows'][:10])
sf_b, sf_c = (read(p / 'setF_straight.json')['sequences'] for p in [base, cur])
assert sf_b == sf_c
result['Set_F'] = dict(sequences=len(sf_b), rows=sum(len(s['rows']) for s in sf_b), identical=True)
comparison = gate.compare(read(HERE / 'gate-a-reference.json'), read(HERE / f'gate-{revision}-candidate.json'), [])
result['gate_non_timing_metrics'] = dict(Counter(r['verdict'] for r in comparison if not r['metric'].startswith('latency_ms.')))
assert all(not r['fails'] and not r['allowed'] for r in comparison)

b = read(HERE / 'x3-final-reference.json')
c = read(HERE / f'x3-{"final" if revision == "b" else revision}-candidate.json')
assert b['sources'] == c['sources'] and c['status'] == 'PASS'
for report in [b, c]:
    rb.validated_entries(report, DATA / 'decoded', ROOT)
for key in b['entries']:
    left, right = (rows(Path(r['entries'][key]['raw_path'])) for r in [b, c])
    delta = pair_delta(left, right, 'i', 'dets')
    delta['changed_non_timing_rows'] = [x['i'] for x, y in zip(left, right, strict=True)
                                       if node_normalize(x) != node_normalize(y)]
    result['X3'][key] = delta
    assert not delta['lost_STOP'] and not delta['lost_payloads']
    assert not delta['added_STOP'] and not delta['changed_non_timing_rows'], (key, delta)

for name in ['A-axis', 'C-person', 'E6']:
    b = read(WORK / 'supplement' / f'reference-{name}.json')
    c = read(WORK / f'supplement{suffix}' / f'candidate-{name}.json')
    assert [(r['k'], r['X'], r['n_obj']) for r in b['rows']] == [(r['k'], r['X'], r['n_obj']) for r in c['rows']]
    def hits(r):
        return {x['k'] for x in r['rows'] if x['X'] is not None and x['X'] > 3 and x['n_obj'] > 0 and x['hit']}
    old, new = hits(b), hits(c)
    assert len(old) == b['summary']['stop_frames'] and len(new) == c['summary']['stop_frames']
    assert not old - new
    extra = [r['k'] for r in c['rows'] if r['decision'] == 'STOP' and not r['hit']
             and b['rows'][r['k']]['decision'] != 'STOP']
    # Preserve unmatched decisions, including an existing miss-hold below range_min.
    # Attribution is established separately from full tracker state, not inferred here.
    assert all(c['rows'][i]['X'] is not None and 0 < c['rows'][i]['X'] < 3
               and c['rows'][i]['n_obj'] == 0 for i in extra), (name, extra)
    result['probes'][name] = dict(baseline=b['summary'], candidate=c['summary'],
                                 added_matches=sorted(new - old), lost_matches=sorted(old - new),
                                 added_unmatched_decisions=[c['rows'][i] for i in extra])
left = rows(WORK / 'supplement' / 'reference-Falcon.jsonl')
right = rows(WORK / f'supplement{suffix}' / 'candidate-Falcon.jsonl')
delta = pair_delta(left, right, 'i', 'dets')
delta['changed_non_timing_rows'] = [x['i'] for x, y in zip(left, right, strict=True)
                                   if node_normalize(x) != node_normalize(y)]
result['probes']['Falcon'] = delta
assert len(left) == 4443
assert not delta['lost_STOP'] and not delta['added_STOP'] and not delta['lost_payloads']
assert not delta['changed_non_timing_rows']

physical = read(HERE / f'physical-sweep{suffix}.json')
preserved = added = 0
misses = []
for case in physical['full']:
    for side in ['off', 'on']:
        for r in case[side]:
            actual = any(abs(d['distance'] - case['distance']) < 1 and abs(d['center'][1] - case['lateral']) < .5
                         for d in r['dets'])
            assert actual == r['hit']
    old = {r['i'] for r in case['off'] if r['hit']}
    new = {r['i'] for r in case['on'] if r['hit']}
    assert not old - new
    preserved += len(old)
    added += len(new - old)
    if not new:
        misses.append({k: case[k] for k in ['distance', 'lateral', 'top', 'absorbing']})
outside = [r for r in physical['outside'] if abs(r['error']) <= .3]
assert len(outside) == 48 and not any(r['core'] or r['matched_stop'] for r in outside)
result['physical'] = dict(full_cases=len(physical['full']), full_rows=sum(len(c[s]) for c in physical['full'] for s in ['off', 'on']),
                          preserved_matches=preserved, added_matches=added, remaining_missed_cases=misses,
                          outside_budget_cases=len(outside), larger_error_results=[r for r in physical['outside'] if abs(r['error']) > .3])

# Independently exercise negative-result comparators on known positive data.
known = rows(base / 'doubleT_obstacle.jsonl')
planted = deepcopy(known)
index = next(i for i, r in enumerate(planted) if r['detections'])
planted[index]['detections'] = []
planted[index]['obstacle'] = False
detected = pair_delta(known, planted, 'stamp', 'detections')
assert detected['lost_STOP'] == [known[index]['stamp']] and len(detected['lost_payloads']) == 1
empty = rows(base / 'roundT_doubleT.jsonl')
planted = deepcopy(empty)
planted[10]['obstacle'] = True
planted[10]['detections'] = deepcopy(known[index]['detections'])
detected = pair_delta(empty, planted, 'stamp', 'detections')
assert detected['added_STOP'] == [empty[10]['stamp']]
changed = deepcopy(known[index])
changed['track']['center'] += .01
assert fd['normalize'](known[index])[0] != fd['normalize'](changed)[0]
result['positive_controls'] = dict(deleted_positive_STOP_and_payload_detected=True,
                                   added_empty_STOP_detected=True, changed_axis_field_detected=True)
(HERE / f'raw-audit{suffix}.json').write_text(json.dumps(result, indent=2) + '\n')
print('Gate ordinary', sum(d['frames'] for d in result['gate'].values()), 'Set F', result['Set_F']['rows'],
      'X3', sum(d['frames'] for d in result['X3'].values()), 'Falcon', delta['frames'])
print('Physical preserved/added', preserved, added, 'remaining misses', misses)
print('Range summaries', {n: (r['baseline']['stop_frames'], r['candidate']['stop_frames'])
                          for n, r in result['probes'].items() if 'baseline' in r})
