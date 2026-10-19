#!/usr/bin/env python3
"""Compare the paired B4 replays; fail on incomplete data or unmet acceptance.

  python summarize_b4.py --runs <directory with b4-{baseline,candidate}-{empty,positive}.json>
                         --labels labels/doubleT_obstacle.json --out <summary.json>
"""
import argparse
import hashlib
import json
from pathlib import Path


def matched_frames(rows, labels):
    """Jury score_objects.py tolerances, only visible in-gauge labelled rows."""
    hits = {}
    for r in rows:
        for o in labels.get(f"{r['i']:05d}", []):
            if not o.get('in_gauge') or o.get('n_points', 1) == 0:
                continue
            name = o.get('label', o.get('name'))
            length, width = o.get('size', [0.5, 0.5])[:2]
            y = 0.5 * (o['bbox'][0][1] + o['bbox'][1][1]) if 'bbox' in o else o['lateral']
            if any(abs(d['d'] - o['distance']) <= max(2, 0.03 * o['distance']) + length / 2 and
                   abs(d['c'][1] - y) <= 1 + width / 2 for d in r['dets']):
                hits.setdefault(name, []).append(r['i'])
    return hits


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs', type=Path, required=True)
    p.add_argument('--labels', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    labels = json.loads(a.labels.read_text())
    data, hashes = {}, {}
    for tag in ('baseline', 'candidate'):
        for bag in ('empty', 'positive'):
            path = a.runs / f'b4-{tag}-{bag}.json'
            data[tag, bag] = json.loads(path.read_text())
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    checks, cases = [], []

    def check(name, ok):
        checks.append({'check': name, 'pass': bool(ok)})

    for tag in ('baseline', 'candidate'):
        check(f'{tag}: identical source across both recordings',
              data[tag, 'empty']['source_sha256'] == data[tag, 'positive']['source_sha256'])
    for bag, n in (('empty', 545), ('positive', 201)):
        before, after = data['baseline', bag], data['candidate', bag]
        check(f'{bag}: identical cached inputs', before['input_sha256'] == after['input_sha256'])
        for tag in ('baseline', 'candidate'):
            source = data[tag, bag]
            check(f'{tag}/{bag}: 24 unique complete cases',
                  sorted(c['index'] for c in source['cases']) == list(range(24)) and
                  all([r['i'] for r in c['rows']] == list(range(n)) for c in source['cases']))
        check(f'{bag}: same runtime/environment', before['python'] == after['python'] and
              before['environment'] == after['environment'])
        baseline = {c['index']: c for c in before['cases']}
        plain_hits = matched_frames(baseline[0]['rows'], labels) if bag == 'positive' else {}
        for c in after['cases']:
            k = c['index']
            b = baseline[k]
            check(f'{bag}/{k}: correct by frame 1', c['first_correct_label'] is not None and c['first_correct_label'] <= 1)
            check(f'{bag}/{k}: no wrong accepted orientation', not c['wrong_accepted_frames'])
            check(f'{bag}/{k}: no GO before orientation confirmed',
                  all(r['decision'] != 'GO' for r in c['rows'] if not r['mapping_confirmed']))
            diff = [r['i'] for r, old in zip(c['rows'], b['rows']) if r['decision'] != old['decision']]
            lost_stop = [r['i'] for r, old in zip(c['rows'], b['rows'])
                         if old['decision'] == 'STOP' and r['decision'] != 'STOP']
            row = {'bag': bag, 'index': k, 'upright': c['up_vertical'],
                   'first_correct_label': c['first_correct_label'], 'baseline': b['decisions'],
                   'candidate': c['decisions'], 'decision_diff_frames': diff,
                   'first_stop_frame': next((r['i'] for r in c['rows'] if r['decision'] == 'STOP'), None),
                   'lost_stop_frames_vs_same_rotation': lost_stop}
            if bag == 'empty':
                check(f'{bag}/{k}: no false STOP', c['decisions']['STOP'] == 0)
            else:
                hits = matched_frames(c['rows'], labels)
                old_hits = matched_frames(b['rows'], labels)
                row['matched_frames'] = hits
                row['lost_matches_vs_plain'] = {name: sorted(set(v) - set(hits.get(name, [])))
                                                for name, v in plain_hits.items()}
                row['lost_matches_vs_same_rotation'] = {name: sorted(set(v) - set(hits.get(name, [])))
                                                        for name, v in old_hits.items()}
                if c['up_vertical']:
                    check(f'{bag}/{k}: retain all previously matched STOP frames',
                          not any(row['lost_matches_vs_same_rotation'].values()))
                else:
                    # A wrong-mount STOP is not a positive baseline. Corrected
                    # sideways cases are compared with the unrotated control.
                    check(f'{bag}/{k}: retain plain matched STOP frames',
                          not any(row['lost_matches_vs_plain'].values()))
            cases.append(row)
    result = {'pass': all(c['pass'] for c in checks), 'checks': checks, 'cases': cases,
              'raw_sha256': hashes, 'labels_sha256': hashlib.sha256(a.labels.read_bytes()).hexdigest()}
    a.out.write_text(json.dumps(result, indent=1))
    for r in cases:
        print(r['bag'], r['index'], r['first_correct_label'],
              r['baseline']['STOP'], '->', r['candidate']['STOP'],
              'first STOP', r['first_stop_frame'],
              'lost matches', r.get('lost_matches_vs_same_rotation', {}))
    failed = [c['check'] for c in checks if not c['pass']]
    print('PASS' if result['pass'] else 'FAIL', 'failed:', failed)
    raise SystemExit(0 if result['pass'] else 1)


if __name__ == '__main__':
    main()
