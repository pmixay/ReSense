#!/usr/bin/env python3
"""Verify and summarize the complete frozen-placement Set F dust battery."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import shutil

STARTS = (46, 68, 98, 140, 168, 172)
KINDS = ('person', 'box1.0', 'box0.5', 'trolley', 'cable')
LEVELS = ('clean', 'low', 'medium', 'high')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--bank', type=Path, required=True)
    args = parser.parse_args()
    report_path = args.out / 'summary.json'
    report = json.loads(report_path.read_text())
    manifest_path = args.bank / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if digest(manifest_path) != report['placement_manifest_sha256']:
        raise ValueError('placement manifest changed')
    expected = {f'{start}_{kind}' for start in STARTS for kind in KINDS}
    if set(report['sequences']) != expected or set(manifest['sequences']) != expected:
        raise ValueError('all 30 canonical sequences are required')
    for relative, sha in report['source_hashes'].items():
        if digest(Path(report['detector_root']) / relative) != sha:
            raise ValueError(f'measured source changed: {relative}')
    receipt = json.loads((args.out / 'verified_ride_receipt.json').read_text())
    if receipt['receipt']['verified'] is not True or receipt['receipt']['total_frames'] != 11271:
        raise ValueError('complete verified ride receipt required')
    totals = {level: Counter() for level in LEVELS}
    details, archives, ratios, complete_misses = {}, {}, {}, {}
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
