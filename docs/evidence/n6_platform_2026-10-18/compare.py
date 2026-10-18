#!/usr/bin/env python3
"""Compare complete paired N6 replays with unchanged frozen N5 annotation semantics."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.score_team_labels import score  # noqa: E402


def load(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('baseline', type=Path)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--labels', type=Path)
    args = parser.parse_args()
    baseline, candidate = load(args.baseline), load(args.candidate)
    if [row['i'] for row in baseline] != list(range(len(baseline))) or [row['i'] for row in candidate] != list(range(len(baseline))):
        raise ValueError('recordings must contain the same complete consecutive frames')
    before = {row['i'] for row in baseline if row['obstacle']}
    after = {row['i'] for row in candidate if row['obstacle']}
    shape = ('center', 'yaw', 'curvature', 'floor_coef', 'floor_range', 'rail_offset')
    report = {'frames': len(baseline), 'baseline_sha256': hashlib.sha256(args.baseline.read_bytes()).hexdigest(),
              'candidate_sha256': hashlib.sha256(args.candidate.read_bytes()).hexdigest(),
              'comparison_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'stop_frames': [len(before), len(after)], 'new_stop_frames': sorted(after - before),
              'lost_stop_frames': sorted(before - after),
              'changed_detection_counts': [
                  {'frame': a['i'], 'baseline': len(a['dets']), 'candidate': len(b['dets'])}
                  for a, b in zip(baseline, candidate) if len(a['dets']) != len(b['dets'])],
              'changed_detection_geometry_frames': [
                  a['i'] for a, b in zip(baseline, candidate)
                  if [[d.get(k) for k in ('d', 'c', 'size', 'kind')] for d in a['dets']]
                  != [[d.get(k) for k in ('d', 'c', 'size', 'kind')] for d in b['dets']]],
              'changed_warning_frames': [
                  a['i'] for a, b in zip(baseline, candidate) if a['warns'] != b['warns']],
              'decision_changes': [
                  {'frame': a['i'], 'baseline': {k: a.get(k) for k in ('decision', 'dlevel')},
                   'candidate': {k: b.get(k) for k in ('decision', 'dlevel')}}
                  for a, b in zip(baseline, candidate)
                  if any(a.get(k) != b.get(k) for k in ('decision', 'dlevel'))],
              'health_level_change_frames': [
                  a['i'] for a, b in zip(baseline, candidate) if a['level'] != b['level']],
              'non_latency_health_message_change_frames': [
                  a['i'] for a, b in zip(baseline, candidate)
                  if [m for m in a['msgs'] if not m.startswith('latency p95 ')]
                  != [m for m in b['msgs'] if not m.startswith('latency p95 ')]],
              'latency_warning_frame_counts': [
                  sum(any(m.startswith('latency p95 ') for m in row['msgs']) for row in rows)
                  for rows in (baseline, candidate)],
              'range_changes': [
                  {'frame': a['i'], 'clear': [a['clear'], b['clear']],
                   'monitored': [a['monitored'], b['monitored']],
                   'axis_valid': [a.get('model', {}).get('axis_valid'), b.get('model', {}).get('axis_valid')]}
                  for a, b in zip(baseline, candidate)
                  if a['clear'] != b['clear'] or a['monitored'] != b['monitored']],
              'shape_changed_frames': [a['i'] for a, b in zip(baseline, candidate)
                                       if 'model' in a and any(a['model'][key] != b['model'][key] for key in shape)],
              'extended_axis_frames': [a['i'] for a, b in zip(baseline, candidate)
                                       if 'model' in a and b['model']['axis_valid'] > a['model']['axis_valid']]}
    if args.labels:
        labels = json.loads(args.labels.read_text())
        reports = [score(rows, labels) for rows in (baseline, candidate)]
        report['label_sha256'] = hashlib.sha256(args.labels.read_bytes()).hexdigest()
        report['score_summary'] = {'baseline': reports[0]['summary'], 'candidate': reports[1]['summary']}
        unmatched_before = {row['frame']: row['unmatched'] for row in reports[0]['stop_frames']}
        report['new_unmatched_stop_frames'] = [
            row['frame'] for row in reports[1]['stop_frames']
            if row['unmatched'] > unmatched_before.get(row['frame'], 0)]
        report['objects'] = {}
        for name in reports[0]['objects']:
            a, b = (r['objects'][name] for r in reports)
            sa = {row['frame'] for row in a['observations'] if row['stop_match'][0]}
            sb = {row['frame'] for row in b['observations'] if row['stop_match'][0]}
            report['objects'][name] = {
                'first_stop_m': [a['first_stop_m_certain_assignment'], b['first_stop_m_certain_assignment']],
                'certain_stop_rows': [len(sa), len(sb)], 'new_stop_rows': sorted(sb - sa),
                'lost_stop_rows': sorted(sa - sb),
                'new_outside_stop_rows': [r['frame'] for r in b['observations']
                                          if r['gauge_relation'] == 'outside' and r['stop_match'][0] and r['frame'] not in sa]}
        for version, result in zip(('baseline', 'candidate'), reports):
            args.out.with_name(args.out.stem + '_' + version + '_score.json').write_text(json.dumps(result, indent=2) + '\n')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
