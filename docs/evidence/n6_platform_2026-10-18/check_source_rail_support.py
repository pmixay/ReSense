#!/usr/bin/env python3
"""Probe N6 rail support against exact source clouds without altering the candidate."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import asdict, replace
from pathlib import Path

for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(name, '1')
ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(os.environ.get('RESENSE_REPO', '/home/resense/data/n6/source_745096f'))
os.environ['RESENSE_REPO'] = str(SOURCE)
sys.path.insert(0, str(SOURCE))
sys.path.insert(0, str(ROOT / 'docs/evidence/judgement_2026-10-13/scripts'))
import numpy as np  # noqa: E402
from judge_runner import NodeReplica, record  # noqa: E402
from range_test import run_frame  # noqa: E402
from resense import track  # noqa: E402
from resense.farrails import FarRailParams, far_rails  # noqa: E402

EVIDENCE = Path(__file__).parent
CACHE = Path('/home/resense/data/decoded')
LABELS = ROOT / 'docs/evidence/n5_labels_2026-10-17/labels_synthetic_platform.json'
CAPTURE = Path('/home/resense/data/n6/synthetic_platform_candidate_v3.jsonl')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plain(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(type(value).__name__)


def without_timing(row):
    return {key: value for key, value in row.items()
            if key not in ('level', 'msgs', 'total_ms', 'timing_ms')}


def main():
    meta = json.loads((CACHE / 'synthetic_platform/meta.json').read_text())
    reference_meta = json.loads((CACHE / 'cloud_with_fake_obj/meta.json').read_text())
    labels = json.loads(LABELS.read_text())
    expected = [json.loads(line) for line in CAPTURE.read_text().splitlines()]
    rep = NodeReplica(overrides={'track.rails_axis_extension': True})
    original = track._extend_axis_from_rails
    rows, mismatches, current, source_hashes = [], [], {}, {}
    code_hashes = {name: digest(SOURCE / name) for name in
                   ('resense/track.py', 'resense/detector.py', 'resense/config.py', 'resense/farrails.py')}

    def probe(xyz, model, cfg, near, ring):
        prior = replace(model)
        original(xyz, model, cfg, near, ring)
        if not model.rail_axis_support:
            return
        i = current['frame']
        if not np.array_equal(rep.detector.calib.R, np.eye(3)):
            raise AssertionError('expected validated identity mount in platform reference interval')
        source_path = CACHE / f'cloud_with_fake_obj/f_{i + 1195:05d}.npz'
        with np.load(source_path) as source:
            source_xyz = source['xyz'] @ rep.R_vs.T
            source_ring = source['ring'].copy() if reference_meta[i + 1195]['has_ring'] else None
        source_hashes[str(source_path)] = digest(source_path)
        if abs(reference_meta[i + 1195]['stamp'] - meta[i]['stamp']) > 1e-6:
            raise AssertionError('exact source stamp mismatch')
        source_members = {point.tobytes() for point in np.ascontiguousarray(source_xyz)}
        keep_exact = np.array([point.tobytes() in source_members for point in np.ascontiguousarray(xyz)])
        keep_boxes = np.ones(xyz.shape[0], dtype=bool)
        for obj in labels[f'{i:05d}']:
            low, high = np.asarray(obj['bbox'], dtype=float)
            keep_boxes &= ~np.all((xyz >= low - 0.02) & (xyz <= high + 0.02), axis=1)
        source_near = track.estimate_rails(source_xyz, prior, cfg, prior.center, prior=prior)
        params = FarRailParams(x_max=80.0, gauge=cfg.rails_spacing, height_band=0.3, cant=0.1,
                               max_gap=10.0, min_stations=3, pair_max_forward_gap=5.0,
                               pair_use_nearer_forward=True)
        variants = {}
        for name, points, rings, seed in (
                ('synthetic', xyz, ring, near),
                ('source_same_near', source_xyz, source_ring, near),
                ('shared_returns_source_near', xyz[keep_exact], ring[keep_exact], source_near),
                ('exact_new_returns_removed', xyz[keep_exact], ring[keep_exact], near),
                ('label_boxes_removed', xyz[keep_boxes], ring[keep_boxes], near)):
            result = replace(prior)
            original(points, result, cfg, seed, rings)
            paired = (far_rails(points, rings, prior, (float(seed.xm[-1]), float(seed.mids[-1])), params)
                      if rings is not None else None)
            variants[name] = {'axis_valid': result.axis_valid,
                              'rail_axis_support': result.rail_axis_support,
                              'accepted_station_x': paired.x.tolist() if paired is not None else [],
                              'accepted_station_y': paired.y.tolist() if paired is not None else [],
                              'station_axis_residual_m': (paired.y - prior.center_y(paired.x)).tolist() if paired is not None else [],
                              'supplied_ring_available': rings is not None,
                              'near_score': seed.score, 'near_slabs': seed.n_slabs,
                              'near_seed': [float(seed.xm[-1]), float(seed.mids[-1])]}
        rows.append({'frame': i, 'source_frame': i + 1195, 'pre_extension_model': asdict(prior),
                     'near_fit': asdict(near), 'removed_exact_returns': int((~keep_exact).sum()),
                     'removed_box_returns': int((~keep_boxes).sum()), 'variants': variants})
        print(f'probe frame {i} support ' + str({key: round(val['rail_axis_support'], 3)
                                               for key, val in variants.items()}), flush=True)

    track._extend_axis_from_rails = probe
    try:
        for i in range(315):
            current['frame'] = i
            path = CACHE / f'synthetic_platform/f_{i:05d}.npz'
            source_hashes[str(path)] = digest(path)
            with np.load(path) as data:
                result = run_frame(rep, data['xyz'], data['inten'], data['ring'], meta[i], i)
            row = record(i, meta[i]['bag_t'], meta[i]['stamp'], result, 0., 0.,
                         meta[i]['frame_id'], meta[i]['topic'])
            row['model'] = result.track.to_dict()
            if without_timing(row) != without_timing(expected[i]):
                mismatches.append(i)
    finally:
        track._extend_axis_from_rails = original
    variants = ('source_same_near', 'shared_returns_source_near', 'exact_new_returns_removed', 'label_boxes_removed')
    summary = {key: {'extension_lost_frames': [], 'support_changed_frames': [],
                     'support_lower_frames': [], 'minimum_support_delta_m': None, 'original_stations_missing_frames': []} for key in variants}
    for key in variants:
        delta = []
        for row in rows:
            a, b = row['variants']['synthetic'], row['variants'][key]
            d = b['rail_axis_support'] - a['rail_axis_support']
            delta.append(d)
            if any(not any(abs(x - xx) < 1e-7 and abs(y - yy) < 1e-7
                           for xx, yy in zip(b['accepted_station_x'], b['accepted_station_y']))
                   for x, y in zip(a['accepted_station_x'], a['accepted_station_y'])):
                summary[key]['original_stations_missing_frames'].append(row['frame'])
            if b['rail_axis_support'] <= 0:
                summary[key]['extension_lost_frames'].append(row['frame'])
            if abs(d) > 1e-7:
                summary[key]['support_changed_frames'].append(row['frame'])
            if d < -1e-7:
                summary[key]['support_lower_frames'].append(row['frame'])
        summary[key]['minimum_support_delta_m'] = min(delta)
    report = {'method': 'Full-precision diagnostic hook; original branch unchanged. Exact source stamps and identity mount checked. Fixed original near seed isolates far-point dependence; source near refit separately tests seed dependence.',
              'limitations': 'Label-box removal uses observed boxes padded 2cm, may remove real adjacent rail points. Exact subtraction includes all non-source XYZ returns, not only labeled or intensity-1 returns. Source replay is conditional on synthetic fitted geometry, not an independently refitted full-history control. Set O has no ring field: source_same_near passes None and cannot extend. Shared-return variants retain actual synthetic supplied rings only on exact source XYZ members; no ring is inferred.',
              'source_ring_presence': reference_meta[1195]['has_ring'],
              'source_without_ring_is_not_positive_support_control': True,
              'replayed_frames': 315, 'supported_frames': len(rows),
              'non_timing_output_mismatch_frames': mismatches, 'summary': summary,
              'rows': rows, 'input_sha256': source_hashes,
              'labels_sha256': digest(LABELS), 'candidate_capture_sha256': digest(CAPTURE),
              'script_sha256': digest(Path(__file__)), 'source_root': str(SOURCE),
              'code_sha256': code_hashes,
              'source_unchanged': all(digest(SOURCE / name) == sha for name, sha in code_hashes.items())}
    (EVIDENCE / 'exact_source_rail_support.json').write_text(json.dumps(report, indent=2, default=plain) + '\n')
    print(json.dumps({'supported_frames': len(rows), 'mismatches': mismatches, 'summary': summary}), flush=True)


if __name__ == '__main__':
    main()
