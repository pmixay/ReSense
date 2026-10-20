"""Independent raw-row recount; does not use the evaluator's held90 function."""
from collections import Counter
from copy import deepcopy
import hashlib
from itertools import accumulate, groupby
import json
from pathlib import Path
import statistics

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/r3-sustained')


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sustained(rows):
    hits = total = 0
    accepted = []
    for distance, group in groupby(sorted((r for r in rows if r['n'] > 0), key=lambda r: r['d']),
                                    key=lambda r: r['d']):
        group = list(group)
        total += len(group)
        hits += sum(bool(r['hit']) for r in group)
        if total >= 5 and 10 * hits >= 9 * total:
            accepted.append(distance)
    return max(accepted, default=None)


def key(sequence):
    return sequence['kind'], sequence['file0']


def index(report):
    result = {key(s): s for s in report['sequences']}
    assert len(result) == len(report['sequences']) == 30
    return result


def compare(before, after):
    b, a = index(before), index(after)
    assert b.keys() == a.keys()
    result = []
    for identity, old in b.items():
        new = a[identity]
        assert {k: v for k, v in old.items() if k not in ('rows', 'first', 'fp')} == {
            k: v for k, v in new.items() if k not in ('rows', 'first', 'fp')}
        assert [{k: r[k] for k in ('frame', 'd', 'path_d', 'gt', 'gt_vehicle_y_m', 'n')} for r in old['rows']] == [
            {k: r[k] for k in ('frame', 'd', 'path_d', 'gt', 'gt_vehicle_y_m', 'n')} for r in new['rows']]
        old_hits, new_hits = [{r['frame'] for r in s['rows'] if r['hit']} for s in (old, new)]
        result.append(dict(kind=identity[0], file0=identity[1], frames=len(old['rows']),
            visible=sum(r['n'] > 0 for r in old['rows']), old_hits=len(old_hits), new_hits=len(new_hits),
            lost=sorted(old_hits - new_hits), added=sorted(new_hits - old_hits),
            old_first=old['first'], new_first=new['first'],
            old_sustained=sustained(old['rows']), new_sustained=sustained(new['rows']),
            old_fp=sum(len(r['fp_dets']) for r in old['rows']), new_fp=sum(len(r['fp_dets']) for r in new['rows'])))
    return result


def main():
    off, on = (read(WORK / f'{side}.json') for side in ('off', 'on'))
    for side in ('off', 'on'):
        receipt = read(HERE / f'{side}-execution.json')
        assert receipt['returncode'] == 0 and receipt['source_unchanged']
        assert receipt['raw_sha256'] == sha(WORK / f'{side}.json')
        assert receipt['log_sha256'] == sha(WORK / f'{side}.log')
        for path, digest in receipt['source_sha256'].items():
            assert sha(ROOT / path) == digest, path
    compared = compare(off, on)
    assert sum(row['frames'] for row in compared) == 3060
    assert not any(row['lost'] or row['new_fp'] > row['old_fp'] for row in compared)
    assert all(row['old_sustained'] is None or (row['new_sustained'] is not None
               and row['new_sustained'] >= row['old_sustained']) for row in compared)
    for report in (off, on):
        for kind, summary in report['summary']['per_kind'].items():
            values = [sustained(s['rows']) for s in report['sequences'] if s['kind'] == kind]
            valid = [v for v in values if v is not None]
            median = round(statistics.median(valid), 1) if valid else None
            assert summary['sustained_median'] == median
            assert summary['sustained_m'] == sorted(valid)
    cable = [r for r in compared if r['kind'] == 'cable']
    historical = read(ROOT / 'docs/evidence/r3_h1_2026-10-19/final-raw-audit.json')['set_F_cable_sustained_population']
    assert [(r['file0'], r['old_sustained'], r['new_sustained'], r['old_hits'], r['new_hits']) for r in cable] == [
        (r['file'], r['baseline_sustained'], r['candidate_sustained'], r['baseline_hit_rows'], r['candidate_hit_rows'])
        for r in historical]
    original = [r for r in cable if r['old_sustained'] is not None]
    assert len(original) == 2
    paired = [statistics.median([r[f'{side}_sustained'] for r in original]) for side in ('old', 'new')]
    assert paired == [34.25, 34.25]
    planted = deepcopy(on)
    sequence = next(s for s in planted['sequences'] if s['kind'] == 'cable' and '140_' in s['file0'])
    for row in sequence['rows']:
        row['hit'] = False
    positive = compare(off, planted)
    assert any(r['lost'] and r['old_sustained'] is not None and r['new_sustained'] is None for r in positive)
    missing = deepcopy(on)
    missing['sequences'].pop()
    try:
        compare(off, missing)
    except AssertionError:
        pass
    else:
        raise AssertionError('missing sequence was not detected')
    shifted = deepcopy(on)
    shifted['sequences'][0]['rows'][0]['d'] += 1
    try:
        compare(off, shifted)
    except AssertionError:
        pass
    else:
        raise AssertionError('changed placement was not detected')
    examples = []
    bo, ao = index(off), index(on)
    for row in cable:
        identity = ('cable', row['file0'])
        old_rows = {r['frame']: r for r in bo[identity]['rows']}
        for r in ao[identity]['rows']:
            if r['frame'] in row['added']:
                examples.append(dict(file=row['file0'], frame=r['frame'], distance=r['d'],
                    object_returns=r['n'], before_hit=old_rows[r['frame']]['hit'], after_hit=r['hit']))
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), sharex=True, sharey=True)
    for ax, row in zip(axes.flat, cable, strict=True):
        identity = ('cable', row['file0'])
        for data, label in [(bo, 'R3 off'), (ao, 'R3 on')]:
            visible = sorted((r for r in data[identity]['rows'] if r['n'] > 0), key=lambda r: r['d'])
            distances = [r['d'] for r in visible]
            hits = list(accumulate(int(r['hit']) for r in visible))
            ax.plot(distances, [h / n for n, h in enumerate(hits, 1)], label=label)
        ax.axhline(.9, color='grey', linestyle='--')
        ax.set(title=row['file0'].split('_')[2], xlabel='distance threshold [m]', ylabel='visible-tail recall', xlim=(0, 220))
        ax.legend()
    fig.tight_layout()
    fig.savefig(HERE / 'cable-tail-recall.png', dpi=130)
    report = dict(status='R3_DETECTOR_REGRESSION_NOT_REPRODUCED_POPULATION_EFFECT_CONFIRMED',
        sequences=compared, cable=cable, frames_per_side=3060,
        old_conditional_median_m=off['summary']['per_kind']['cable']['sustained_median'],
        new_conditional_median_m=on['summary']['per_kind']['cable']['sustained_median'],
        fixed_baseline_success_cohort_median_unrounded_m=paired,
        old_sustained_sequences=2, new_sustained_sequences=4,
        lost_hit_rows=sum(len(r['lost']) for r in compared),
        added_hit_rows_by_kind=dict(Counter({kind: sum(len(r['added']) for r in compared if r['kind'] == kind)
                                            for kind in on['summary']['per_kind']})),
        false_detection_increase=0, added_cable_examples=examples,
        controls=dict(planted_hit_and_sustained_loss_detected=True,
                      missing_sequence_rejected=True, changed_placement_rejected=True),
        limitations='Synthetic positives on legacy detector-axis placement; held90 is pooled, not a continuous STOP guarantee.')
    with (HERE / 'audit.json').open('x') as out:
        json.dump(report, out, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k != 'sequences'}, indent=2))


if __name__ == '__main__':
    main()
