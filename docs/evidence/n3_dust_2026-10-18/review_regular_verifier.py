"""Independent verifier probes on artificial three-frame inputs; no detector calls."""
from __future__ import annotations

import argparse
from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = Path('/home/resense/data/n2/baseline_9b92df5')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, separators=(',', ':')) + '\n')


def write_raw(path, rows):
    with gzip.open(path, 'wt') as stream:
        for row in rows:
            stream.write(json.dumps(row, separators=(',', ':')) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contradiction-only', action='store_true')
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT))
    import numpy as np
    from resense.config import DetectorConfig
    from resense.frame import Frame, axis_matrix
    from scripts.dust_reference import _digest, source_frame_sha256
    spec = importlib.util.spec_from_file_location('regular_verifier_under_review', HERE / 'summarize_regular_dust.py')
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    results = {}
    with (tempfile.TemporaryDirectory(prefix='regular_verifier_review_') as temporary,
          tempfile.TemporaryDirectory(prefix='review_fixture_', dir='/home/resense/data/decoded') as cache_name):
        folder, cache = Path(temporary), Path(cache_name)
        verifier.ROOT = folder
        (folder / 'labels').mkdir()
        bag = cache.name
        verifier.FRAME_COUNTS[bag] = 3
        labels = {f'{i:05d}': [{'label': 'person_crossing', 'distance': d, 'lateral': 0., 'n_points': 1,
                              'plausible': True, 'in_gauge': i > 0}] for i, d in enumerate((110., 50., 40.))}
        save(folder / 'labels' / f'{bag}.json', labels)
        metadata = [{'stamp': 100 + i * .1, 'frame_id': 'probe', 'has_ring': False, 'n_raw': 1, 'n_near': 0} for i in range(3)]
        save(cache / 'meta.json', metadata)
        rotation = axis_matrix(DetectorConfig.from_yaml(str(SOURCE / 'configs/default.yaml')).sensor).astype(np.float32)
        references = []
        for i, meta in enumerate(metadata):
            xyz, intensity = np.array([[10., 0., -1.]], np.float32), np.array([15.], np.float32)
            np.savez_compressed(cache / f'f_{i:05d}.npz', xyz=xyz, inten=intensity)
            frame = Frame(xyz @ rotation.T, intensity, None, meta['stamp'], 'probe', {'n_raw': 1, 'n_near': 0})
            ref = {'schema': 'dust-clean-reference-v1', 'input_to_model_rotation': np.eye(3).tolist(),
                   'rail_z_at20': -1.5, 'source_frame_sha256': source_frame_sha256(frame)}
            ref['reference_sha256'] = _digest(ref)
            references.append(ref)
        cache_digest = hashlib.sha256((cache / 'meta.json').read_bytes())
        for path in sorted(cache.glob('f_*.npz')):
            cache_digest.update(path.name.encode())
            cache_digest.update(bytes.fromhex(sha(path)))
        identity_paths = [ROOT / 'scripts/dust_reference.py', ROOT / 'resense/dust.py', SOURCE / 'configs/default.yaml']
        identity = {str(path): sha(path) for path in identity_paths}
        report = {'schema': 'dust-battery-v2', 'native_enabled': True, 'seed': 20261018, 'config_overrides': [],
                  'dust_support': False, 'health_only': False, 'dim_label_intensity': None,
                  'runtime_identity_start': identity, 'runtime_identity_end': identity, 'detector_root': str(SOURCE),
                  'source_hashes': {'resense/metrics.py': sha(SOURCE / 'resense/metrics.py')},
                  'generator_sha256': sha(ROOT / 'resense/dust.py'), 'recordings': {bag: {'frames': 3,
                      'labels_sha256': sha(folder / 'labels' / f'{bag}.json'), 'cache_sha256': cache_digest.hexdigest(), 'levels': {}}}}
        original_rows = {}
        for level, (density, extinction) in zip(verifier.LEVELS, ((0., 0.), (.1, .0005), (1., .003), (10., .02))):
            hits = {0, 1, 2} if level in ('clean', 'medium') else {0, 2} if level == 'low' else set()
            rows = []
            for i, ref in enumerate(references):
                audit = None if level == 'clean' else {'seed': 20261018, 'frame_index': i, 'rail_z': -1.5,
                    'placement_reference': ref, 'spec': {'density': density, 'extinction': extinction,
                        'x_bounds': [2.5, 60.], 'y_bounds': [-3., 3.], 'height_bounds': [.1, 3.5], 'intensity_max': 5.}}
                distance = labels[f'{i:05d}'][0]['distance']
                rows.append({'frame': i, 'stamp': metadata[i]['stamp'], 'obstacle': i in hits, 'warning': False,
                             'decision': 'STOP' if i in hits else 'GO', 'health': {'level': 'ok', 'decision_level': 'ok'},
                             'clean_reference': ref, 'augmentation': audit,
                             'detections': [{'distance': distance, 'lateral': 0.}] if i in hits else [],
                             'matched_labels': ['person_crossing'] if i in hits else []})
            original_rows[level] = rows
            path = folder / f'{bag}_{level}.jsonl.gz'
            write_raw(path, rows)
            inside = sorted(hits & {1, 2})
            report['recordings'][bag]['levels'][level] = {'frames': 3, 'raw_sha256': sha(path), 'STOP': len(hits),
                'GO': 3 - len(hits), 'stop_episodes': sum(i - 1 not in hits for i in hits), 'degraded_frames': 0,
                'objects': {'person_crossing': {'stop_frames': inside, 'first_stop_frame': inside[0] if inside else None,
                                               'first_stop_m': labels[f'{inside[0]:05d}'][0]['distance'] if inside else None}}}
        save(folder / 'summary.json', report)
        verified = verifier.verify(folder, (bag,))
        obj = verified['recordings'][bag]['levels']['low']['objects']['person_crossing']
        assert obj['first_stop_ratio'] == 1. and obj['first_inside_stop_ratio'] == .8
        assert obj['lost_clean_inside_stop_frames'] == [1] and obj['lost_clean_outside_stop_frames'] == []
        results['unaltered_artificial_fixture'] = 'accepted; first-any ratio1.0 and first-inside ratio0.8 remain distinct'
        cases = (('confirmed_detection_contradiction',) if args.contradiction_only else
                 ('summary_count', 'inside_first_distance', 'raw_match', 'wrong_reference_source', 'changed_level_reference', 'wrong_density', 'truncated_raw'))
        for case in cases:
            altered = deepcopy(report)
            rows = deepcopy(original_rows['low' if case in ('changed_level_reference', 'wrong_density') else 'clean'])
            level = 'low' if case in ('changed_level_reference', 'wrong_density') else 'clean'
            if case == 'summary_count':
                altered['recordings'][bag]['levels']['clean']['STOP'] += 1
            elif case == 'inside_first_distance':
                altered['recordings'][bag]['levels']['clean']['objects']['person_crossing']['first_stop_m'] = 110.
            elif case == 'raw_match':
                rows[0]['matched_labels'] = []
            elif case == 'wrong_reference_source':
                rows[0]['clean_reference']['source_frame_sha256'] = 'f' * 64
                payload = {k: v for k, v in rows[0]['clean_reference'].items() if k != 'reference_sha256'}
                rows[0]['clean_reference']['reference_sha256'] = _digest(payload)
            elif case == 'changed_level_reference':
                rows[0]['clean_reference']['rail_z_at20'] = -2.
                payload = {k: v for k, v in rows[0]['clean_reference'].items() if k != 'reference_sha256'}
                rows[0]['clean_reference']['reference_sha256'] = _digest(payload)
            elif case == 'wrong_density':
                rows[0]['augmentation']['spec']['density'] = 0.
            elif case == 'confirmed_detection_contradiction':
                rows[0]['obstacle'] = False
                rows[0]['decision'] = 'GO'
                altered['recordings'][bag]['levels']['clean']['STOP'] -= 1
                altered['recordings'][bag]['levels']['clean']['GO'] += 1
            else:
                rows.pop()
            path = folder / f'{bag}_{level}.jsonl.gz'
            write_raw(path, rows)
            altered['recordings'][bag]['levels'][level]['raw_sha256'] = sha(path)
            save(folder / 'summary.json', altered)
            try:
                verifier.verify(folder, (bag,))
            except ValueError as error:
                results[case] = str(error)
            else:
                raise AssertionError(f'tampered fixture accepted: {case}')
            write_raw(path, original_rows[level])
            report['recordings'][bag]['levels'][level]['raw_sha256'] = sha(path)
    output = {'scope': 'Artificial3-frame cache/schema fixture, no detector processing and no measured-data claim.',
              'verifier_sha256': sha(HERE / 'summarize_regular_dust.py'), 'probe_sha256': sha(Path(__file__)), 'outcomes': results}
    output['mode'] = 'contradiction_only' if args.contradiction_only else 'historical_suite'
    if args.contradiction_only:
        output['mutation'] = 'Keep confirmed detections and matches; set obstacle=false and decision=GO, recompute summary counts and update raw SHA.'
        output['prior_suite_receipt_sha256'] = sha(HERE / 'independent_regular_verifier_probes.json')
    save(HERE / ('independent_regular_contradiction_probe.json' if args.contradiction_only else 'independent_regular_verifier_probes.json'), output)
    print(json.dumps(output, indent=2))


if __name__ == '__main__':
    main()
