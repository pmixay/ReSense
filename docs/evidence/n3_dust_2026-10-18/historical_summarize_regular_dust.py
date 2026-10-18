#!/usr/bin/env python3
"""Complete-only verification of seven-bag baseline and separate dark-person experiment."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EMPTY = ('doubleT_platform', 'roundT_doubleT', 'roundT_pressureGate_roundT',
         'roundT_squareT_pressureGate_squareT', 'squareT_platform_squareT_switch')
BAGS = (*EMPTY, 'doubleT_obstacle', 'cloud_with_fake_obj')
LEVELS = ('clean', 'low', 'medium', 'high')
FRAME_COUNTS = dict(zip(BAGS, (345, 252, 268, 545, 877, 201, 1510)))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def episodes(frames):
    selected = set(frames)
    return sum(frame - 1 not in selected for frame in frames)


def write_baseline_review(report, directory):
    """Render only a successfully verified complete measurement, never partial rows."""
    lines = ['# Complete seven-recording dust baseline', '',
             f"All seven recordings completed all four levels: **{report['total_processed_frames']:,} processed frames**.",
             'Source Python hashes, raw gzip hashes, exact frame sequence/timestamps and decision counts',
             'were verified before this report. Every object association was independently reconstructed.',
             'The immutable detector is `9b92df5`; all densities use seed 20261018.', '',
             '| Empty recording | Level | STOP frames / episodes | CAUTION | GO | Degraded | Extra episodes | Acceptance |',
             '|---|---|---:|---:|---:|---:|---:|---|']
    for bag in EMPTY:
        for level, row in report['recordings'][bag]['levels'].items():
            counts = row['counts']
            extra = row.get('extra_stop_episodes')
            accepted = row.get('empty_episode_acceptance')
            status = 'reference' if accepted is None else 'PASS' if accepted else 'FAIL'
            lines.append(f"| {bag} | {level} | {counts.get('STOP', 0)} / {row['stop_episodes']} | {counts.get('CAUTION', 0)} | {counts.get('GO', 0)} | {len(row['degraded_frames'])} | {'—' if extra is None else extra} | {status} |")
    lines += ['', 'Each empty-bag level may add at most one STOP episode relative to its own clean recording.',
              'An episode is a consecutive run of STOP frames, never joined across recordings.', '',
              '| Positive recording | Level | STOP | CAUTION | GO | Degraded |',
              '|---|---|---:|---:|---:|---:|']
    for bag in BAGS[len(EMPTY):]:
        for level, row in report['recordings'][bag]['levels'].items():
            counts = row['counts']
            lines.append(f"| {bag} | {level} | {counts.get('STOP', 0)} | {counts.get('CAUTION', 0)} | {counts.get('GO', 0)} | {len(row['degraded_frames'])} |")
    crossing = report['recordings']['doubleT_obstacle']['levels']['low']['objects']['person_crossing']
    ratio = crossing['first_stop_ratio']
    person_status = 'FAIL' if ratio is None or ratio < .9 else 'PASS'
    lines += ['', f"Low-density crossing first-range criterion (at least 90% of clean): **{person_status}**, ratio **{ratio}**.",
              'Per-frame STOP retention is reported separately; a preserved first range does not imply preserved later detections.', '',
              '| Object | Level | Temporal first STOP m | Inside / outside / unknown matches | Lost clean inside / outside / unknown |',
              '|---|---|---:|---|---|']
    for bag in BAGS[len(EMPTY):]:
        for name in report['recordings'][bag]['levels']['clean']['objects']:
            for level, row in report['recordings'][bag]['levels'].items():
                obj = row['objects'][name]
                distance = 'none' if obj['first_stop_m'] is None else f"{obj['first_stop_m']:.2f}"
                matched = ' / '.join(str(len(obj[f'{rel}_matched_stop_frames'])) for rel in ('inside', 'outside', 'unknown'))
                lost = 'reference' if level == 'clean' else ' / '.join(str(len(obj[f'lost_clean_{rel}_stop_frames'])) for rel in ('inside', 'outside', 'unknown'))
                lines.append(f'| {bag}: {name} | {level} | {distance} | {matched} | {lost} |')
    lines += ['', 'Gauge relation comes from each individual label row, including the crossing person changing relation.',
              'Outside associations are never silently counted as inside positives. Every exact lost/new row,',
              'unmatched detection frame and first-range ratio remains in [verified_complete.json](verified_complete.json).', '',
              '| High-density recording | GO without degradation | Degraded / all frames |',
              '|---|---:|---:|']
    for bag, row in report['recordings'].items():
        high = row['levels']['high']
        lines.append(f"| {bag} | {len(high['silent_go_frames'])} | {len(high['degraded_frames'])} / {high['frames']} |")
    lines += ['', 'High density is required to be explicitly degraded rather than silently GO. The table preserves',
              'every failure; STOP under high density by itself is not proof that visibility health was recognized.',
              'Original reports did not capture native-library or configuration-file hashes during replay;',
              'the verifier records that limitation instead of supplying retrospective measurement provenance.',
              'These are fixed synthetic stresses, not calibrated physical dust. Timing shared a single-CPU',
              'host and includes recorded pauses, so it does not establish throughput.', '']
    (directory / 'RESULTS.md').write_text('\n'.join(lines))


def verify(directory, expected_bags, dark=False):
    summary_path = directory / 'summary.json'
    report = json.loads(summary_path.read_text())
    if set(report['recordings']) != set(expected_bags):
        raise ValueError(f'{directory.name}: missing or unexpected recordings')
    if report['seed'] != 20261018 or report['config_overrides']:
        raise ValueError('unexpected seed or configuration overrides')
    if dark:
        if report.get('dust_support') is not True or report.get('dim_label_intensity') != 1.:
            raise ValueError('expected separate suppression+intensity1 dark-person experiment')
    elif report.get('dust_support', False) or report.get('health_only', False) or report.get('dim_label_intensity') is not None:
        raise ValueError('expected unmodified original-intensity baseline')
    source = Path(report['detector_root'])
    for relative, recorded in report['source_hashes'].items():
        if digest(source / relative) != recorded:
            raise ValueError(f'immutable source drift: {relative}')
    if dark and digest(source / 'resense/dust_health.py') != report['support_sha256']:
        raise ValueError('dark experiment support implementation differs from frozen source')
    # The immutable core metrics assignment is shared by both experiments.
    sys.path.insert(0, str(source))
    from resense.metrics import _assign_detections, gt_objects
    output = {'complete': True, 'scope': 'dark_person_experiment' if dark else 'seven_recording_baseline',
              'summary_sha256': digest(summary_path), 'detector_root': str(source),
              'source_hashes': report['source_hashes'], 'generator_sha256': report['generator_sha256'],
              'support_sha256': report.get('support_sha256'), 'dim_label_intensity': report.get('dim_label_intensity'),
              'configuration_file_sha256_at_verification': digest(source / 'configs/default.yaml'),
              'recordings': {}, 'label_sha256': {},
              'limits': ['Original report captures source Python hashes but not native-library or YAML hashes; do not retroactively claim they were captured during replay.',
                         'Legacy labels/matching are retained; outside-object results are included, not silently counted as true positives.',
                         'Concurrent wall/latency timings are informational; this is not measured physical dust.']}
    for bag in expected_bags:
        recorded = report['recordings'][bag]
        if recorded['frames'] != FRAME_COUNTS[bag] or set(recorded['levels']) != set(LEVELS):
            raise ValueError(f'{bag}: all four complete levels are required')
        meta_path = Path('/home/resense/data/decoded') / bag / 'meta.json'
        meta = json.loads(meta_path.read_text())
        if len(meta) != FRAME_COUNTS[bag]:
            raise ValueError(f'{bag}: decoded frame count differs')
        label_path = ROOT / 'labels' / f'{bag}.json'
        labels = json.loads(label_path.read_text()) if label_path.exists() else {}
        if labels:
            output['label_sha256'][bag] = digest(label_path)
        bag_out = {'frames_per_level': FRAME_COUNTS[bag], 'cache_sha256_from_replay': recorded['cache_sha256'],
                   'metadata_sha256_at_verification': digest(meta_path), 'levels': {}}
        output['recordings'][bag] = bag_out
        for level in LEVELS:
            measurement = recorded['levels'][level]
            path = directory / f'{bag}_{level}.jsonl.gz'
            if digest(path) != measurement['raw_sha256']:
                raise ValueError(f'{bag}/{level}: compressed capture hash mismatch')
            counts, objects = Counter(), {}
            stop_frames, go_frames, degraded, unmatched_frames = [], [], [], []
            silent_go_frames, rows_read = [], 0
            with gzip.open(path, 'rt') as stream:
                for i, line in enumerate(stream):
                    row = json.loads(line)
                    if row['frame'] != i or row['stamp'] != meta[i]['stamp']:
                        raise ValueError(f'{bag}/{level}: nonconsecutive frame or wrong timestamp {i}')
                    rows_read += 1
                    health = row['health'] or {}
                    decision = ('STOP' if row['obstacle'] else 'FAULT' if health.get('level') == 'error'
                                else 'CAUTION' if row['warning'] or health.get('decision_level', health.get('level')) == 'warn'
                                else 'GO')
                    if decision != row['decision']:
                        raise ValueError(f'{bag}/{level}: decision disagreement at {i}')
                    counts[decision] += 1
                    is_degraded = health.get('decision_level', health.get('level')) in ('warn', 'error')
                    if decision == 'STOP':
                        stop_frames.append(i)
                    if decision == 'GO':
                        go_frames.append(i)
                        if not is_degraded:
                            silent_go_frames.append(i)
                    if is_degraded:
                        degraded.append(i)
                    audit = row['augmentation']
                    if level == 'clean':
                        if audit is not None:
                            raise ValueError('clean input unexpectedly augmented')
                    else:
                        if audit['seed'] != 20261018 or audit['frame_index'] != i:
                            raise ValueError('augmentation seed/frame mismatch')
                        expected = {'low': (.1, .0005), 'medium': (1., .003), 'high': (10., .02)}[level]
                        if (audit['spec']['density'], audit['spec']['extinction']) != expected:
                            raise ValueError('dust specification differs')
                    visible = [obj for obj in labels.get(f'{i:05d}', [])
                               if obj.get('n_points', 1) > 0 and obj.get('plausible', True)]
                    assigned = _assign_detections(row.get('detections', []), gt_objects(visible))
                    matched = [visible[k].get('label', 'obstacle') for k in assigned]
                    if sorted(matched) != sorted(row['matched_labels']):
                        raise ValueError(f'{bag}/{level}: independent assignment differs at {i}')
                    if len(row.get('detections', [])) > len(assigned):
                        unmatched_frames.append(i)
                    for index, obj in enumerate(visible):
                        name = obj.get('label', 'obstacle')
                        record = objects.setdefault(name, {'visible_frames': [], 'inside_frames': [], 'outside_frames': [],
                                                           'unknown_frames': [], 'matched_stop_frames': [],
                                                           'inside_matched_stop_frames': [], 'outside_matched_stop_frames': [],
                                                           'unknown_matched_stop_frames': [],
                                                           'first_stop_frame': None, 'first_stop_m': None})
                        record['visible_frames'].append(i)
                        relation = obj.get('in_gauge', True)
                        record['inside_frames' if relation is True else 'outside_frames' if relation is False else 'unknown_frames'].append(i)
                        if index in assigned:
                            record['matched_stop_frames'].append(i)
                            if relation is True:
                                record['inside_matched_stop_frames'].append(i)
                            elif relation is False:
                                record['outside_matched_stop_frames'].append(i)
                            else:
                                record['unknown_matched_stop_frames'].append(i)
                            if record['first_stop_frame'] is None:
                                record['first_stop_frame'], record['first_stop_m'] = i, float(obj['distance'])
            if rows_read != FRAME_COUNTS[bag] or measurement['frames'] != rows_read:
                raise ValueError(f'{bag}/{level}: incomplete gzip frame sequence')
            for decision in ('STOP', 'FAULT', 'CAUTION', 'GO'):
                if counts[decision] != measurement.get(decision, 0):
                    raise ValueError(f'{bag}/{level}: count disagreement for {decision}')
            if episodes(stop_frames) != measurement.get('stop_episodes', 0) or len(degraded) != measurement.get('degraded_frames', 0):
                raise ValueError(f'{bag}/{level}: episode/degraded disagreement')
            for name, original in measurement['objects'].items():
                if objects[name]['inside_matched_stop_frames'] != original['stop_frames']:
                    raise ValueError(f'{bag}/{level}/{name}: original object summary disagrees')
            level_out = {'frames': rows_read, 'counts': counts, 'stop_frames': stop_frames,
                         'stop_episodes': episodes(stop_frames), 'go_frames': go_frames,
                         'silent_go_frames': silent_go_frames, 'degraded_frames': degraded,
                         'unmatched_stop_frames': unmatched_frames, 'unmatched_stop_episodes': episodes(unmatched_frames),
                         'objects': objects, 'raw_sha256': measurement['raw_sha256']}
            bag_out['levels'][level] = level_out
            if level != 'clean':
                clean = bag_out['levels']['clean']
                level_out['extra_stop_episodes'] = level_out['stop_episodes'] - clean['stop_episodes']
                if bag in EMPTY:
                    level_out['empty_episode_acceptance'] = level_out['extra_stop_episodes'] <= 1
                for name, obj in objects.items():
                    old = clean['objects'][name]
                    obj['lost_clean_stop_frames'] = sorted(set(old['matched_stop_frames']) - set(obj['matched_stop_frames']))
                    obj['new_stop_frames'] = sorted(set(obj['matched_stop_frames']) - set(old['matched_stop_frames']))
                    for relation in ('inside', 'outside', 'unknown'):
                        old_hits = set(old[f'{relation}_matched_stop_frames'])
                        new_hits = set(obj[f'{relation}_matched_stop_frames'])
                        obj[f'lost_clean_{relation}_stop_frames'] = sorted(old_hits - new_hits)
                        obj[f'new_{relation}_stop_frames'] = sorted(new_hits - old_hits)
                    if sum(len(obj[f'lost_clean_{relation}_stop_frames']) for relation in ('inside', 'outside', 'unknown')) != len(obj['lost_clean_stop_frames']):
                        raise ValueError('per-frame gauge relation does not partition lost matches')
                    obj['first_stop_ratio'] = (obj['first_stop_m'] / old['first_stop_m']
                                               if old['first_stop_m'] and obj['first_stop_m'] is not None else None)
                    obj['lost_all_clean_stops'] = bool(old['matched_stop_frames'] and not obj['matched_stop_frames'])
    output['total_processed_frames'] = sum(v['frames_per_level'] * 4 for v in output['recordings'].values())
    output['high_silent_go_frames'] = {bag: row['levels']['high']['silent_go_frames'] for bag, row in output['recordings'].items()}
    output['script_sha256'] = digest(Path(__file__))
    (directory / 'verified_complete.json').write_text(json.dumps(output, indent=2) + '\n')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=HERE / 'baseline')
    parser.add_argument('--dark', type=Path, default=HERE / 'candidate_dark_person')
    parser.add_argument('--only-dark', action='store_true')
    args = parser.parse_args()
    dark = verify(args.dark, ('doubleT_obstacle',), dark=True)
    if args.only_dark:
        print(json.dumps({'dark_complete': True, 'frames': dark['total_processed_frames']}))
        return
    baseline = verify(args.baseline, BAGS)
    if baseline['source_hashes']['resense/metrics.py'] != dark['source_hashes']['resense/metrics.py']:
        raise ValueError('experiments used different matching implementations')
    write_baseline_review(baseline, args.baseline)
    comparison = {'complete': True,
                  'interpretation': 'Different detector source and different original-object intensities: descriptive contrast only, not an isolated causal effect of suppression. Each dusty level is separately compared to its own clean source/intensity control. No extra paired dimmed baseline run is implied.',
                  'baseline_source': baseline['detector_root'], 'dark_source': dark['detector_root'],
                  'baseline_sha256': digest(args.baseline / 'verified_complete.json'),
                  'dark_sha256': digest(args.dark / 'verified_complete.json'), 'levels': {}}
    for level in LEVELS:
        a = baseline['recordings']['doubleT_obstacle']['levels'][level]
        b = dark['recordings']['doubleT_obstacle']['levels'][level]
        comparison['levels'][level] = {'original_intensity_counts': a['counts'], 'dark_candidate_counts': b['counts'], 'objects': {}}
        for name in a['objects']:
            first, second = a['objects'][name], b['objects'][name]
            comparison['levels'][level]['objects'][name] = {
                'first_stop_m': [first['first_stop_m'], second['first_stop_m']],
                'matched_stop_rows': [len(first['matched_stop_frames']), len(second['matched_stop_frames'])],
                'rows_missing_from_dark_contrast': sorted(set(first['matched_stop_frames']) - set(second['matched_stop_frames'])),
                'rows_added_in_dark_contrast': sorted(set(second['matched_stop_frames']) - set(first['matched_stop_frames']))}
            for relation in ('inside', 'outside', 'unknown'):
                comparison['levels'][level]['objects'][name][f'{relation}_matched_stop_rows'] = [
                    len(first[f'{relation}_matched_stop_frames']), len(second[f'{relation}_matched_stop_frames'])]
                comparison['levels'][level]['objects'][name][f'{relation}_rows_missing_from_dark_contrast'] = sorted(
                    set(first[f'{relation}_matched_stop_frames']) - set(second[f'{relation}_matched_stop_frames']))
    (HERE / 'original_vs_dark_descriptive.json').write_text(json.dumps(comparison, indent=2) + '\n')
    print(json.dumps({'baseline_complete': True, 'baseline_frames': baseline['total_processed_frames'],
                      'dark_complete': True, 'dark_frames': dark['total_processed_frames']}))


if __name__ == '__main__':
    main()
