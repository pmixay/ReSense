"""Independently recheck final Set F rows/banks; never invoke a detector."""
from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / 'set_f_baseline_pose_fixed'
CACHE = Path('/home/resense/data/gate_cache/new_data')
STARTS = (46, 68, 98, 140, 168, 172)
KINDS = ('person', 'box1.0', 'box0.5', 'trolley', 'cable')
LEVELS = ('clean', 'low', 'medium', 'high')
DETECTOR = '9b92df56e802d9d63f83f2fc5e5b07374db669c7'
HARNESS = 'b9ad5f4348e1ffd882bb6a503961a9768384c416'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def blob_sha(commit, name):
    return hashlib.sha256(subprocess.check_output(['git', 'show', f'{commit}:{name}'], cwd=ROOT)).hexdigest()


def summarize(rows, clean):
    hits = [row['index'] for row in rows if row['hit']]
    false = [row['index'] for row in rows if row['false_detections']]
    output = {'frames': len(rows), 'counts': dict(Counter(row['decision'] for row in rows)),
              'hit_frames': hits, 'first_stop_frame': hits[0] if hits else None,
              'first_stop_m': rows[hits[0]]['distance'] if hits else None,
              'clean_supported_frames': sum(row['clean_returns'] > 0 for row in rows),
              'observed_supported_frames': sum(row['retained_object_returns'] > 0 for row in rows),
              'observed_hit_frames': [row['index'] for row in rows if row['hit'] and row['retained_object_returns'] > 0],
              'false_stop_frames': false,
              'false_stop_episodes': sum(i == 0 or frame != false[i-1]+1 for i, frame in enumerate(false)),
              'false_detections': sum(row['false_detections'] for row in rows),
              'degraded_frames': sum(row['degraded'] for row in rows),
              'go_frames': [row['index'] for row in rows if row['decision'] == 'GO']}
    if clean is not None:
        output.update(lost_clean_stop_frames=sorted(set(clean['hit_frames'])-set(hits)),
                      new_stop_frames=sorted(set(hits)-set(clean['hit_frames'])),
                      extra_false_stop_episodes=output['false_stop_episodes']-clean['false_stop_episodes'],
                      first_stop_ratio=(output['first_stop_m']/clean['first_stop_m']
                          if clean['first_stop_m'] and output['first_stop_m'] is not None else None))
    return output


def main():
    aggregate, summary, manifest = (read(OUT / name) for name in ('aggregate.json', 'summary.json', 'placement_manifest.json'))
    assert aggregate['complete'] and aggregate['sequences'] == 30 and tuple(aggregate['levels']) == LEVELS
    assert sha(OUT / 'summary.json') == aggregate['summary_sha256']
    assert sha(OUT / 'placement_manifest.json') == summary['placement_manifest_sha256']
    assert sha(HERE / 'summarize_set_f.py') == aggregate['script_sha256']
    assert summary['dust_seed'] == 20261018
    expected = {f'{start}_{kind}' for start in STARTS for kind in KINDS}
    assert set(summary['sequences']) == set(manifest['sequences']) == set(aggregate['placement_archives']) == expected
    assert summary['configuration'] == manifest['configuration']
    for payload, source_name in ((summary, 'detector_root'), (manifest, 'source_root')):
        source = Path(payload[source_name])
        assert sha(source / 'configs/default.yaml') == payload['configuration_yaml_sha256'] == blob_sha(DETECTOR, 'configs/default.yaml')
        for name, digest in payload['source_hashes'].items():
            assert sha(source / name) == digest
            if name.endswith('.so'):
                assert digest == '511f7766639f0ddab471a77263f7a343de19d0a8217dd7cd3a11635c8a7db2c8'
            else:
                assert blob_sha(DETECTOR, name) == digest
        for name, digest in payload['helper_sha256'].items():
            assert sha(ROOT / name) == blob_sha(HARNESS, name) == digest
        assert payload['script_sha256'] == sha(ROOT / 'scripts/dust_set_f.py') == blob_sha(HARNESS, 'scripts/dust_set_f.py')
        assert payload['native_status'].startswith('native')
    intake = ROOT / 'docs/extended_dataset_intake.json'
    assert sha(intake) == manifest['speeds_sha256']
    speeds = {entry['n']: entry.get('speed_tracks') or 0. for entry in read(intake)['files']}
    stamps = {}
    for path in CACHE.glob('*_stamps.json'):
        record = read(path)
        bag = record.get('bag') or path.name[:-len('_stamps.json')]
        stamps.update({f'{bag}_{frame}': float(stamp) for frame, stamp in record['stamps'].items()})
    selected, planned, source_cache = {}, {}, {}
    for start in STARTS:
        distance, previous, keep = 220., None, True
        planned[start] = []
        for index in range(110):
            split, offset = start + index//51, index % 51
            stem = f'new_data_{split}_{offset:04d}'
            stamp = stamps[stem]
            selected[stem] = stamp
            if previous is not None:
                assert 0 < stamp-previous < 10
                distance -= speeds[split]*(stamp-previous)
            previous = stamp
            keep = keep and distance >= 8
            if keep:
                filename = stem+'.npy.zst'
                if filename not in source_cache:
                    source_cache[filename] = sha(CACHE / filename)
                planned[start].append(dict(index=index, cache_file=filename, cache_sha256=source_cache[filename],
                                           stamp=stamp, speed=speeds[split], distance=distance))
    assert hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest() == manifest['selected_stamps_sha256']
    totals, ambiguities, details, hashes = {level: Counter() for level in LEVELS}, {}, {}, {}
    ratios, complete_misses = {}, {}
    vanished_returns_with_hit = {level: 0 for level in LEVELS}
    no_clean_returns_stop = {level: 0 for level in LEVELS}
    for name in sorted(expected):
        start, kind = name.split('_', 1)
        start = int(start)
        archive = OUT / aggregate['placement_archives'][name]['archive']
        archived = aggregate['placement_archives'][name]
        assert sha(archive) == archived['gzip_sha256']
        hashes[str(archive)] = sha(archive)
        data = gzip.decompress(archive.read_bytes())
        assert hashlib.sha256(data).hexdigest() == archived['raw_sha256'] == manifest['sequences'][name]
        bank = json.loads(data)
        assert bank['id'] == name and bank['kind'] == kind and bank['start_split'] == start and bank['requested_frames'] == 110
        assert len(bank['frames']) == len(planned[start])
        recorded_detail = aggregate['details'][name]
        assert (recorded_detail['kind'], recorded_detail['start_split'], recorded_detail['frames']) == (kind, start, len(bank['frames']))
        for frozen, original in zip(bank['frames'], planned[start]):
            assert all(frozen[key] == value for key, value in original.items())
            assert frozen['distance'] == frozen['spec']['distance']
            reference = frozen['dust_reference']
            digest = hashlib.sha256(json.dumps({k:v for k,v in reference.items() if k != 'reference_sha256'},
                                    sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
            assert digest == reference['reference_sha256'] and frozen['rail_z'] == reference['rail_z_at20']
        clean = None
        details[name] = {}
        for level in LEVELS:
            entry = summary['sequences'][name]['levels'][level]
            path = OUT / f'{name}_{level}.jsonl.gz'
            assert sha(path) == entry['raw_sha256']
            hashes[str(path)] = sha(path)
            with gzip.open(path, 'rt') as stream:
                rows = [json.loads(line) for line in stream]
            assert len(rows) == len(bank['frames'])
            for i, (row, frozen) in enumerate(zip(rows, bank['frames'])):
                assert row['index'] == i and row['cache_file'] == frozen['cache_file'] and row['distance'] == frozen['distance']
                assert row['clean_frame_sha256'] == frozen['clean_frame_sha256'] and row['clean_returns'] == frozen['clean_returns']
                result, audit = row['result'], row['augmentation']
                assert result['stamp'] == frozen['stamp']
                assert type(result['obstacle']) is bool and result['obstacle'] == bool(result['detections'])
                health = result['health']
                decision = ('STOP' if result['obstacle'] else 'FAULT' if health['level'] == 'error' else
                            'CAUTION' if result['warning'] or health['decision_level'] == 'warn' else 'GO')
                assert decision == row['decision'] and row['degraded'] == (health['decision_level'] in ('warn','error'))
                assert 0 <= row['retained_object_returns'] <= row['clean_returns']
                assert audit['placement_reference'] == frozen['dust_reference']
                assert row['dust_reference_sha256'] == frozen['dust_reference']['reference_sha256']
                assert audit['seed'] == 20261018 and audit['frame_index'] == i and audit['rail_z'] == frozen['rail_z']
                density, extinction = {'clean': (0,0), 'low': (.1,.0005), 'medium': (1,.003), 'high': (10,.02)}[level]
                assert audit['spec'] == dict(density=density, extinction=extinction, x_bounds=[2.5,60.],
                    y_bounds=[-3.,3.], height_bounds=[.1,3.5], intensity_max=5.)
                if level == 'clean':
                    assert audit['added_returns'] == audit['removed_returns'] == 0
                    assert row['retained_object_returns'] == row['clean_returns']
                certain, possible = [], []
                for detection in result['detections']:
                    dx = abs(detection['distance']-frozen['distance'])
                    dy = abs(detection['lateral']-frozen['spec']['lateral'])
                    tolerance = max(2., .03*frozen['distance'])
                    certain.append(dx+.005000001 <= tolerance and dy+.005000001 <= 1.2)
                    possible.append(dx-.005000001 <= tolerance and dy-.005000001 <= 1.2)
                low_hit, high_hit = bool(any(certain) and frozen['clean_returns'] > 0), bool(any(possible) and frozen['clean_returns'] > 0)
                low_false, high_false = len(possible)-sum(possible), len(certain)-sum(certain)
                assert low_hit <= row['hit'] <= high_hit and low_false <= row['false_detections'] <= high_false
                if low_hit != high_hit or low_false != high_false:
                    ambiguities.setdefault(f'{name}/{level}', []).append(dict(index=i, hit_bounds=[low_hit,high_hit],
                        false_detection_bounds=[low_false,high_false], recorded_hit=row['hit'], recorded_false_detections=row['false_detections']))
                vanished_returns_with_hit[level] += bool(row['hit'] and not row['retained_object_returns'])
                no_clean_returns_stop[level] += bool(result['obstacle'] and not row['clean_returns'])
            recalculated = summarize(rows, clean)
            assert recalculated == {k:v for k,v in entry.items() if k != 'raw_sha256'}
            if level == 'clean':
                clean = recalculated
            assert recorded_detail['first_m'][level] == recalculated['first_stop_m']
            assert recorded_detail['lost_clean_stop_rows'][level] == recalculated.get('lost_clean_stop_frames', [])
            assert recorded_detail['false_stop_episodes'][level] == recalculated['false_stop_episodes']
            if level != 'clean' and clean['first_stop_m'] is not None:
                if recalculated['first_stop_m'] is None:
                    complete_misses.setdefault(level, []).append(name)
                else:
                    ratios.setdefault(level, {})[name] = recalculated['first_stop_m']/clean['first_stop_m']
            t = totals[level]
            for key, value in {'frames':len(rows), 'matched_stop_rows':len(recalculated['hit_frames']),
                    'clean_supported_frames':recalculated['clean_supported_frames'],
                    'retained_return_supported_frames':recalculated['observed_supported_frames'],
                    'observed_matched_stop_rows':len(recalculated['observed_hit_frames']),
                    'false_stop_frames':len(recalculated['false_stop_frames']),
                    'false_stop_episodes':recalculated['false_stop_episodes'], 'false_detections':recalculated['false_detections'],
                    'degraded_frames':recalculated['degraded_frames'],
                    'lost_clean_stop_rows':len(recalculated.get('lost_clean_stop_frames',[])),
                    'new_stop_rows':len(recalculated.get('new_stop_frames',[]))}.items():
                t[key] += value
            t.update({f'decision_{key}':value for key,value in recalculated['counts'].items()})
            details[name][level] = {key:recalculated[key] for key in ('first_stop_frame','first_stop_m','hit_frames','false_stop_episodes')}
    assert {level:dict(stats) for level,stats in totals.items()} == aggregate['totals']
    assert ratios == aggregate['first_stop_ratios']
    assert {k:sorted(v) for k,v in complete_misses.items()} == {k:sorted(v) for k,v in aggregate['lost_all_clean_object_stops'].items()}
    assert ambiguities == aggregate['serialized_geometry_boundary_rows']
    assert sum(stats['frames'] for stats in totals.values()) == aggregate['total_processed_frames'] == 12240
    inputs = [Path(__file__), HERE / 'summarize_set_f.py', OUT / 'aggregate.json', OUT / 'summary.json',
              OUT / 'placement_manifest.json', OUT / 'verified_ride_receipt.json', intake]
    output = {'status':'COMPLETE_SET_F_EVIDENCE_REVALIDATED_NOT_N3_ACCEPTANCE',
              'checked_utc':datetime.now(timezone.utc).isoformat(), 'detector_commit':DETECTOR, 'harness_commit':HARNESS,
              'sequences':30, 'raw_captures':120, 'rows':12240, 'unique_source_cache_hashes_verified':source_cache,
              'totals':totals, 'details':details, 'rounding_boundary_rows':ambiguities,
              'matched_rows_with_all_object_returns_attenuated':vanished_returns_with_hit,
              'stop_rows_with_zero_clean_object_returns':no_clean_returns_stop,
              'input_sha256':{**hashes, **{str(path):sha(path) for path in inputs}},
              'limits':['Frozen synthetic object placement on real backgrounds; not the real crossing-person criterion.',
                        'No detector or renderer rerun; bank source hashes/cadence and archived raw evidence rechecked.',
                        'Legacy association is approximate; 1cm geometry has explicit rounding uncertainty.',
                        'Physical clean truth remains when attenuation removes returns; observed-return statistics stay separate.',
                        'Detector9b/harnessb9, not a new selectedcecab stress test; no physical-dust or throughput claim.']}
    (HERE / 'independent_completed_set_f_review.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({k:output[k] for k in ('status','sequences','raw_captures','rows')}))


if __name__ == '__main__':
    main()
