"""T1: raw-CDR startup exposure, independent XYZ decode and executed cue branches."""
import argparse
import ast
from copy import deepcopy
import hashlib
import importlib.util
from itertools import islice
import json
import os
from pathlib import Path
import sys
from typing import Optional

import numpy as np
import resense.calibration as cal
from resense.pointcloud import compact_to_compact16, pointcloud2_to_structured, structured_to_compact

ROOT = Path(os.environ['RESENSE_REPO']).resolve()
DATA = Path('/tmp/opencode/resense-b4-data')
WORK = Path('/tmp/opencode/l16-open-air-work')
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'ros2_ws/src/resense_ros'))
from scripts.cache_io import load_cache_array  # noqa: E402
from resense_ros import fastcloud  # noqa: E402


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def cue_list(cue):
    return [None if v is None else v.tolist() for v in cue]


def independent_xyz(msg, low, high):
    types = {1: 'i1', 2: 'u1', 3: 'i2', 4: 'u2', 5: 'i4', 6: 'u4', 7: 'f4', 8: 'f8'}
    fields = {f.name: f for f in msg.fields}
    endian = '>' if msg.is_bigendian else '<'
    dtype = np.dtype({'names': ['x', 'y', 'z'], 'itemsize': msg.point_step,
        'formats': [endian + types[fields[n].datatype] for n in ('x', 'y', 'z')],
        'offsets': [fields[n].offset for n in ('x', 'y', 'z')]})
    view = np.ndarray((msg.height, msg.width), dtype=dtype, buffer=msg.data,
                      strides=(msg.row_step, msg.point_step)).reshape(-1)
    xyz = np.column_stack([view[n] for n in ('x', 'y', 'z')]).astype(np.float32)
    r2 = xyz[:, 0] ** 2 + xyz[:, 1] ** 2 + xyz[:, 2] ** 2
    return xyz[np.isfinite(r2) & (r2 >= low ** 2) & (r2 <= high ** 2)]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    judge = module('t1_jury_runner', ROOT / 'docs/evidence/judgement_2026-10-13/scripts/judge_runner.py')
    reference_source = Path('/tmp/opencode/l16-open-air-reference/resense/calibration.py').read_text()
    node = next(n for n in ast.parse(reference_source).body if isinstance(n, ast.FunctionDef) and n.name == 'directional_axes')
    scope = {'np': np, 'Optional': Optional}
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<pre-fix-directional-axes>', 'exec'), scope)
    before = scope['directional_axes']
    bags = [(name, DATA / 'for_hackathon' / name) for name in (
        'doubleT_obstacle', 'doubleT_platform', 'roundT_doubleT', 'roundT_pressureGate_roundT',
        'roundT_squareT_pressureGate_squareT', 'squareT_platform_squareT_switch')]
    bags += [('set_O', DATA / 'cloud_with_fake_obj'), ('ride_start', WORK / 'new_data_0.db3'),
             ('falcon', Path('/tmp/opencode/l16-s3/falcon_test_second_dark'))]
    marker_root = Path('/tmp/opencode/yadisk-markers-2026-10-19/extracted')
    bags += [(f'marked_{name}', marker_root / f'synthetic_{name}_cloud_with_markers')
             for name in ('platform', 'switch', 'tunnels')]
    report = {'scope': '12 original starts, first 10 raw PointCloud2 messages each; jury default axis mapping',
              'bags': {}, 'pre_fix_function_sha256': hashlib.sha256(ast.unparse(node).encode()).hexdigest()}
    stamp_manifest = json.loads((DATA / 'cache/new_data/new_data_0_stamps.json').read_text())
    for name, bag in bags:
        replica, rows = judge.NodeReplica(), []
        files = judge.db3_files(str(bag))
        assert files, bag
        raw_rows = islice(((ts, topic, raw) for db in files for ts, topic, raw in judge.iter_raw(db)), 10)
        for i, (ts, topic, raw) in enumerate(raw_rows):
            msg = fastcloud.parse_pointcloud2(raw)
            xyz, _, _, _, _ = fastcloud.decode(fastcloud.packed(msg), replica.cfg.sensor.min_range,
                                               replica.cfg.sensor.max_range)
            manual = independent_xyz(msg, replica.cfg.sensor.min_range, replica.cfg.sensor.max_range)
            assert np.array_equal(xyz, manual), (name, i, xyz.shape, manual.shape)
            xyz = xyz @ replica.R_vs.T
            old_cue = before(xyz)
            executed = []
            def trace(f, event, arg):
                if f.f_code.co_filename == cal.__file__ and f.f_code.co_name == 'directional_axes':
                    if event == 'line':
                        executed.append(f.f_lineno)
                    return trace
                return None
            sys.settrace(trace)
            try:
                new_cue = cal.directional_axes(xyz)
            finally:
                sys.settrace(None)
            _, _, result, _, _ = replica.process_raw(raw, topic, i)
            entry = {'i': i, 'bag_time_ns': ts, 'topic': topic, 'frame_id': msg.header.frame_id,
                'raw_cdr_sha256': hashlib.sha256(raw).hexdigest(),
                'vehicle_xyz_sha256': hashlib.sha256(xyz.tobytes()).hexdigest(), 'points': len(xyz),
                'independent_raw_numpy_decode_equal': True, 'axis_matrix': replica.R_vs.tolist(),
                'positive_fraction': (xyz > 0).mean(axis=0).tolist(),
                'before_cue': cue_list(old_cue), 'after_cue': cue_list(new_cue),
                'executed_cue_lines': executed, 'mount': deepcopy(result.mount),
                'decision': judge.node_decision(result), 'health': deepcopy(result.health),
                'raw_examples': xyz[np.linspace(0, len(xyz) - 1, 4, dtype=int)].tolist()}
            if name == 'ride_start':
                cached = load_cache_array(DATA / f'cache/new_data/new_data_0_{i:04d}.npy.zst')
                reconstructed = compact_to_compact16(structured_to_compact(pointcloud2_to_structured(fastcloud.packed(msg))))
                assert np.array_equal(cached, reconstructed), ('ride cache identity', i)
                assert ts / 1e9 == stamp_manifest['stamps'][f'{i:04d}']
                entry['prior_verified_ride_cache_exact'] = True
            rows.append(entry)
        assert len(rows) == 10, (name, len(rows))
        report['bags'][name] = {'bag': str(bag), 'rows': rows}
        print(name, 'above minimum', min(r['positive_fraction'][2] for r in rows),
              'cues', rows[0]['before_cue'], rows[0]['after_cue'],
              'confirmed', rows[-1]['mount']['orientation_confirmed'], flush=True)
    scene = module('t1_known_positive_scene', ROOT / 'docs/evidence/p4_review_shipping_2026-10-20/scripts/scene.py')
    rays, ring = scene.rays(-104, 106)
    frame, _ = scene.frame(rays, ring, *scene.cast(rays, tunnel=False, open_air=True))
    assert np.array_equal(before(frame.xyz)[0], [0, 0, -1])
    assert cal.directional_axes(frame.xyz) == (None, None)
    report['positive_control'] = {'before': cue_list(before(frame.xyz)), 'after': [None, None]}
    assert len(report['bags']) == 12
    with a.out.open('x') as out:
        json.dump(report, out, indent=2)


if __name__ == '__main__':
    main()
