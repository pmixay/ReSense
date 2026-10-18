#!/usr/bin/env python3
"""Compare every legacy-label match in complete paired node-replica captures.

Uses the repository's unchanged distance/lateral assignment rule. The captures
contain rounded geometry but no persistent IDs, so event/track counts cannot be
reconstructed and are deliberately not reported as zero.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from resense.metrics import GTObstacle, _assign_detections  # noqa: E402
from scripts.score_fake_objects import score  # noqa: E402


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_capture(path):
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if [row['i'] for row in rows] != list(range(len(rows))):
        raise ValueError('capture must contain consecutive complete frames')
    return [{'frame': row['i'], 'obstacle': row['obstacle'],
             'detections': [{'distance': d['d'], 'lateral': d['lat']} for d in row['dets']],
             'warnings': [{'distance': d['d'], 'lateral': d['lat']} for d in row['warns']]}
            for row in rows]


def match_rows(results, labels):
    hits, unmatched = {}, {}
    for result in results:
        frame = result['frame']
        objects = [row for row in labels.get(f'{frame:05d}', []) if row.get('n_points', 1) > 0]
        assigned = _assign_detections(result['detections'], [GTObstacle.from_dict(row) for row in objects])
        unmatched[frame] = len(result['detections']) - len(assigned)
        for gi, obj in enumerate(objects):
            if not obj.get('plausible', True):
                continue
            rows = hits.setdefault(obj['label'], {})
            rows[frame] = {'matched': gi in assigned, 'distance': obj['distance'],
                           'in_gauge': obj['in_gauge']}
    return hits, unmatched


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('labels', type=Path)
    parser.add_argument('out', type=Path)
    args = parser.parse_args()
    baseline, candidate = [read_capture(path) for path in (args.baseline, args.candidate)]
    labels = json.loads(args.labels.read_text())
    if len(baseline) != len(candidate) or len(baseline) != len([k for k in labels if not k.startswith('_')]):
        raise ValueError('label and capture frame counts must agree')
    pairs = [match_rows(rows, labels) for rows in (baseline, candidate)]
    report = {'frames': len(baseline), 'objects': {},
              'input_sha256': {str(path): digest(path) for path in (args.baseline, args.candidate, args.labels)},
              'code_sha256': {str(path.relative_to(ROOT)): digest(path) for path in
                              (Path(__file__), ROOT / 'resense/metrics.py', ROOT / 'scripts/score_fake_objects.py')},
              'event_counts': None, 'event_count_reason': 'capture contains no persistent detection IDs',
              'legacy_aggregate_limit': 'The baseline/candidate legacy scorer collapses each object to one gauge value. Its aggregate verdict is not authoritative for an object whose gauge relation changes over time; use the per-frame relation breakdown in top-level objects.',
              'new_unmatched_stop_frames': [i for i in range(len(baseline)) if pairs[1][1][i] > pairs[0][1][i]]}
    for label in pairs[0][0]:
        a, b = [pair[0][label] for pair in pairs]
        before = {i for i, row in a.items() if row['matched']}
        after = {i for i, row in b.items() if row['matched']}
        report['objects'][label] = {'matched_stop_rows': [len(before), len(after)],
                                    'first_stop_m': [rows[min(hits)]['distance'] if hits else None
                                                     for rows, hits in ((a, before), (b, after))],
                                    'maximum_matched_distance_m': [max((rows[i]['distance'] for i in hits), default=None)
                                                                   for rows, hits in ((a, before), (b, after))],
                                    'lost_stop_rows': sorted(before - after),
                                    'new_stop_rows': sorted(after - before),
                                    'new_outside_stop_rows': sorted(i for i in after - before if b[i]['in_gauge'] is False)}
        item = report['objects'][label]
        item['first_stop_frame'] = [min(hits) if hits else None for hits in (before, after)]
        for relation, value in (('inside', True), ('outside', False), ('unknown', None)):
            first = {i for i in before if a[i]['in_gauge'] is value}
            second = {i for i in after if b[i]['in_gauge'] is value}
            item[f'{relation}_matched_stop_rows'] = [len(first), len(second)]
            item[f'lost_{relation}_stop_rows'] = sorted(first - second)
            item[f'new_{relation}_stop_rows'] = sorted(second - first)
        item['gauge_relation_changes_by_frame'] = len({row['in_gauge'] for row in a.values()}) > 1
    for variant, rows in (('baseline', baseline), ('candidate', candidate)):
        objects, background = score(rows, labels)
        background.pop('background_alarm_ids')
        background['persistent_event_count'] = None
        report[variant] = {'objects': objects, 'background': background}
        for label, obj in objects.items():
            if report['objects'][label]['gauge_relation_changes_by_frame']:
                obj['aggregate_verdict_not_authoritative'] = True
    if args.labels.name == 'cloud_with_fake_obj.json':
        report['exact_source_interval'] = {'first_frame': 1308, 'last_frame': 1433,
                                          'baseline_stop_frames': [r['frame'] for r in baseline[1308:1434] if r['obstacle']],
                                          'candidate_stop_frames': [r['frame'] for r in candidate[1308:1434] if r['obstacle']]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'frames': report['frames'], 'objects': report['objects'],
                      'new_unmatched_stop_frames': report['new_unmatched_stop_frames']}))


if __name__ == '__main__':
    main()
