"""Audit publication checks from raw rows, prior evidence and current source bytes."""
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/h1-publication')
sys.path.insert(0, str(ROOT / 'scripts'))
import robustness_battery as battery  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    spec = importlib.util.spec_from_file_location('h1_receipts', ROOT / 'docs/evidence/h1_core_2026-10-19/run_checks.py')
    receipts = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(receipts)
    sources = receipts.sources(ROOT)
    for phase in ['physical', 'x3']:
        receipt = read(HERE / f'{phase}-execution.json')
        assert receipt['source_unchanged'] and receipt['source_sha256'] == sources
        assert receipt['returncode'] == 0 and sha(WORK / f'{phase}.log') == receipt['log_sha256']
    prior = read(ROOT / 'docs/evidence/h1_trajectory_2026-10-19/audit-final.json')
    assert prior['source_files'] == sources
    report = dict(status='H1_PARTIAL_IMPROVEMENT_ACCEPTED_OVERALL_OPEN', source_files=sources,
        source_fingerprint=hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest(),
        measured_detector_commit='0f02b283a9a8ebeb8bccae76a7b12f23862206df',
        merged_remote_base='0acb18c57bfb84c61d9344aacaad8b65be648b07',
        publication_authorization='User explicitly requests publication of the partial improvement while H1 remains OPEN; supersedes earlier closure-only push condition.')
    data = read(WORK / 'x3.json')
    reference = read(ROOT / 'docs/evidence/h1_reference_2026-10-19/x3-e-candidate.json')
    cache = Path('/tmp/opencode/resense-b4-data/decoded')
    for obj in [reference, data]:
        battery.validated_entries(obj, cache, ROOT)
    assert data['status'] == 'PASS' and len(data['entries']) == 40 and not data['errors']
    cases = {}
    comparisons = []
    for key, entry in data['entries'].items():
        before, after = rows(Path(reference['entries'][key]['raw_path'])), rows(Path(entry['raw_path']))
        assert [r['i'] for r in before] == [r['i'] for r in after]
        old_stop, new_stop = [{r['i'] for r in obj if r['decision'] == 'STOP'} for obj in [before, after]]
        lost_payloads = []
        for a, b in zip(before, after, strict=True):
            ca, cb = (Counter(json.dumps(d, sort_keys=True) for d in r['dets']) for r in [a, b])
            if ca-cb:
                lost_payloads.append(a['i'])
        calculated = battery.compare_metrics(reference['entries'][key]['metrics'], entry['metrics'])
        assert calculated == data['comparison']['cases'][key] and all(r['passed'] for r in calculated)
        comparisons += calculated
        cases[key] = dict(frames=len(after), old_STOP=len(old_stop), current_STOP=len(new_stop),
            lost_STOP=sorted(old_stop-new_stop), added_STOP=sorted(new_stop-old_stop), lost_detection_payload_rows=lost_payloads)
    assert sum(row['frames'] for row in cases.values()) == 29765
    # Exercise both the metrics comparator and raw payload accounting on a known positive.
    positive = reference['entries']['doubleT_obstacle/nominal']['metrics']
    planted = deepcopy(positive)
    planted['stop_frames'] -= 3
    assert any(not r['passed'] for r in battery.compare_metrics(positive, planted))
    positive_row = next(r for r in rows(Path(data['entries']['doubleT_obstacle/nominal']['raw_path'])) if r['dets'])
    old = Counter(json.dumps(d, sort_keys=True) for d in positive_row['dets'])
    assert old-Counter()
    report['X3'] = dict(status='PASS', cases=cases, rows=29765, comparisons=len(comparisons),
        comparison_controls_passed=True, source_identity_workers_and_raw_hashes_verified=True,
        reference='retained E, docs/evidence/h1_reference_2026-10-19/x3-e-candidate.json')
    physical = read(WORK / 'physical.json')
    old_physical = read(ROOT / 'docs/evidence/h1_reference_2026-10-19/physical-e.json')
    assert len(physical['full']) == 32 and len(physical['outside']) == 280 and len(physical['moving']) == 12
    for case, old in zip(physical['full'], old_physical['full'], strict=True):
        matches = []
        for row in case['rows']:
            hit = any(abs(d['distance']-case['distance']) < 1 and abs(d['center'][1]-case['lateral']) < .5 for d in row['detections'])
            assert hit == row['hit']
            if hit:
                matches.append(row['i'])
        assert matches == case['matched'] == old['matched'] == list(range(4, 14))
    assert all(not row['stop'] and not row['core'] for row in physical['outside'])
    # The outside selector's own path must detect an inside body, not only return negatives.
    spec2 = importlib.util.spec_from_file_location('h1_physical_checks', ROOT / 'tests/test_column_collision_core.py')
    controls = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(controls)
    xyz, ring, labels = controls.physical_column(distance=67., lateral=.68, top=4.12)
    clusters = controls.matched(xyz, ring, labels)
    assert any(c.collision_core and any(controls.stop_history(c)) for c in clusters)
    for new, old in zip(physical['moving'], old_physical['moving'], strict=True):
        assert new['geometry'] == old['geometry'] and new['lateral'] == old['lateral']
        assert [(r['distance'], r['hit']) for r in new['rows']] == [(r['distance'], r['hit']) for r in old['rows']]
        continuous = next((r['distance'] for i, r in enumerate(new['rows']) if all(s['hit'] for s in new['rows'][i:])), None)
        assert continuous == new['continuous_from']
    report['physical'] = dict(stationary_cases=32, stationary_matched_rows=320, every_post_confirmation_row_matched=True,
        outside_cases=280, false_STOP=0, outside_selector_positive_control=True,
        moving_cases=12, nominal_continuous_from_m=[row['continuous_from'] for row in physical['moving'][:2]],
        limitation='Idealized ray-cast physical scenes, not verified real-world detection or braking range.')
    report['preserved_merged_checks'] = dict(gate=prior['gate']['main_non_timing_metric_identity'],
        probes=prior['probes'], Falcon=prior['Falcon'], tests=prior['tests'])
    report['remaining'] = dict(A_axis_visible_unmatched=63, validated_far_axis_reference=False,
        overall_H1_closed=False, independent_final_review='pending', combined_reseal='pending',
        full_pytest_all_green=False)
    with (HERE / 'acceptance.json').open('x') as stream:
        json.dump(report, stream, indent=2)
    (HERE / 'x3.json').write_text(json.dumps(data, indent=2))
    raw_files = [p for p in WORK.rglob('*') if p.is_file()]
    manifest = {str(p.relative_to(WORK)): dict(sha256=sha(p), bytes=p.stat().st_size) for p in raw_files}
    archive = HERE / 'raw-evidence.tar.gz'
    with tarfile.open(archive, 'x:gz') as tar:
        for path in raw_files:
            tar.add(path, arcname=str(path.relative_to(WORK)), recursive=False)
    with tarfile.open(archive) as tar:
        assert set(tar.getnames()) == set(manifest)
        for member in tar:
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest() == manifest[member.name]['sha256']
    (HERE / 'raw-manifest.json').write_text(json.dumps(manifest, indent=2))
    (HERE / 'package.json').write_text(json.dumps(dict(file=archive.name, bytes=archive.stat().st_size,
        sha256=sha(archive), members=len(manifest), all_member_hashes_verified=True), indent=2))
    print('X3', len(cases), 'cases', len(comparisons), 'comparisons', sum(len(v['lost_STOP']) for v in cases.values()), 'lost STOP rows',
          sum(len(v['added_STOP']) for v in cases.values()), 'added STOP rows',
          sum(len(v['lost_detection_payload_rows']) for v in cases.values()), 'changed/lost payload rows')
    print('PHYSICAL', report['physical'])
    print('PACKAGE', archive.stat().st_size, sha(archive))


if __name__ == '__main__':
    main()
