#!/usr/bin/env python3
"""Complete-only verification of seven-bag baseline and separate dark-person experiment."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
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
    ratio = crossing['first_inside_stop_ratio']
    person_status = 'FAIL' if ratio is None or ratio < .9 else 'PASS'
    lines += ['', f"Low-density crossing first-range criterion (at least 90% of clean): **{person_status}**, ratio **{ratio}**.",
              'Per-frame STOP retention is reported separately; a preserved first range does not imply preserved later detections.', '',
              '| Object | Level | Temporal first STOP m: any / inside | Inside / outside / unknown matches | Lost clean inside / outside / unknown |',
              '|---|---|---|---|---|']
    for bag in BAGS[len(EMPTY):]:
        for name in report['recordings'][bag]['levels']['clean']['objects']:
            for level, row in report['recordings'][bag]['levels'].items():
                obj = row['objects'][name]
                distance = 'none' if obj['first_stop_m'] is None else f"{obj['first_stop_m']:.2f}"
                inside_distance = 'none' if obj['first_inside_stop_m'] is None else f"{obj['first_inside_stop_m']:.2f}"
                matched = ' / '.join(str(len(obj[f'{rel}_matched_stop_frames'])) for rel in ('inside', 'outside', 'unknown'))
                lost = 'reference' if level == 'clean' else ' / '.join(str(len(obj[f'lost_clean_{rel}_stop_frames'])) for rel in ('inside', 'outside', 'unknown'))
                lines.append(f'| {bag}: {name} | {level} | {distance} / {inside_distance} | {matched} | {lost} |')
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
              'The corrected captures include source, native-library, configuration and helper hashes',
              'at start and after each completed level; the verifier checks those immutable dependencies.',
              'These are fixed synthetic stresses, not calibrated physical dust. Timing shared a single-CPU',
              'host and includes recorded pauses, so it does not establish throughput.', '']
    (directory / 'RESULTS.md').write_text('\n'.join(lines))


def verify(directory, expected_bags, dark=False, health_only=False, levels=LEVELS):
    summary_path = directory / 'summary.json'
    report = json.loads(summary_path.read_text())
    if report.get('schema') != 'dust-battery-v2':
        raise ValueError('corrected clean-coordinate schema required')
    if report.get('native_enabled') is not True:
        raise ValueError('matched native baseline runtime required')
    if set(report['recordings']) != set(expected_bags):
        raise ValueError(f'{directory.name}: missing or unexpected recordings')
    if report['seed'] != 20261018 or report['config_overrides']:
        raise ValueError('unexpected seed or configuration overrides')
    if report.get('dust_support') or report.get('health_only') is not health_only:
        raise ValueError('unexpected suppression/health-only mode')
    if report.get('dim_label_intensity') != (1. if dark else None):
        raise ValueError('unexpected source-object intensity intervention')
    identity = report['runtime_identity_start']
    if identity != report['runtime_identity_end']:
        raise ValueError('measurement helper/native/config identity changed during capture')
    for path, recorded in identity.items():
        if digest(Path(path)) != recorded:
            raise ValueError(f'frozen measurement dependency drift: {path}')
    reference_paths = [Path(path) for path in identity if path.endswith('/scripts/dust_reference.py')]
    if len(reference_paths) != 1:
        raise ValueError('one captured clean-reference helper is required')
    module_spec = importlib.util.spec_from_file_location('verified_regular_dust_reference', reference_paths[0])
    reference_helper = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(reference_helper)
    source = Path(report['detector_root'])
    for relative, recorded in report['source_hashes'].items():
        if digest(source / relative) != recorded:
            raise ValueError(f'immutable source drift: {relative}')
    if health_only:
        support_paths = [Path(path) for path in identity if path.endswith('/resense/dust_health.py')]
        if len(support_paths) != 1 or digest(support_paths[0]) != report['support_sha256']:
            raise ValueError('health experiment implementation differs from frozen harness source')
    # The immutable core metrics assignment is shared by both experiments.
    sys.path.insert(0, str(source))
    import numpy as np
    from resense.config import DetectorConfig
    from resense.frame import Frame, axis_matrix
    from resense.metrics import _assign_detections, gt_objects
    cfg = DetectorConfig.from_yaml(str(source / 'configs/default.yaml'))
    rotation = axis_matrix(cfg.sensor).astype(np.float32)
    output = {'complete': True, 'scope': {'dark': dark, 'health_only': health_only, 'recordings': expected_bags, 'levels': levels},
              'summary_sha256': digest(summary_path), 'detector_root': str(source),
              'source_hashes': report['source_hashes'], 'generator_sha256': report['generator_sha256'],
              'support_sha256': report.get('support_sha256'), 'dim_label_intensity': report.get('dim_label_intensity'),
              'runtime_identity': identity,
              'configuration_file_sha256_at_verification': digest(source / 'configs/default.yaml'),
              'recordings': {}, 'label_sha256': {},
              'limits': ['Cloud geometry uses the frozen clean applied axes and a flat height anchored at rail_z(20m), not a surveyed or graded rail plane.',
                         'Legacy labels/matching are retained; outside-object results are included, not silently counted as true positives.',
                         'Concurrent wall/latency timings are informational; this is not measured physical dust.']}
    for bag in expected_bags:
        recorded = report['recordings'][bag]
        if recorded['frames'] != FRAME_COUNTS[bag] or set(recorded['levels']) != set(levels):
            raise ValueError(f'{bag}: all requested complete levels are required')
        meta_path = Path('/home/resense/data/decoded') / bag / 'meta.json'
        meta = json.loads(meta_path.read_text())
        if len(meta) != FRAME_COUNTS[bag]:
            raise ValueError(f'{bag}: decoded frame count differs')
        label_path = ROOT / 'labels' / f'{bag}.json'
        labels = json.loads(label_path.read_text()) if label_path.exists() else {}
        if recorded['labels_sha256'] != (digest(label_path) if label_path.exists() else None):
            raise ValueError('label provenance differs')
        if labels:
            output['label_sha256'][bag] = digest(label_path)
        bag_out = {'frames_per_level': FRAME_COUNTS[bag], 'cache_sha256_from_replay': recorded['cache_sha256'],
                   'metadata_sha256_at_verification': digest(meta_path), 'levels': {}}
        output['recordings'][bag] = bag_out
        clean_references = []
        cache_digest = hashlib.sha256(meta_path.read_bytes())
        for level in levels:
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
                    reference = row['clean_reference']
                    reference_helper._validated_rotation(reference)
                    if level == 'clean':
                        if audit is not None:
                            raise ValueError('clean input unexpectedly augmented')
                        cache_path = meta_path.parent / f'f_{i:05d}.npz'
                        cache_digest.update(cache_path.name.encode())
                        cache_digest.update(bytes.fromhex(digest(cache_path)))
                        with np.load(cache_path) as data:
                            frame = Frame(data['xyz'] @ rotation.T, data['inten'],
                                          data['ring'] if meta[i]['has_ring'] else None,
                                          meta[i]['stamp'], meta[i]['frame_id'],
                                          {'n_raw': meta[i]['n_raw'], 'n_near': meta[i]['n_near']})
                        if dark:
                            for label in labels.get(f'{i:05d}', []):
                                if label.get('bbox') is not None and label.get('n_points', 1) > 0:
                                    lo, hi = np.asarray(label['bbox'])
                                    frame.intensity[((frame.xyz >= lo) & (frame.xyz <= hi)).all(axis=1)] = 1.
                        if reference_helper.source_frame_sha256(frame) != reference['source_frame_sha256']:
                            raise ValueError('clean reference source payload differs from cache/intervention')
                        clean_references.append(reference)
                    else:
                        if reference != clean_references[i] or audit['placement_reference'] != reference or audit['rail_z'] != reference['rail_z_at20']:
                            raise ValueError('frozen clean reference changed across density levels')
                        if audit['seed'] != 20261018 or audit['frame_index'] != i:
                            raise ValueError('augmentation seed/frame mismatch')
                        density, extinction = {'low': (.1, .0005), 'medium': (1., .003), 'high': (10., .02)}[level]
                        expected = {'density': density, 'extinction': extinction, 'x_bounds': [2.5, 60.],
                                    'y_bounds': [-3., 3.], 'height_bounds': [.1, 3.5], 'intensity_max': 5.}
                        if audit['spec'] != expected:
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
                                                           'first_inside_stop_frame': None, 'first_inside_stop_m': None,
                                                           'first_stop_frame': None, 'first_stop_m': None})
                        record['visible_frames'].append(i)
                        relation = obj.get('in_gauge', True)
                        record['inside_frames' if relation is True else 'outside_frames' if relation is False else 'unknown_frames'].append(i)
                        if index in assigned:
                            record['matched_stop_frames'].append(i)
                            if relation is True:
                                record['inside_matched_stop_frames'].append(i)
                                if record['first_inside_stop_frame'] is None:
                                    record['first_inside_stop_frame'], record['first_inside_stop_m'] = i, float(obj['distance'])
                            elif relation is False:
                                record['outside_matched_stop_frames'].append(i)
                            else:
                                record['unknown_matched_stop_frames'].append(i)
                            if record['first_stop_frame'] is None:
                                record['first_stop_frame'], record['first_stop_m'] = i, float(obj['distance'])
            if rows_read != FRAME_COUNTS[bag] or measurement['frames'] != rows_read:
                raise ValueError(f'{bag}/{level}: incomplete gzip frame sequence')
            if level == 'clean' and cache_digest.hexdigest() != recorded['cache_sha256']:
                raise ValueError('complete source cache payload hash differs')
            for decision in ('STOP', 'FAULT', 'CAUTION', 'GO'):
                if counts[decision] != measurement.get(decision, 0):
                    raise ValueError(f'{bag}/{level}: count disagreement for {decision}')
            if episodes(stop_frames) != measurement.get('stop_episodes', 0) or len(degraded) != measurement.get('degraded_frames', 0):
                raise ValueError(f'{bag}/{level}: episode/degraded disagreement')
            for name, original in measurement['objects'].items():
                if (objects[name]['inside_matched_stop_frames'] != original['stop_frames']
                        or objects[name]['first_inside_stop_frame'] != original['first_stop_frame']
                        or objects[name]['first_inside_stop_m'] != original['first_stop_m']):
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
                    obj['first_inside_stop_ratio'] = (obj['first_inside_stop_m'] / old['first_inside_stop_m']
                                                      if old['first_inside_stop_m'] and obj['first_inside_stop_m'] is not None else None)
                    obj['lost_all_clean_stops'] = bool(old['matched_stop_frames'] and not obj['matched_stop_frames'])
    output['total_processed_frames'] = sum(v['frames_per_level'] * len(levels) for v in output['recordings'].values())
    output['high_silent_go_frames'] = {bag: row['levels']['high']['silent_go_frames'] for bag, row in output['recordings'].items()}
    output['script_sha256'] = digest(Path(__file__))
    (directory / 'verified_complete.json').write_text(json.dumps(output, indent=2) + '\n')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, default=HERE / 'baseline_pose_fixed')
    parser.add_argument('--dark', type=Path, default=HERE / 'dark_baseline_pose_fixed')
    parser.add_argument('--health-dark', type=Path, default=HERE / 'dark_health_pose_fixed')
    parser.add_argument('--health-platform', type=Path, default=HERE / 'health_platform_pose_fixed')
    parser.add_argument('--mode', choices=('all', 'baseline', 'dark_baseline', 'dark_health', 'health_platform'), default='all')
    args = parser.parse_args()
    requested = {'baseline': (args.baseline, BAGS, False, False, LEVELS),
                 'dark_baseline': (args.dark, ('doubleT_obstacle',), True, False, LEVELS),
                 'dark_health': (args.health_dark, ('doubleT_obstacle',), True, True, LEVELS),
                 'health_platform': (args.health_platform, ('doubleT_platform',), False, True, ('clean', 'medium', 'high'))}
    verified = {}
    for mode, values in requested.items():
        if args.mode not in ('all', mode):
            continue
        directory, bags, dark, health_only, levels = values
        verified[mode] = verify(directory, bags, dark=dark, health_only=health_only, levels=levels)
        if mode == 'baseline':
            write_baseline_review(verified[mode], directory)
    if args.mode != 'all':
        print(json.dumps({'complete': args.mode, 'frames': verified[args.mode]['total_processed_frames']}))
        return
    baseline = verified['baseline']
    if any(item['source_hashes'] != baseline['source_hashes'] for item in verified.values()):
        raise ValueError('matched controls must use exactly the same detector source')
    comparison = {'complete': True, 'detector_source': baseline['detector_root'],
                  'scope': 'Exact health-only detection parity against matching intensity/source/coordinate controls; health, clear-range and timing fields may change.',
                  'verified_capture_sha256': {mode: digest(values[0] / 'verified_complete.json') for mode, values in requested.items()},
                  'cases': {}}
    for before_mode, after_mode, bag in (('dark_baseline', 'dark_health', 'doubleT_obstacle'),
                                         ('baseline', 'health_platform', 'doubleT_platform')):
        for level in requested[after_mode][4]:
            captures = []
            for mode in (before_mode, after_mode):
                with gzip.open(requested[mode][0] / f'{bag}_{level}.jsonl.gz', 'rt') as stream:
                    captures.append([json.loads(line) for line in stream])
            if len(captures[0]) != len(captures[1]):
                raise ValueError('paired health control length differs')
            differences, reference_differences = {}, []
            for i, (before, after) in enumerate(zip(*captures)):
                if before['clean_reference'] != after['clean_reference'] or before['augmentation'] != after['augmentation']:
                    reference_differences.append(i)
                for field in ('frame', 'stamp', 'obstacle', 'warning', 'nearest_distance', 'detections',
                              'warnings', 'track', 'n_points', 'n_corridor', 'matched_labels', 'n_candidates',
                              'n_accumulated', 'ego_speed', 'ego_speed_source', 'ego_speed_estimate',
                              'ego_speed_confidence', 'mount'):
                    if before[field] != after[field]:
                        differences.setdefault(field, []).append(i)
            case = f'{after_mode}/{level}'
            comparison['cases'][case] = {'frames': len(captures[0]), 'changed_detection_fields': differences,
                                        'changed_augmentation_or_reference_frames': reference_differences,
                                        'exact_parity': not differences and not reference_differences,
                                        'health_counts': verified[after_mode]['recordings'][bag]['levels'][level]['counts'],
                                        'health_degraded_frames': len(verified[after_mode]['recordings'][bag]['levels'][level]['degraded_frames'])}
    comparison['all_detection_inputs_and_outputs_identical'] = all(row['exact_parity'] for row in comparison['cases'].values())
    (HERE / 'corrected_health_parity.json').write_text(json.dumps(comparison, indent=2) + '\n')
    print(json.dumps({'complete': True, 'frames': {mode: item['total_processed_frames'] for mode, item in verified.items()},
                      'health_detection_parity': comparison['all_detection_inputs_and_outputs_identical']}))


if __name__ == '__main__':
    main()
