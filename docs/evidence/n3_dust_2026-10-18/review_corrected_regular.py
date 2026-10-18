"""Independent read-only review of completed corrected regular dust captures.

No detector is imported or run. Rebuild association arithmetic from serialized
detections and original labels, and separately check recorded source samples.
"""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
CACHE = Path('/home/resense/data/decoded')
DETECTOR = '9b92df56e802d9d63f83f2fc5e5b07374db669c7'
HARNESS = 'b9ad5f4348e1ffd882bb6a503961a9768384c416'
FOLDERS = ('baseline_pose_fixed', 'dark_baseline_pose_fixed', 'dark_health_pose_fixed',
           'health_platform_pose_fixed')


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def git_sha(commit, name):
    return hashlib.sha256(subprocess.check_output(['git', 'show', f'{commit}:{name}'], cwd=ROOT)).hexdigest()


def associate(detections, labels):
    if not detections or not labels:
        return {}
    missing = 2 * min(len(detections), len(labels)) + 1
    costs = np.full((len(labels), len(detections) + len(labels)), float(missing))
    costs[:, :len(detections)] = 1e6
    for i, label in enumerate(labels):
        distance, lateral = float(label['distance']), float(label.get('lateral', 0))
        tolerance = max(2, .03 * distance) + .5 * max(label.get('size', [.5])[0], 0)
        for j, detection in enumerate(detections):
            dx = abs(float(detection['distance']) - distance)
            dy = abs(float(detection['lateral']) - lateral)
            if dx <= tolerance and dy <= 1:
                costs[i, j] = dx / tolerance + dy
    ii, jj = linear_sum_assignment(costs)
    return {int(i): int(j) for i, j in zip(ii, jj) if j < len(detections) and costs[i, j] < missing}


def source_sample(bag, index, meta, labels, dark, reference):
    path = CACHE / bag / f'f_{index:05d}.npz'
    with np.load(path) as arrays:
        # The pinned baseline config has forward=-y, left=+x, up=+z and no fixed rotations.
        xyz = arrays['xyz'] @ np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]], dtype=np.float32).T
        intensity = arrays['inten'].copy()
        ring = arrays['ring'] if meta['has_ring'] else None
        if dark:
            for label in labels:
                if label.get('bbox') is not None and label.get('n_points', 1) > 0:
                    lo, hi = np.asarray(label['bbox'])
                    intensity[((xyz >= lo) & (xyz <= hi)).all(axis=1)] = 1.
        digest = hashlib.sha256()
        for name, array in [('xyz', xyz), ('intensity', intensity), ('ring', ring)]:
            digest.update(name.encode())
            if array is None:
                digest.update(b'None')
            else:
                digest.update(str((array.dtype.str, array.shape)).encode())
                digest.update(array.tobytes(order='C'))
        digest.update(canonical_sha({'stamp': meta['stamp'], 'frame_id': meta['frame_id'],
                      'meta': {'n_raw': meta['n_raw'], 'n_near': meta['n_near']}}).encode())
        assert digest.hexdigest() == reference['source_frame_sha256']
    return {'bag': bag, 'frame': index, 'dark_intervention': dark, 'cache_sha256': sha(path),
            'source_frame_sha256': digest.hexdigest()}


def main():
    outputs, captures, inputs, samples = {}, {}, {}, []
    max_height_rounding = 0.
    total_rows = 0
    for folder in FOLDERS:
        directory = HERE / folder
        verified, summary = read(directory / 'verified_complete.json'), read(directory / 'summary.json')
        assert verified['complete'] and sha(directory / 'summary.json') == verified['summary_sha256']
        assert sha(HERE / 'summarize_regular_dust.py') == verified['script_sha256']
        assert summary['commit'] == HARNESS and summary['native_enabled'] is True
        assert summary['config_overrides'] == [] and not summary['dust_support'] and summary['seed'] == 20261018
        assert summary['runtime_identity_start'] == summary['runtime_identity_end'] == verified['runtime_identity']
        detector_root = Path(summary['detector_root'])
        for name, digest in summary['source_hashes'].items():
            assert sha(detector_root / name) == git_sha(DETECTOR, name) == digest
        for filename, digest in verified['runtime_identity'].items():
            path = Path(filename)
            assert sha(path) == digest
            if 'harness_b9ad5f4' in filename:
                assert git_sha(HARNESS, filename.split('harness_b9ad5f4/', 1)[1]) == digest
        inputs[str(directory / 'verified_complete.json')] = sha(directory / 'verified_complete.json')
        inputs[str(directory / 'summary.json')] = sha(directory / 'summary.json')
        folder_result, captures[folder] = {}, {}
        for bag, record in verified['recordings'].items():
            metadata = read(CACHE / bag / 'meta.json')
            assert sha(CACHE / bag / 'meta.json') == record['metadata_sha256_at_verification']
            label_path = ROOT / 'labels' / f'{bag}.json'
            labels = read(label_path) if label_path.exists() else {}
            if labels:
                assert sha(label_path) == verified['label_sha256'][bag]
                inputs[str(label_path)] = sha(label_path)
            references, bag_result, captures[folder][bag] = [], {}, {}
            for level, level_summary in record['levels'].items():
                raw = directory / f'{bag}_{level}.jsonl.gz'
                assert sha(raw) == level_summary['raw_sha256']
                inputs[str(raw)] = sha(raw)
                with gzip.open(raw, 'rt') as stream:
                    rows = [json.loads(line) for line in stream]
                captures[folder][bag][level] = rows
                assert len(rows) == record['frames_per_level'] == len(metadata)
                total_rows += len(rows)
                counts, stop, degraded, objects, unmatched = Counter(), [], [], defaultdict(lambda: defaultdict(list)), []
                for i, row in enumerate(rows):
                    assert row['frame'] == i and row['stamp'] == metadata[i]['stamp']
                    assert type(row['obstacle']) is bool and row['obstacle'] == bool(row['detections'])
                    health = row['health']
                    degree = health.get('decision_level', health['level'])
                    decision = ('STOP' if row['obstacle'] else 'FAULT' if health['level'] == 'error' else
                                'CAUTION' if row['warning'] or degree == 'warn' else 'GO')
                    assert decision == row['decision']
                    counts[decision] += 1
                    if decision == 'STOP':
                        stop.append(i)
                    if degree in ('warn', 'error'):
                        degraded.append(i)
                    reference = row['clean_reference']
                    assert canonical_sha({k: v for k, v in reference.items() if k != 'reference_sha256'}) == reference['reference_sha256']
                    rotation = np.asarray(reference['input_to_model_rotation'])
                    assert np.allclose(rotation @ rotation.T, np.eye(3), atol=3e-7, rtol=0)
                    assert np.isclose(np.linalg.det(rotation), 1, atol=3e-7, rtol=0)
                    if level == 'clean':
                        assert row['augmentation'] is None
                        references.append(reference)
                        track = row['track']
                        x = np.clip(20., *track['floor_range'])
                        a, b, c = track['floor_coef']
                        rail = (a*x+b)*x+c+(2*a*x+b)*(20-x)+track['rail_offset']
                        error = abs(rail-reference['rail_z_at20'])
                        assert error <= .000501  # Serialized rail_offset rounds to .001 m.
                        max_height_rounding = max(max_height_rounding, error)
                        if bag in ('doubleT_obstacle', 'doubleT_platform') and i in (0, 8, len(rows)-1):
                            samples.append(source_sample(bag, i, metadata[i], labels.get(f'{i:05d}', []),
                                                         verified['scope']['dark'], reference))
                    else:
                        audit = row['augmentation']
                        assert reference == references[i] == audit['placement_reference']
                        assert audit['rail_z'] == reference['rail_z_at20']
                        assert audit['seed'] == 20261018 and audit['frame_index'] == i
                        density, extinction = {'low': (.1, .0005), 'medium': (1., .003), 'high': (10., .02)}[level]
                        assert audit['spec'] == {'density': density, 'extinction': extinction,
                            'x_bounds': [2.5, 60.], 'y_bounds': [-3., 3.], 'height_bounds': [.1, 3.5], 'intensity_max': 5.}
                        assert row['n_points'] == audit['source_points'] - audit['removed_returns'] + audit['added_returns']
                    visible = [label for label in labels.get(f'{i:05d}', []) if label.get('n_points', 1) > 0 and label.get('plausible', True)]
                    pairs = associate(row['detections'], visible)
                    assert sorted(visible[k].get('label', 'obstacle') for k in pairs) == sorted(row['matched_labels'])
                    if len(pairs) < len(row['detections']):
                        unmatched.append(i)
                    for k, label in enumerate(visible):
                        relation = label.get('in_gauge', True)
                        relation = 'inside' if relation is True else 'outside' if relation is False else 'unknown'
                        name = label.get('label', 'obstacle')
                        if k in pairs:
                            objects[name][relation].append(i)
                assert dict(counts) == level_summary['counts'] and stop == level_summary['stop_frames']
                assert degraded == level_summary['degraded_frames'] and unmatched == level_summary['unmatched_stop_frames']
                episodes = sum(i == 0 or value != stop[i-1]+1 for i, value in enumerate(stop))
                assert episodes == level_summary['stop_episodes']
                compact_objects = {}
                for name, result in level_summary['objects'].items():
                    for relation in ('inside', 'outside', 'unknown'):
                        assert objects[name][relation] == result[f'{relation}_matched_stop_frames']
                    all_matches = sorted(i for relation in ('inside', 'outside', 'unknown') for i in objects[name][relation])
                    assert all_matches == result['matched_stop_frames']
                    for matches, frame_key, range_key in ((all_matches, 'first_stop_frame', 'first_stop_m'),
                            (objects[name]['inside'], 'first_inside_stop_frame', 'first_inside_stop_m')):
                        first = matches[0] if matches else None
                        assert first == result[frame_key]
                        distance = (next(float(label['distance']) for label in labels[f'{first:05d}']
                                    if label.get('label', 'obstacle') == name) if first is not None else None)
                        assert distance == result[range_key]
                    if level != 'clean':
                        clean = record['levels']['clean']['objects'][name]
                        for relation in ('inside', 'outside', 'unknown'):
                            old = set(clean[f'{relation}_matched_stop_frames'])
                            new = set(objects[name][relation])
                            assert sorted(old-new) == result[f'lost_clean_{relation}_stop_frames']
                            assert sorted(new-old) == result[f'new_{relation}_stop_frames']
                        for range_key, ratio_key in (('first_stop_m', 'first_stop_ratio'),
                                                     ('first_inside_stop_m', 'first_inside_stop_ratio')):
                            ratio = result[range_key]/clean[range_key] if clean[range_key] and result[range_key] is not None else None
                            assert ratio == result[ratio_key]
                    compact_objects[name] = {relation: len(objects[name][relation]) for relation in ('inside', 'outside', 'unknown')}
                    compact_objects[name]['first_inside_stop_m'] = result['first_inside_stop_m']
                if level != 'clean':
                    extra = episodes-record['levels']['clean']['stop_episodes']
                    assert extra == level_summary['extra_stop_episodes']
                    if 'empty_episode_acceptance' in level_summary:
                        assert (extra <= 1) == level_summary['empty_episode_acceptance']
                bag_result[level] = {'counts': dict(counts), 'stop_episodes': episodes, 'degraded_frames': len(degraded),
                                     'unmatched_detection_frames': len(unmatched), 'objects': compact_objects}
            folder_result[bag] = bag_result
        outputs[folder] = folder_result

    parity = {}
    for before, after, bag in [('dark_baseline_pose_fixed', 'dark_health_pose_fixed', 'doubleT_obstacle'),
                               ('baseline_pose_fixed', 'health_platform_pose_fixed', 'doubleT_platform')]:
        for level, rows in captures[after][bag].items():
            controls = captures[before][bag][level]
            assert len(rows) == len(controls)
            for left, right in zip(controls, rows):
                excluded = {'health', 'clear_distance', 'timing_ms', 'decision'}
                assert {k:v for k,v in left.items() if k not in excluded} == {k:v for k,v in right.items() if k not in excluded}
            parity[f'{after}/{level}'] = {'rows': len(rows), 'all_other_serialized_fields_exact': True}
    assert total_rows == 18635 and len(parity) == 7
    result = {'status': 'COMPLETED_CORRECTED_EVIDENCE_VERIFIED_ACCEPTANCE_FAIL',
              'checked_utc': datetime.now(timezone.utc).isoformat(), 'detector_commit': DETECTOR,
              'harness_commit': HARNESS, 'frames_rechecked': total_rows, 'raw_files_rechecked': 39,
              'results': outputs, 'health_only_parity': parity, 'source_samples': samples,
              'max_serialized_rail_height_rounding_error_m': max_height_rounding,
              'input_sha256': {**inputs, str(Path(__file__)): sha(Path(__file__)),
                               str(HERE / 'summarize_regular_dust.py'): sha(HERE / 'summarize_regular_dust.py')},
              'limits': [f'No detector rerun; exact original source payload hashing sampled {len(samples)} frame/intervention combinations, not an independent rehash of every NPZ.',
                         'Association uses recorded distance/lateral tolerances and legacy per-frame gauge labels; it is not surveyed truth.',
                         'Pinned9b detector and b9 harness, not a new selected-cecab stress test.',
                         'Frozen flat clean rail_z(20m) placement is synthetic; actual physical dust remains unvalidated.',
                         'Health-only experiment is not enabled production behavior and does not recover missed objects.']}
    (HERE / 'independent_corrected_regular_review.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','frames_rechecked','raw_files_rechecked')}))


if __name__ == '__main__':
    main()
