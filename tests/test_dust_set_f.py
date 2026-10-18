"""Frozen Set F geometry and per-frame stress accounting contracts."""
import json
from dataclasses import asdict

import numpy as np
import pytest

from resense.config import DetectorConfig
from resense.frame import Frame
from scripts.dust_set_f import (canonical_jobs, frame_hash, json_default, prepare_sequence,
                                render_frozen, same_json, sequence_path, summarize, without_truth)


def test_canonical_jobs_keep_complete_gate_seed_schedule():
    jobs = list(canonical_jobs())
    assert len(jobs) == 30 and jobs == list(canonical_jobs())
    assert len({job['id'] for job in jobs}) == 30
    assert [job['kind'] for job in jobs[:5]] == ['person', 'box1.0', 'box0.5', 'trolley', 'cable']
    rng = np.random.default_rng(0)
    assert jobs[0]['reflectivity'] == rng.uniform(10, 60)
    assert jobs[0]['lateral'] == rng.uniform(-.6, .6)
    assert jobs[0]['render_seed'] == rng.integers(1 << 30)


def test_resumable_provenance_survives_json_tuple_roundtrip():
    config = asdict(DetectorConfig())
    loaded = json.loads(json.dumps(config))
    assert same_json(config, loaded)
    loaded['sensor']['max_range'] += 1
    assert not same_json(config, loaded)


def test_path_requires_timestamps_and_stops_at_original_near_boundary():
    files = ['a.npy', 'b.npy', 'c.npy']
    with pytest.raises(ValueError, match='missing source timestamp'):
        sequence_path(files, {'a': 0.}, [1., 1., 1.])
    with pytest.raises(ValueError, match='discontinuous'):
        sequence_path(files, {'a': 0., 'b': 0., 'c': .2}, [1., 1., 1.])
    path = sequence_path(files, {'a': 0., 'b': .1, 'c': .2}, [20., 20., 20.], 10.)
    assert [row[3] for row in path] == [10., 8.]


def test_oracle_metadata_is_removed_without_modifying_input():
    frame = Frame(np.zeros((2, 3), np.float32), np.ones(2, np.float32),
                  meta={'n_raw': 2, 'obstacles': [{'distance': 20}]})
    clean = without_truth(frame)
    assert clean.meta == {'n_raw': 2} and 'obstacles' in frame.meta
    assert frame_hash(clean) == frame_hash(frame)


def test_lost_positive_and_false_episode_accounting_are_per_frame():
    def rows(hits, false_frames):
        return [{'index': i, 'distance': 50 - i, 'hit': i in hits,
                 'false_detections': int(i in false_frames), 'clean_returns': 2,
                 'retained_object_returns': 0 if i == 1 else 2,
                 'decision': 'STOP' if i in hits or i in false_frames else 'CAUTION',
                 'degraded': True} for i in range(5)]
    clean = summarize(rows({0, 1, 2, 3}, set()))
    dusty = summarize(rows({0, 1, 3}, {0, 1, 3}), clean)
    assert dusty['lost_clean_stop_frames'] == [2]
    assert dusty['false_stop_episodes'] == 2
    assert dusty['observed_hit_frames'] == [0, 3]
    assert 1 in dusty['hit_frames']  # complete attenuation does not erase physical truth


def test_full_precision_bank_roundtrip_reproduces_injected_points(synth_npy_dir):
    from scripts.dust_reference import source_frame_sha256, _validated_rotation
    files = sorted(str(path) for path in synth_npy_dir.glob('*.npy'))
    stamps = {path.rsplit('/', 1)[-1][:-4]: .1 * i for i, path in enumerate(files)}
    cfg = DetectorConfig()
    bank = prepare_sequence(files, stamps, [1., 1.], next(canonical_jobs()), cfg, start_distance=25.)
    bank = json.loads(json.dumps(bank, default=json_default))
    assert any(row['clean_returns'] > 0 for row in bank['frames'])
    for row in bank['frames']:
        rendered, _, _ = render_frozen(row, bank, synth_npy_dir, cfg)
        assert frame_hash(rendered.frame) == row['clean_frame_sha256']
        assert row['dust_reference']['source_frame_sha256'] == source_frame_sha256(without_truth(rendered.frame))
        assert row['dust_reference']['rail_z_at20'] == row['rail_z']
        _validated_rotation(row['dust_reference'])
    bank['render_seed'] += 1
    with pytest.raises(ValueError, match='rendering drift'):
        render_frozen(bank['frames'][0], bank, synth_npy_dir, cfg)
