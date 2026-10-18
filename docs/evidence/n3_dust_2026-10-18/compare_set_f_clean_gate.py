"""Bind corrected clean Set F rows to the independent native9b gate control."""
from dataclasses import asdict
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / 'set_f_baseline_pose_fixed'
CONTROL = ROOT / 'docs/evidence/lidar_adaptation_2026-10-18/control_9b_native'
sys.path.insert(0, '/home/resense/data/control_lidar_9b92df5')

import numpy as np  # noqa: E402
from resense.config import DetectorConfig  # noqa: E402
from resense.track import TrackModel  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plain(value):
    return json.loads(json.dumps(value))


def main():
    path = CONTROL / 'work/setF_straight.json'
    gate, receipt = read(path), read(CONTROL / 'receipt.json')
    summary, manifest = read(OUT / 'summary.json'), read(OUT / 'placement_manifest.json')
    assert receipt['status'] == 'FINISHED' and receipt['source_commit'] == '9b92df56e802d9d63f83f2fc5e5b07374db669c7'
    assert receipt['source_unchanged']
    original_audit = read(CONTROL.parent / 'default_off/gate_independent_review.json')
    assert original_audit['input_sha256'][str(path)] == sha(path)
    cfg_path = CONTROL / 'work/config.yaml'
    cfg = DetectorConfig.from_yaml(str(cfg_path))
    assert plain(asdict(cfg)) == summary['configuration'] == manifest['configuration']
    params = gate['parameters']
    assert params['config_sha256'] == sha(cfg_path)
    assert params['placement_mode'] == 'legacy' and params['place'] == 'bed' and params['given_speed'] is False
    assert params['seed'] == 0 and params['start_m'] == 220 and params['frames'] == 110
    for key in ('speeds_sha256', 'selected_stamps_sha256'):
        assert params[key] == manifest[key]
    result, rows_total, hash_inputs = {}, 0, {}
    for sequence in gate['sequences']:
        start = int(sequence['file0'].split('_')[2])
        name = f'{start}_{sequence["kind"]}'
        archive = OUT / 'placement_bank' / f'{name}.json.gz'
        bank = json.loads(gzip.decompress(archive.read_bytes()))
        clean_path = OUT / f'{name}_clean.jsonl.gz'
        with gzip.open(clean_path, 'rt') as stream:
            clean = [json.loads(line) for line in stream]
        assert len(clean) == len(bank['frames']) == len(sequence['rows'])
        assert bank['reflectivity'] == sequence['refl'] and bank['lateral'] == sequence['lateral']
        assert sequence['first'] == summary['sequences'][name]['levels']['clean']['first_stop_m']
        assert sequence['fp'] == sum(row['false_detections'] for row in clean)
        for old, row, frozen in zip(sequence['rows'], clean, bank['frames']):
            assert old['frame'] == frozen['cache_file'][:-len('.npy.zst')]
            assert old['d'] == old['path_d'] == round(frozen['distance'], 1)
            assert old['n'] == frozen['clean_returns'] == row['clean_returns']
            assert old['hit'] == row['hit'] and len(old['fp_dets']) == row['false_detections']
            assert old['mon'] == row['result']['health']['monitored_range']
            assert old['vis'] == row['result']['health']['visibility']
            spec = frozen['spec']
            serialized = {key:value for key,value in spec.items() if value is not None}
            if 'base_z' in serialized:
                serialized['base_z'] = round(serialized['base_z'], 3)
            assert old['gt'] == serialized
            model = TrackModel(**dict(frozen['placement_model'], floor_coef=np.asarray(frozen['placement_model']['floor_coef'])))
            y = float(model.center_y(spec['distance']+spec['size'][0]/2))+spec['lateral']
            assert old['gt_vehicle_y_m'] == y
            assert old['axis_error_m'] == round(spec['lateral']-sequence['lateral'], 2)
        rows_total += len(clean)
        result[name] = {'rows':len(clean), 'matched_rows':sum(row['hit'] for row in clean),
                        'first_match_m':sequence['first'], 'unmatched_detections':sequence['fp'],
                        'all_compared_fields_exact':True}
        hash_inputs[str(archive)] = sha(archive)
        hash_inputs[str(clean_path)] = sha(clean_path)
    assert len(result) == 30 and rows_total == 3060
    assert sum(case['matched_rows'] for case in result.values()) == 1064
    inputs = [Path(__file__), path, CONTROL / 'receipt.json', cfg_path, OUT / 'summary.json',
              OUT / 'placement_manifest.json', CONTROL.parent / 'default_off/gate_independent_review.json']
    output = {'status':'ALL3060_SHARED_CLEAN_PLACEMENT_AND_SCORING_ROWS_EXACT',
              'checked_utc':datetime.now(timezone.utc).isoformat(), 'sequences':30, 'rows':3060,
              'matched_rows':1064, 'per_sequence':result, 'effective_configuration_identical':True,
              'source_speed_and_stamp_identity_equal':True,
              'fields_compared':['source frame', 'distance/path distance', 'serialized target spec', 'vehicle target y',
                                 'axis error', 'clean object return count', 'hit', 'unmatched detection count',
                                 'monitored range', 'visibility', 'sequence first matched range'],
              'limits':['Gate scoring rows omit full detections and timestamps; this is exact shared-field equality, not complete output/payload equivalence.',
                        'Gate candidate-hit flag has no matching serialized candidate list in dust rows and is not independently compared.',
                        'Gate stores unmatched detection geometry at different precision; counts match, full-precision reassignment is not claimed.',
                        'Background cache provenance and speed/stamp hashes match; injected point bytes are not stored by the gate, so input cloud byte equality is not independently proven.'],
              'input_sha256':{**hash_inputs, **{str(p):sha(p) for p in inputs}}}
    (HERE / 'set_f_clean_gate_comparison.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:output[k] for k in ('status','sequences','rows','matched_rows')}))


if __name__ == '__main__':
    main()
