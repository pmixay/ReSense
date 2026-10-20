#!/usr/bin/env python3
"""Compare fixed Set F sequences without confusing success coverage with range.

The historical held90 median excludes unsuccessful sequences. Keep that metric,
but report its population, the baseline-success cohort and exact per-frame losses.
This diagnostic does not change the regression gate's acceptance thresholds.
"""
from __future__ import annotations

import argparse
import hashlib
from itertools import groupby
import json
from pathlib import Path
from statistics import median


def _median(values):
    return round(float(median(values)), 1) if values else None


def sequence_metrics(sequences):
    """Compact, identity-preserving summaries from the raw Set F worker output."""
    kinds, seen = {}, set()
    for sequence in sequences:
        identity = {k: sequence.get(k) for k in ('kind', 'file0', 'd0', 'lateral', 'refl',
                    'placement_mode', 'reference', 'perturbation', 'anchor_frame')}
        key = json.dumps(identity, sort_keys=True, separators=(',', ':'))
        if key in seen:
            raise ValueError(f'duplicate Set F sequence: {key}')
        seen.add(key)
        rows = sequence['rows']
        frame_ids = [r['frame'] for r in rows]
        if len(frame_ids) != len(set(frame_ids)):
            raise ValueError(f'duplicate frame in Set F sequence: {key}')
        placement = [{k: r[k] for k in ('frame', 'd', 'n', 'gt')} for r in rows]
        fingerprint = hashlib.sha256(json.dumps(placement, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        visible = [r for r in rows if r['n'] > 0]
        hits = count = 0
        sustained = None
        for distance, group in groupby(sorted(visible, key=lambda r: r['d']), key=lambda r: r['d']):
            group = list(group)
            hits += sum(bool(r['hit']) for r in group)
            count += len(group)
            if count >= 5 and 10 * hits >= 9 * count:
                sustained = distance
        kinds.setdefault(sequence['kind'], []).append(dict(
            identity=identity, placement_sha256=fingerprint, skipped=sequence.get('skipped'),
            frames=len(rows), visible_frames=len(visible),
            hit_frames=[r['frame'] for r in visible if r['hit']],
            first_m=sequence['first'], sustained_m=sustained,
            false_detections=sum(len(r['fp_dets']) for r in rows)))
    return kinds


def compare_cohorts(before, after):
    """Compare one kind's sequence summaries; insufficient identity is not a pass.

    Placement hashes identify the evaluated labels/visibility, not the background
    point-cloud bytes. Evidence runs must also retain source/cache hashes.
    """
    if before is None or after is None:
        return dict(status='not_comparable', reason='per-sequence evidence missing (legacy summary)')

    def index(entries):
        result = {json.dumps(e['identity'], sort_keys=True): e for e in entries}
        if len(result) != len(entries):
            raise ValueError('duplicate Set F sequence identity')
        return result

    old, new = index(before), index(after)
    if not old or old.keys() != new.keys():
        return dict(status='not_comparable', reason='sequence populations differ')
    if any(a.get('skipped') or b.get('skipped') or a['placement_sha256'] != b['placement_sha256']
           for a, b in ((old[k], new[k]) for k in old)):
        return dict(status='not_comparable', reason='skipped sequence or changed placement/visibility')
    pairs = []
    for key, a in old.items():
        b = new[key]
        lost = sorted(set(a['hit_frames']) - set(b['hit_frames']))
        added = sorted(set(b['hit_frames']) - set(a['hit_frames']))
        range_loss = any(a[field] is not None and (b[field] is None or b[field] < a[field])
                         for field in ('first_m', 'sustained_m'))
        pairs.append(dict(identity=a['identity'], baseline_sustained_m=a['sustained_m'],
            current_sustained_m=b['sustained_m'], lost_hit_frames=lost, added_hit_frames=added,
            first_range_regressed=a['first_m'] is not None and (b['first_m'] is None or b['first_m'] < a['first_m']),
            false_detections_added=b['false_detections'] - a['false_detections'],
            regressed=bool(lost or range_loss or b['false_detections'] > a['false_detections'])))
    baseline_success = [p for p in pairs if p['baseline_sustained_m'] is not None]
    new_success = [p for p in pairs if p['current_sustained_m'] is not None]
    lost_success = [p for p in baseline_success if p['current_sustained_m'] is None]
    conditional_before = _median([p['baseline_sustained_m'] for p in baseline_success])
    conditional_after = _median([p['current_sustained_m'] for p in new_success])
    regressed = sum(p['regressed'] for p in pairs)
    expanded = len(new_success) > len(baseline_success) and not lost_success
    status = ('sequence_regression' if regressed else
              'success_population_expanded' if expanded else 'no_sequence_regression')
    return dict(status=status, sequences=len(pairs),
        baseline_sustained_sequences=len(baseline_success), current_sustained_sequences=len(new_success),
        baseline_conditional_median_m=conditional_before, current_conditional_median_m=conditional_after,
        baseline_success_cohort_baseline_median_m=conditional_before,
        # Never discard a lost success when computing the fixed-cohort comparison.
        baseline_success_cohort_current_median_m=None if lost_success else
            _median([p['current_sustained_m'] for p in baseline_success]),
        lost_sustained_sequences=len(lost_success), regressed_sequences=regressed,
        lost_hit_frames=sum(len(p['lost_hit_frames']) for p in pairs),
        added_hit_frames=sum(len(p['added_hit_frames']) for p in pairs), pairs=pairs)


def comparison_lines(comparisons):
    lines = []
    for kind, report in comparisons.items():
        if report['status'] == 'not_comparable':
            lines.append(f"set F {kind}: paired sustained comparison unavailable: {report['reason']}")
            continue
        lines.append(f"set F {kind}: conditional held90 median {report['baseline_conditional_median_m']} -> "
            f"{report['current_conditional_median_m']} m, successful sequences "
            f"{report['baseline_sustained_sequences']} -> {report['current_sustained_sequences']}/{report['sequences']}; "
            f"baseline-success cohort {report['baseline_success_cohort_baseline_median_m']} -> "
            f"{report['baseline_success_cohort_current_median_m']} m; "
            f"lost hits {report['lost_hit_frames']}, regressed sequences {report['regressed_sequences']} "
            f"[{report['status']}]")
    return lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('current', type=Path)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        before, after = [sequence_metrics(json.loads(p.read_text())['sequences'])
                         for p in (args.baseline, args.current)]
        report = {k: compare_cohorts(before.get(k), after.get(k)) for k in sorted(before.keys() | after.keys())}
    except (KeyError, ValueError) as exc:
        parser.error(str(exc))
    with args.out.open('x') as out:
        json.dump(report, out, indent=2)
    print('\n'.join(comparison_lines(report)))
    return 2 if any(r['status'] == 'not_comparable' for r in report.values()) else int(
        any(r['status'] == 'sequence_regression' for r in report.values()))


if __name__ == '__main__':
    raise SystemExit(main())
