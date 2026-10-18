"""Compare complete clean captures and independently rebuild frozen source hashes."""
from __future__ import annotations

from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean_semantics(row):
    result = deepcopy(row)
    result.pop('timing_ms')
    result.pop('clean_reference', None)
    result['health'].pop('latency_p95_ms')
    return result


def main():
    old_dir, new_dir = HERE / 'baseline', HERE / 'baseline_pose_fixed'
    bag = 'doubleT_platform'
    before, after = (json.loads((folder / 'summary.json').read_text()) for folder in (old_dir, new_dir))
    entry = after['recordings'][bag]['levels']['clean']
    assert entry['frames'] == before['recordings'][bag]['levels']['clean']['frames'] == 345
    assert after['schema'] == 'dust-battery-v2' and after['native_enabled'] is True
    identity = after['runtime_identity_start']
    assert identity == after['runtime_identity_end']
    assert all(sha(Path(path)) == digest for path, digest in identity.items())
    assert any(path.endswith('.so') for path in identity)
    assert before['source_hashes'] == after['source_hashes']
    assert before['recordings'][bag]['cache_sha256'] == after['recordings'][bag]['cache_sha256']
    paths = [folder / f'{bag}_clean.jsonl.gz' for folder in (old_dir, new_dir)]
    rows = []
    for folder, report, path in zip((old_dir, new_dir), (before, after), paths):
        assert sha(path) == report['recordings'][bag]['levels']['clean']['raw_sha256']
        rows.append([json.loads(line) for line in gzip.open(path, 'rt')])
    assert [len(value) for value in rows] == [345, 345]
    differences, timing_health = [], []
    for i, pair in enumerate(zip(*rows)):
        left, right = (clean_semantics(row) for row in pair)
        if left != right:
            differences.append(i)
        old_health, new_health = left.pop('health'), right.pop('health')
        assert left == right, f'non-health clean detector drift: {i}'
        old_level, new_level = old_health.pop('level'), new_health.pop('level')
        old_messages, new_messages = old_health.pop('messages'), new_health.pop('messages')
        prefix = 'latency p95 '
        assert old_health == new_health
        assert [m for m in old_messages if not m.startswith(prefix)] == [m for m in new_messages if not m.startswith(prefix)]
        if old_level != new_level:
            assert old_level == 'ok' and new_level == 'warn' and any(m.startswith(prefix) for m in new_messages)
        if old_level != new_level or old_messages != new_messages:
            timing_health.append({'frame': i, 'before_level': old_level, 'after_level': new_level,
                                  'before_messages': old_messages, 'after_messages': new_messages,
                                  'before_latency_p95_ms': pair[0]['health']['latency_p95_ms'],
                                  'after_latency_p95_ms': pair[1]['health']['latency_p95_ms']})
    source = Path(after['detector_root'])
    sys.path.insert(0, str(source))
    import numpy as np
    from resense.config import DetectorConfig
    from resense.frame import Frame, axis_matrix
    helper_path = next(Path(path) for path in identity if path.endswith('/scripts/dust_reference.py'))
    spec = importlib.util.spec_from_file_location('recorded_clean_helper', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    cfg = DetectorConfig.from_yaml(str(source / 'configs/default.yaml'))
    rotation = axis_matrix(cfg.sensor).astype(np.float32)
    cache = Path('/home/resense/data/decoded') / bag
    metadata_path = cache / 'meta.json'
    metadata = json.loads(metadata_path.read_text())
    digest = hashlib.sha256(metadata_path.read_bytes())
    source_mismatches = []
    for i, (row, meta) in enumerate(zip(rows[1], metadata)):
        assert row['frame'] == i and row['stamp'] == meta['stamp'] and row['augmentation'] is None
        path = cache / f'f_{i:05d}.npz'
        digest.update(path.name.encode())
        digest.update(bytes.fromhex(sha(path)))
        with np.load(path) as data:
            frame = Frame(data['xyz'] @ rotation.T, data['inten'], data['ring'] if meta['has_ring'] else None,
                          meta['stamp'], meta['frame_id'], {'n_raw': meta['n_raw'], 'n_near': meta['n_near']})
        reference = row['clean_reference']
        helper._validated_rotation(reference)
        if helper.source_frame_sha256(frame) != reference['source_frame_sha256']:
            source_mismatches.append(i)
        track = row['track']
        x = np.clip(20., *track['floor_range'])
        z = np.polyval(track['floor_coef'], x) + np.polyval(np.polyder(track['floor_coef']), x) * (20. - x) + track['rail_offset']
        assert abs(z - reference['rail_z_at20']) <= .0005000001
    assert not source_mismatches
    assert digest.hexdigest() == after['recordings'][bag]['cache_sha256']
    result = {'scope': 'Complete345 clean platform frames. No detector rerun. Detector decisions/ranges/geometry exact; concurrent-load latency warnings change health level/messages and remain explicit.',
              'before_sha256': sha(paths[0]), 'after_sha256': sha(paths[1]), 'source_hashes_equal': True,
              'native_enabled': after['native_enabled'], 'native_description': after['native_description'],
              'runtime_identity': identity, 'raw_frames': 345, 'strict_non_timing_semantic_mismatch_frames': differences,
              'strict_non_timing_json_equal': not differences, 'non_health_detector_mismatches': [],
              'health_except_latency_messages_and_level_mismatches': [],
              'timing_derived_health_changes': timing_health,
              'excluded_fields': ['timing_ms', 'health.latency_p95_ms'],
              'new_audit_field_separately_verified': 'clean_reference',
              'independently_rebuilt_source_hashes': 345, 'source_mismatches': source_mismatches,
              'cache_sha256': digest.hexdigest(), 'reference_checks': 'Proper finite rotation, reference digest, full configured-input frame identity; clean rail height consistent within0.5mm serialization rounding.',
              'review_script_sha256': sha(Path(__file__))}
    (HERE / 'independent_corrected_clean_comparison.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
