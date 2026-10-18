#!/usr/bin/env python3
"""Verify and summarize the complete frozen-placement Set F dust battery."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

STARTS = (46, 68, 98, 140, 168, 172)
KINDS = ('person', 'box1.0', 'box0.5', 'trolley', 'cable')
LEVELS = ('clean', 'low', 'medium', 'high')
ROOT = Path(__file__).resolve().parents[3]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_raw_row(row, frozen):
    """Audit serialized decisions and bound matching with the captured 1cm precision."""
    result = row['result']
    health = result['health']
    decision = ('STOP' if result['obstacle'] else 'FAULT' if health.get('level') == 'error'
                else 'CAUTION' if result['warning'] or health.get('decision_level') == 'warn' else 'GO')
    if row['decision'] != decision or row['degraded'] != (health.get('decision_level') in ('warn', 'error')):
        raise ValueError('raw decision/degradation differs from captured result')
    if result['stamp'] != frozen['stamp'] or row['clean_returns'] != frozen['clean_returns']:
        raise ValueError('raw stamp/physical truth differs from frozen bank')
    if not 0 <= row['retained_object_returns'] <= row['clean_returns']:
        raise ValueError('impossible retained-object return count')
    certain, possible = [], []
    for detection in result['detections']:
        dx = abs(detection['distance'] - frozen['distance'])
        dy = abs(detection['lateral'] - frozen['spec']['lateral'])
        tolerance = max(2., .03 * frozen['distance'])
        certain.append(dx + .005000001 <= tolerance and dy + .005000001 <= 1.2)
        possible.append(dx - .005000001 <= tolerance and dy - .005000001 <= 1.2)
    low_hit = bool(any(certain) and frozen['clean_returns'] > 0)
    high_hit = bool(any(possible) and frozen['clean_returns'] > 0)
    low_false = len(possible) - sum(possible)
    high_false = len(certain) - sum(certain)
    if not low_hit <= row['hit'] <= high_hit or not low_false <= row['false_detections'] <= high_false:
        raise ValueError('raw association lies outside independent serialized-geometry bounds')
    if low_hit != high_hit or low_false != high_false:
        return {'index': row['index'], 'hit_bounds': [low_hit, high_hit],
                'false_detection_bounds': [low_false, high_false],
                'recorded_hit': row['hit'], 'recorded_false_detections': row['false_detections']}
    return None


def expected_paths(manifest, cache):
    """Reconstruct complete source cadence/cutoff from frozen-provenance metadata."""
    intake_path = ROOT / 'docs/extended_dataset_intake.json'
    if digest(intake_path) != manifest['speeds_sha256']:
        raise ValueError('source speed metadata changed')
    speeds = {row['n']: row.get('speed_tracks') or 0. for row in json.loads(intake_path.read_text())['files']}
    stamps = {}
    for path in cache.glob('*_stamps.json'):
        source = json.loads(path.read_text())
        bag = source.get('bag') or path.name[:-len('_stamps.json')]
        stamps.update({f'{bag}_{frame}': float(stamp) for frame, stamp in source['stamps'].items()})
    selected, planned = {}, {}
    for start in STARTS:
        distance, previous, rows, stopped = 220., None, [], False
        for index in range(110):
            split, frame = start + index // 51, index % 51
            stem = f'new_data_{split}_{frame:04d}'
            stamp = stamps[stem]
            selected[stem] = stamp
            path = cache / f'{stem}.npy.zst'
            if not path.is_file():
                raise ValueError(f'missing required source frame: {path}')
            if previous is not None:
                if not 0 < stamp - previous < 10:
                    raise ValueError('invalid source timestamp cadence')
                distance -= speeds[split] * (stamp - previous)
            previous = stamp
            if distance < 8:
                stopped = True
            if not stopped:
                rows.append({'index': index, 'cache_file': path.name, 'stamp': stamp,
                             'speed': speeds[split], 'distance': distance, 'cache_sha256': digest(path)})
        if not rows:
            raise ValueError('canonical approach cannot be empty')
        planned[start] = rows
    selected_sha = hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest()
    if selected_sha != manifest['selected_stamps_sha256']:
        raise ValueError('canonical source timestamps differ from frozen manifest')
    return planned


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--bank', type=Path, required=True)
    parser.add_argument('--cache', type=Path, default=Path('/home/resense/data/gate_cache/new_data'))
    args = parser.parse_args()
    report_path = args.out / 'summary.json'
    report = json.loads(report_path.read_text())
    manifest_path = args.bank / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if digest(manifest_path) != report['placement_manifest_sha256']:
        raise ValueError('placement manifest changed')
    if (manifest['schema'] != 'set-f-dust-fixed-placement-v2-clean-reference'
            or report['schema'] != 'set-f-dust-battery-v2-clean-reference'):
        raise ValueError('corrected clean-reference schema required')
    harness_path = ROOT / 'scripts/dust_set_f.py'
    if digest(harness_path) != report['script_sha256'] or digest(harness_path) != manifest['script_sha256']:
        raise ValueError('recorded harness changed')
    module_spec = importlib.util.spec_from_file_location('recorded_set_f_harness', harness_path)
    harness = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(harness)
    reference_spec = importlib.util.spec_from_file_location('recorded_dust_reference', ROOT / 'scripts/dust_reference.py')
    reference_helper = importlib.util.module_from_spec(reference_spec)
    reference_spec.loader.exec_module(reference_helper)
    for relative, sha in report['helper_sha256'].items():
        if digest(ROOT / relative) != sha:
            raise ValueError(f'measurement helper changed: {relative}')
    if report['dust_seed'] != 20261018 or digest(ROOT / 'resense/dust.py') != report['dust_generator_sha256']:
        raise ValueError('dust seed/generator differs')
    planned = expected_paths(manifest, args.cache)
    expected = {f'{start}_{kind}' for start in STARTS for kind in KINDS}
    if set(report['sequences']) != expected or set(manifest['sequences']) != expected:
        raise ValueError('all 30 canonical sequences are required')
    for relative, sha in report['source_hashes'].items():
        if digest(Path(report['detector_root']) / relative) != sha:
            raise ValueError(f'measured source changed: {relative}')
    for payload, source_key in ((report, 'detector_root'), (manifest, 'source_root')):
        for relative, sha in payload['source_hashes'].items():
            if digest(Path(payload[source_key]) / relative) != sha:
                raise ValueError(f'frozen placement/evaluation source changed: {relative}')
        for relative, sha in payload['helper_sha256'].items():
            if digest(ROOT / relative) != sha:
                raise ValueError(f'frozen placement/evaluation helper changed: {relative}')
        if digest(Path(payload[source_key]) / 'configs/default.yaml') != payload['configuration_yaml_sha256']:
            raise ValueError('recorded configuration YAML differs')
        if not payload['native_status'].startswith('native'):
            raise ValueError('matched native baseline runtime required')
    receipt = json.loads((args.out / 'verified_ride_receipt.json').read_text())
    if receipt['receipt']['verified'] is not True or receipt['receipt']['total_frames'] != 11271:
        raise ValueError('complete verified ride receipt required')
    totals = {level: Counter() for level in LEVELS}
    details, archives, ratios, complete_misses, rounding_ambiguities = {}, {}, {}, {}, {}
    bank_out = args.out / 'placement_bank'
    bank_out.mkdir(exist_ok=True)
    for start in STARTS:
        for kind in KINDS:
            name = f'{start}_{kind}'
            bank_path = args.bank / f'{name}.json'
            if digest(bank_path) != manifest['sequences'][name]:
                raise ValueError(f'frozen bank changed: {name}')
            bank = json.loads(bank_path.read_text())
            entries = report['sequences'][name]['levels']
            if set(entries) != set(LEVELS):
                raise ValueError(f'all four levels required: {name}')
            if bank['requested_frames'] != 110:
                raise ValueError('expected original 110-frame maximum')
            expected_rows = planned[start]
            if bank['id'] != name or bank['start_split'] != start or bank['kind'] != kind or len(bank['frames']) != len(expected_rows):
                raise ValueError(f'canonical bank identity/coverage differs: {name}')
            for frozen, expected_row in zip(bank['frames'], expected_rows):
                if any(frozen[key] != value for key, value in expected_row.items()):
                    raise ValueError(f'canonical source sequence/cutoff differs: {name}')
                reference_helper._validated_rotation(frozen['dust_reference'])
                if frozen['rail_z'] != frozen['dust_reference']['rail_z_at20']:
                    raise ValueError('clean model rail height differs from augmentation reference')
            details[name] = {'kind': kind, 'start_split': start, 'frames': len(bank['frames']),
                             'first_m': {}, 'lost_clean_stop_rows': {}, 'false_stop_episodes': {}}
            for level in LEVELS:
                entry = entries[level]
                raw_path = args.out / f'{name}_{level}.jsonl.gz'
                if digest(raw_path) != entry['raw_sha256']:
                    raise ValueError(f'capture changed: {name}/{level}')
                with gzip.open(raw_path, 'rt') as stream:
                    raw = [json.loads(line) for line in stream]
                if len(raw) != len(bank['frames']) or entry['frames'] != len(raw):
                    raise ValueError(f'frame coverage differs: {name}/{level}')
                for i, (row, frozen) in enumerate(zip(raw, bank['frames'])):
                    if (row['index'] != i or row['clean_frame_sha256'] != frozen['clean_frame_sha256']
                            or row['cache_file'] != frozen['cache_file'] or row['distance'] != frozen['distance']):
                        raise ValueError(f'frozen placement mismatch: {name}/{level}/{i}')
                    ambiguity = verify_raw_row(row, frozen)
                    if ambiguity is not None:
                        rounding_ambiguities.setdefault(f'{name}/{level}', []).append(ambiguity)
                    audit = row['augmentation']
                    if audit['seed'] != 20261018 or audit['frame_index'] != i:
                        raise ValueError('dust seed/frame differs')
                    if (audit['placement_reference'] != frozen['dust_reference']
                            or row['dust_reference_sha256'] != frozen['dust_reference']['reference_sha256']
                            or audit['rail_z'] != frozen['dust_reference']['rail_z_at20']):
                        raise ValueError('dust placement reference changed across levels')
                    density, extinction = {'clean': (0., 0.), 'low': (.1, .0005), 'medium': (1., .003), 'high': (10., .02)}[level]
                    expected_spec = {'density': density, 'extinction': extinction, 'x_bounds': [2.5, 60.],
                                     'y_bounds': [-3., 3.], 'height_bounds': [.1, 3.5], 'intensity_max': 5.}
                    if audit['spec'] != expected_spec:
                        raise ValueError('dust specification changed')
                    if level == 'clean' and (row['retained_object_returns'] != row['clean_returns']
                                            or audit['added_returns'] != 0 or audit['removed_returns'] != 0):
                        raise ValueError('clean augmentation/return retention differs')
                recomputed = harness.summarize(raw, entries['clean'] if level != 'clean' else None)
                if recomputed != {key: value for key, value in entry.items() if key != 'raw_sha256'}:
                    raise ValueError(f'summary differs from raw recomputation: {name}/{level}')
                stats = totals[level]
                stats['frames'] += entry['frames']
                stats['matched_stop_rows'] += len(entry['hit_frames'])
                stats['clean_supported_frames'] += entry['clean_supported_frames']
                stats['retained_return_supported_frames'] += entry['observed_supported_frames']
                stats['observed_matched_stop_rows'] += len(entry['observed_hit_frames'])
                stats['false_stop_frames'] += len(entry['false_stop_frames'])
                stats['false_stop_episodes'] += entry['false_stop_episodes']
                stats['false_detections'] += entry['false_detections']
                stats['degraded_frames'] += entry['degraded_frames']
                stats['lost_clean_stop_rows'] += len(entry.get('lost_clean_stop_frames', []))
                stats['new_stop_rows'] += len(entry.get('new_stop_frames', []))
                for decision, count in entry['counts'].items():
                    stats[f'decision_{decision}'] += count
                details[name]['first_m'][level] = entry['first_stop_m']
                details[name]['lost_clean_stop_rows'][level] = entry.get('lost_clean_stop_frames', [])
                details[name]['false_stop_episodes'][level] = entry['false_stop_episodes']
                if level != 'clean' and entries['clean']['first_stop_m'] is not None:
                    if entry['first_stop_m'] is None:
                        complete_misses.setdefault(level, []).append(name)
                    else:
                        ratios.setdefault(level, {})[name] = entry['first_stop_m'] / entries['clean']['first_stop_m']
            archive = bank_out / f'{name}.json.gz'
            with bank_path.open('rb') as src, archive.open('wb') as dst:
                with gzip.GzipFile(filename='', mode='wb', fileobj=dst, mtime=0) as zipped:
                    shutil.copyfileobj(src, zipped)
            archives[name] = {'raw_sha256': digest(bank_path), 'gzip_sha256': digest(archive),
                              'archive': str(archive.relative_to(args.out))}
    aggregate = {'complete': True, 'sequences': 30, 'levels': LEVELS,
                 'total_processed_frames': sum(v['frames'] for v in totals.values()),
                 'totals': totals, 'details': details, 'first_stop_ratios': ratios,
                 'lost_all_clean_object_stops': complete_misses,
                 'summary_sha256': digest(report_path), 'placement_archives': archives,
                 'serialized_geometry_boundary_rows': rounding_ambiguities,
                 'association_verification': 'Independent legacy matching bounds allow +/-0.005m serialized distance/lateral rounding. Every recorded hit/false count must lie within these bounds; ambiguous rows remain explicit. All aggregate fields are exactly recomputed from raw through the hash-verified measurement summarizer.',
                 'script_sha256': digest(Path(__file__)),
                 'scope': 'Frozen legacy model-derived objects on complete real ride backgrounds. Original 110-frame maximum and 8m cutoff; same exact placement at all levels. Unmatched detections use the unchanged approximate legacy association. Simulation only, not physical dust certification. Timing under concurrent load is informational.'}
    (args.out / 'aggregate.json').write_text(json.dumps(aggregate, indent=2) + '\n')
    lines = ['# Set F dust baseline: complete fixed-placement battery', '',
             'All 30 object/ride sequences completed at clean, low, medium and high density.',
             'Source, raw-output and frozen-placement hashes were checked before this report.',
             'The original maximum is 110 frames; each sequence stops when its target passes 8 m.',
             'Every density uses the identical frozen sequence and retains clean physical truth',
             'when attenuation removes its returns. These are simulated stresses, not measured dust physics.', '',
             '| Level | Frames | Matched STOP rows | Lost clean STOP rows | Unmatched STOP frames / episodes | GO | Degraded |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for level in LEVELS:
        row = totals[level]
        lines.append(f"| {level} | {row['frames']} | {row['matched_stop_rows']} | {row['lost_clean_stop_rows']} | {row['false_stop_frames']} / {row['false_stop_episodes']} | {row['decision_GO']} | {row['degraded_frames']} |")
    lines += ['', 'Episodes are summed within independent sequences, never joined across runs.',
              'Unmatched detections are reported under the original fixed matching tolerance;',
              'Serialized detections have 1 cm precision; independent matching uses explicit',
              'rounding bounds and retains any boundary ambiguity in aggregate.json.',
              'the real backgrounds are not exhaustively annotated. Zero matches at every',
              'density remain visible below rather than being silently excluded.', '',
              '| Sequence | Frames | First STOP m: clean / low / medium / high | Lost clean rows: low / medium / high |',
              '|---|---:|---|---|']
    for name, row in details.items():
        first = ' / '.join('—' if row['first_m'][level] is None else f"{row['first_m'][level]:.2f}" for level in LEVELS)
        lost = ' / '.join(str(len(row['lost_clean_stop_rows'][level])) for level in LEVELS[1:])
        lines.append(f"| {name} | {row['frames']} | {first} | {lost} |")
    lines += ['', 'See [aggregate.json](aggregate.json) for every lost row and first-range ratio,',
              '[summary.json](summary.json) for per-level results/source hashes, and',
              '[placement_manifest.json](placement_manifest.json) plus `placement_bank/` for the frozen objects.',
              'No dust-suppression or health-only runtime candidate is activated by this battery.',
              'Measurements shared the single-CPU host; they do not establish isolated throughput.', '']
    (args.out / 'RESULTS.md').write_text('\n'.join(lines))
    print(json.dumps({'complete': True, 'total_processed_frames': aggregate['total_processed_frames'],
                      'totals': totals, 'lost_all_clean_object_stops': complete_misses}))


if __name__ == '__main__':
    main()
