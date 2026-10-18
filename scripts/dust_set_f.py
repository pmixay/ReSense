#!/usr/bin/env python3
"""Set F dust stress with frozen clean legacy placements, separate from runtime decisions.

Prepare with an immutable baseline; evaluate that bank under clean/low/medium/high.
The bank saves full-precision geometry, render seeds and exact clean-frame hashes,
not several gigabytes of repeated background points. Every evaluated rendering
must reproduce its frozen hash before dust is applied. No detector receives truth.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
STARTS = (46, 68, 98, 140, 168, 172)
KINDS = ('person', 'box1.0', 'box0.5', 'trolley', 'cable')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_default(value):
    return value.tolist() if hasattr(value, 'tolist') else value.item()


def same_json(left, right):
    return json.dumps(left, sort_keys=True, default=json_default) == json.dumps(right, sort_keys=True, default=json_default)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def frame_hash(frame):
    """Payload hash includes dtype, shape and channel absence; metadata is separately frozen."""
    h = hashlib.sha256()
    for array in (frame.xyz, frame.intensity, frame.ring):
        if array is None:
            h.update(b'None')
        else:
            h.update(str(array.dtype).encode())
            h.update(str(array.shape).encode())
            h.update(array.tobytes())
    return h.hexdigest()


def without_truth(frame):
    from dataclasses import replace
    return replace(frame, meta={key: value for key, value in frame.meta.items() if key != 'obstacles'})


def canonical_jobs():
    """Exactly the sealed Set F seed-0 draw order; dust has its separate seed."""
    import numpy as np
    from resense.synthetic import OBJECT_CATALOGUE
    rng = np.random.default_rng(0)
    for start in STARTS:
        for kind in KINDS:
            reflectivity = float(rng.uniform(*OBJECT_CATALOGUE[kind].reflectivity))
            yield {'id': f'{start}_{kind}', 'start_split': start, 'kind': kind,
                   'reflectivity': reflectivity, 'lateral': float(rng.uniform(-.6, .6)),
                   'render_seed': int(rng.integers(1 << 30))}


def sequence_path(files, stamps, speeds, distance=220.):
    from scripts.cache_io import cache_file_stem
    result, previous = [], None
    for path, speed in zip(files, speeds):
        stem = cache_file_stem(path)
        if stem not in stamps:
            raise ValueError(f'missing source timestamp: {stem}')
        stamp = stamps[stem]
        if previous is not None:
            gap = stamp - previous
            if not 0 < gap < 10:
                raise ValueError(f'discontinuous source timestamp: {stem}')
            distance -= speed * gap
        previous = stamp
        if distance < 8:
            break
        result.append((path, stamp, speed, distance))
    return result


def prepare_sequence(files, stamps, speeds, job, cfg, start_distance=220.):
    import numpy as np
    from resense.detector import Detector
    from resense.frame import frame_from_compact
    from resense.synthetic import inject_obstacles
    from scripts.cache_io import cache_file_stem, load_cache_array
    from scripts.far_range_eval import legacy_placement
    reference_helper = load_module('set_f_dust_reference', ROOT / 'scripts/dust_reference.py')
    # Only this independent baseline instance advances placement. Evaluated dust
    # detectors are constructed later and cannot feed state back into this bank.
    placement = Detector(cfg)
    rows = []
    for index, (path, stamp, speed, distance) in enumerate(sequence_path(files, stamps, speeds, start_distance)):
        fr = frame_from_compact(load_cache_array(path), cfg.sensor, stamp=stamp, frame_id=cache_file_stem(path))
        spec, model = legacy_placement(fr.xyz, cfg.track, placement.track, job['kind'], distance,
                                       job['lateral'], job['reflectivity'], 'bed')
        rendered = inject_obstacles(fr, model, [spec],
                                    rng=np.random.default_rng(np.random.SeedSequence([job['render_seed'], index, 1])),
                                    dropout_start=60., dropout_full=200.)
        _, reference = reference_helper.process_clean_reference(placement, without_truth(rendered.frame))
        rows.append({'index': index, 'cache_file': Path(path).name, 'cache_sha256': digest(Path(path)),
                     'stamp': stamp, 'speed': speed, 'distance': distance,
                     'spec': asdict(spec), 'placement_model': asdict(model),
                     'placement_rail_z_at20': float(model.rail_z(np.array([20.]))[0]),
                     'rail_z': reference['rail_z_at20'], 'dust_reference': reference,
                     'clean_returns': int(rendered.n_added[0]), 'clean_frame_sha256': frame_hash(rendered.frame)})
    return {**job, 'requested_frames': len(files), 'frames': rows}


def render_frozen(row, bank, cache, cfg):
    import numpy as np
    from resense.frame import frame_from_compact
    from resense.synthetic import ObstacleSpec, inject_obstacles
    from resense.track import TrackModel
    from scripts.cache_io import cache_file_stem, load_cache_array
    path = cache / row['cache_file']
    if digest(path) != row['cache_sha256']:
        raise ValueError(f'source cache changed: {path}')
    fr = frame_from_compact(load_cache_array(str(path)), cfg.sensor, stamp=row['stamp'], frame_id=cache_file_stem(str(path)))
    model = TrackModel(**dict(row['placement_model'], floor_coef=np.asarray(row['placement_model']['floor_coef'])))
    spec = ObstacleSpec(**row['spec'])
    rendered = inject_obstacles(fr, model, [spec],
                                rng=np.random.default_rng(np.random.SeedSequence([bank['render_seed'], row['index'], 1])),
                                dropout_start=60., dropout_full=200.)
    if frame_hash(rendered.frame) != row['clean_frame_sha256'] or rendered.n_added[0] != row['clean_returns']:
        raise ValueError(f'clean rendering drift at {bank["id"]}/{row["index"]}')
    return rendered, spec, model


def summarize(rows, clean=None):
    counts = Counter(row['decision'] for row in rows)
    hit_frames = [row['index'] for row in rows if row['hit']]
    fp_frames = [row['index'] for row in rows if row['false_detections']]
    fp_set = set(fp_frames)
    result = {'frames': len(rows), 'counts': dict(counts), 'hit_frames': hit_frames,
              'first_stop_frame': hit_frames[0] if hit_frames else None,
              'first_stop_m': next((row['distance'] for row in rows if row['hit']), None),
              'clean_supported_frames': sum(row['clean_returns'] > 0 for row in rows),
              'observed_supported_frames': sum(row['retained_object_returns'] > 0 for row in rows),
              'observed_hit_frames': [row['index'] for row in rows if row['hit'] and row['retained_object_returns'] > 0],
              'false_stop_frames': fp_frames,
              'false_stop_episodes': sum(i - 1 not in fp_set for i in fp_frames),
              'false_detections': sum(row['false_detections'] for row in rows),
              'degraded_frames': sum(row['degraded'] for row in rows),
              'go_frames': [row['index'] for row in rows if row['decision'] == 'GO']}
    if clean is not None:
        result['lost_clean_stop_frames'] = sorted(set(clean['hit_frames']) - set(hit_frames))
        result['new_stop_frames'] = sorted(set(hit_frames) - set(clean['hit_frames']))
        result['extra_false_stop_episodes'] = result['false_stop_episodes'] - clean['false_stop_episodes']
        first = clean['first_stop_m']
        result['first_stop_ratio'] = result['first_stop_m'] / first if first and result['first_stop_m'] is not None else None
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--bank', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--placement-root', type=Path, required=True)
    p.add_argument('--detector-root', type=Path, required=True)
    p.add_argument('--mode', choices=('all', 'prepare', 'evaluate'), default='all')
    p.add_argument('--levels', default='clean,low,medium,high')
    p.add_argument('--seed', type=int, default=20261018)
    a = p.parse_args()
    if a.mode == 'all':
        command = [sys.executable, str(Path(__file__).resolve()), '--cache', str(a.cache), '--bank', str(a.bank),
                   '--out', str(a.out), '--placement-root', str(a.placement_root), '--detector-root', str(a.detector_root)]
        subprocess.run(command + ['--mode', 'prepare'], check=True)
        subprocess.run(command + ['--mode', 'evaluate', '--levels', a.levels, '--seed', str(a.seed)], check=True)
        return
    source = a.placement_root if a.mode == 'prepare' else a.detector_root
    sys.path.insert(0, str(source.resolve()))
    import numpy as np
    from resense import _native
    from resense.config import DetectorConfig
    from resense.detector import Detector
    if str(ROOT) not in sys.path:
        sys.path.append(str(ROOT))
    from scripts.cache_io import cache_files, load_cache_stamps
    from scripts.far_range_eval import consecutive_files, placement_match
    cfg = DetectorConfig.from_yaml(str(source / 'configs/default.yaml'))
    if not _native.enabled():
        raise RuntimeError(f'native runtime required for matched baseline measurement: {_native.status()}')
    sources = {str(f.relative_to(source)): digest(f) for f in sorted((source / 'resense').rglob('*'))
               if f.is_file() and f.suffix in ('.py', '.so', '.json')}
    helpers = {str(f.relative_to(ROOT)): digest(f) for f in
               (ROOT / 'scripts/far_range_eval.py', ROOT / 'scripts/cache_io.py', ROOT / 'scripts/dust_reference.py')}
    a.bank.mkdir(parents=True, exist_ok=True)
    a.out.mkdir(parents=True, exist_ok=True)
    if a.mode == 'prepare':
        intake = json.loads((ROOT / 'docs/extended_dataset_intake.json').read_text())
        speed_map = {row['n']: row.get('speed_tracks') or 0. for row in intake['files']}
        all_files, stamps = cache_files(str(a.cache)), load_cache_stamps(str(a.cache))
        from scripts.cache_io import cache_file_stem
        planned = {}
        for start in STARTS:
            index = next((i for i, f in enumerate(all_files) if Path(f).name.startswith(f'new_data_{start}_')), None)
            if index is None:
                raise ValueError(f'missing start split {start}')
            planned[start] = consecutive_files(all_files, index, 110)
            if len(planned[start]) != 110:
                raise ValueError(f'start {start}: all 110 consecutive source frames are required')
        selected_stamps = {cache_file_stem(f): stamps.get(cache_file_stem(f)) for files in planned.values() for f in files}
        manifest = {'schema': 'set-f-dust-fixed-placement-v2-clean-reference', 'source_root': str(source), 'source_hashes': sources,
                    'configuration_yaml_sha256': digest(source / 'configs/default.yaml'),
                    'native_status': _native.status(),
                    'configuration': asdict(cfg), 'object_seed': 0, 'starts': STARTS, 'kinds': KINDS,
                    'script_sha256': digest(Path(__file__)),
                    'helper_sha256': helpers,
                    'speeds_sha256': digest(ROOT / 'docs/extended_dataset_intake.json'),
                    'selected_stamps_sha256': hashlib.sha256(json.dumps(selected_stamps, sort_keys=True).encode()).hexdigest(),
                    'placement': 'legacy baseline state, frozen before any dust evaluation',
                    'dust_coordinates': 'actual applied clean input-to-model matrix and clean rail_z(20), frozen per frame',
                    'sequences': {}}
        previous_manifest = a.bank / 'manifest.json'
        previous = json.loads(previous_manifest.read_text()) if previous_manifest.exists() else None
        if previous is not None and any(not same_json(previous[key], value)
                                        for key, value in manifest.items() if key != 'sequences'):
            raise ValueError('existing placement bank provenance differs; choose a new bank directory')
        for job in canonical_jobs():
            output = a.bank / (job['id'] + '.json')
            if previous is not None and job['id'] in previous['sequences'] and output.exists() and previous['sequences'][job['id']] == digest(output):
                saved = json.loads(output.read_text())
                if all(digest(a.cache / row['cache_file']) == row['cache_sha256'] for row in saved['frames']):
                    manifest['sequences'][job['id']] = digest(output)
                    print('verified existing bank', job['id'], flush=True)
                    continue
            files = planned[job['start_split']]
            speeds = [speed_map[int(Path(f).name.split('_')[2])] for f in files]
            bank = prepare_sequence(files, stamps, speeds, job, cfg)
            output.write_text(json.dumps(bank, default=json_default, separators=(',', ':')) + '\n')
            manifest['sequences'][job['id']] = digest(output)
            (a.bank / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
            print('prepared', job['id'], len(bank['frames']), flush=True)
        return
    manifest = json.loads((a.bank / 'manifest.json').read_text())
    if set(manifest['sequences']) != {job['id'] for job in canonical_jobs()}:
        raise ValueError('bank must contain all 30 canonical sequences')
    dust = load_module('set_f_dust_generator', ROOT / 'resense/dust.py')
    reference_helper = load_module('set_f_dust_reference', ROOT / 'scripts/dust_reference.py')
    levels = a.levels.split(',')
    if not levels or levels[0] != 'clean' or any(level not in dust.PRESETS for level in levels):
        raise ValueError('levels must start with clean and use registered dust presets')
    if manifest['schema'] != 'set-f-dust-fixed-placement-v2-clean-reference':
        raise ValueError('corrected clean-reference placement bank required')
    report = {'schema': 'set-f-dust-battery-v2-clean-reference', 'placement_manifest_sha256': digest(a.bank / 'manifest.json'),
              'configuration_yaml_sha256': digest(source / 'configs/default.yaml'), 'native_status': _native.status(),
              'detector_root': str(source), 'source_hashes': sources, 'configuration': asdict(cfg),
              'dust_seed': a.seed, 'dust_generator_sha256': digest(ROOT / 'resense/dust.py'),
              'script_sha256': digest(Path(__file__)), 'sequences': {},
              'helper_sha256': helpers,
              'truth_note': 'Clean physical object persists through attenuation; observed-return recall is separate. Legacy placement is model-derived, not surveyed truth.'}
    summary_path = a.out / 'summary.json'
    if summary_path.exists():
        previous = json.loads(summary_path.read_text())
        if any(not same_json(previous[key], value) for key, value in report.items() if key != 'sequences'):
            raise ValueError('existing measurement provenance differs; choose a new output directory')
        report = previous
    (a.out / 'placement_manifest.json').write_bytes((a.bank / 'manifest.json').read_bytes())
    for job in canonical_jobs():
        bank_path = a.bank / (job['id'] + '.json')
        if digest(bank_path) != manifest['sequences'][job['id']]:
            raise ValueError('frozen placement bank changed')
        bank = json.loads(bank_path.read_text())
        entries = report['sequences'].setdefault(job['id'], {'kind': job['kind'], 'levels': {}})
        for level in levels:
            output = a.out / f'{job["id"]}_{level}.jsonl.gz'
            if level in entries['levels'] and output.exists() and digest(output) == entries['levels'][level]['raw_sha256']:
                print('verified existing measurement', job['id'], level, flush=True)
                continue
            detector, rows = Detector(cfg), []
            with gzip.open(output, 'wt') as stream:
                for item in bank['frames']:
                    injected, spec, model = render_frozen(item, bank, a.cache, cfg)
                    frame, audit, origins = reference_helper.augment_in_reference(
                        without_truth(injected.frame), dust.PRESETS[level], item['dust_reference'],
                        seed=a.seed, frame_index=item['index'], augment=dust.augment_dust)
                    retained = int(np.count_nonzero(injected.labels[origins[origins >= 0]] > 0))
                    result = detector.process(without_truth(frame))
                    matches = [placement_match(d, spec.distance, spec, model, result.track, 'legacy') for d in result.detections]
                    health = result.health
                    decision = ('STOP' if result.obstacle else 'FAULT' if health.get('level') == 'error'
                                else 'CAUTION' if result.warning or health.get('decision_level') == 'warn' else 'GO')
                    row = {'index': item['index'], 'cache_file': item['cache_file'], 'distance': spec.distance,
                           'clean_returns': item['clean_returns'], 'retained_object_returns': retained,
                           'hit': bool(any(matches) and item['clean_returns'] > 0),
                           'false_detections': sum(not m for m in matches), 'decision': decision,
                           'degraded': health.get('decision_level') in ('warn', 'error'), 'augmentation': audit,
                           'dust_reference_sha256': item['dust_reference']['reference_sha256'],
                           'clean_frame_sha256': item['clean_frame_sha256'], 'result': result.to_dict()}
                    rows.append(row)
                    stream.write(json.dumps(row, separators=(',', ':')) + '\n')
            entries['levels'][level] = summarize(rows, entries['levels'].get('clean') if level != 'clean' else None)
            entries['levels'][level]['raw_sha256'] = digest(output)
            (a.out / 'summary.json').write_text(json.dumps(report, indent=2) + '\n')
            print(job['id'], level, entries['levels'][level]['first_stop_m'], flush=True)


if __name__ == '__main__':
    for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
        os.environ.setdefault(variable, '1')
    main()
