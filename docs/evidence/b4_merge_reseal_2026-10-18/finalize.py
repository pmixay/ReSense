"""Validate complete paired results and preserve every measured row in hashed archives."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = Path('/home/resense/data/b4_merge_reseal')
SOURCE = WORK / 'source'
REFERENCE = WORK / 'reference'
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]

from scripts import detector_freeze as freeze  # noqa: E402
from scripts import regression_gate as gate  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + '\n')


def spans(rows):
    result = []
    for i, row in enumerate(rows):
        if row['obstacle']:
            if result and result[-1][1] == i - 1:
                result[-1][1] = i
            else:
                result.append([i, i])
    return result


def archive(folder, name):
    target = HERE / (name + '.tar.gz')
    members = []
    assert not target.exists()
    with tarfile.open(target, 'w:gz') as bundle:
        for path in sorted(folder.rglob('*')):
            if path.is_file():
                rel = str(path.relative_to(folder))
                bundle.add(path, arcname=rel, recursive=False)
                members.append({'path': rel, 'bytes': path.stat().st_size, 'sha256': sha(path)})
    expected = {m['path']: m for m in members}
    with tarfile.open(target) as bundle:
        seen = set()
        for member in bundle:
            assert member.isfile() and member.name not in seen
            data = bundle.extractfile(member).read()
            assert hashlib.sha256(data).hexdigest() == expected[member.name]['sha256']
            assert len(data) == expected[member.name]['bytes']
            seen.add(member.name)
        assert seen == set(expected)
    receipt = {'archive': target.name, 'sha256': sha(target), 'bytes': target.stat().st_size,
               'members': members, 'reopened_all_members_verified': True}
    write(HERE / (name + '_manifest.json'), receipt)
    return receipt


def main():
    files = freeze.source_hashes(ROOT)
    assert files == freeze.source_hashes(SOURCE)
    for checkout in (SOURCE, REFERENCE):
        assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=checkout, text=True)
    inputs = [Path(__file__), HERE / 'PROTOCOL.md', HERE / 'initial_clean_build.json']
    for stage in ('tests', 'gate-reference', 'gate', 'x3-reference', 'x3', 'b4'):
        path = HERE / f'{stage}_execution.json'
        receipt = read(path)
        assert receipt['status'] == 'complete'
        assert receipt['source']['files'] == files
        assert receipt['source']['native'] == receipt['reference']['native']
        assert receipt['runner_sha256'] == sha(HERE / 'run_measurements.py')
        for execution in receipt['runs']:
            assert execution['exit'] == 0
            log = HERE / (execution['name'] + '.log')
            assert sha(log) == execution['log_sha256']
            inputs.append(log)
        inputs.append(path)
    measured = receipt['source']['commit']
    for name, digest in files.items():
        blob = subprocess.check_output(['git', 'show', f'{measured}:{name}'], cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == digest
    reference_files = freeze.source_hashes(REFERENCE)
    for name, digest in reference_files.items():
        blob = subprocess.check_output(['git', 'show', f'9917851:{name}'], cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == digest
    assert set(files) == set(reference_files)
    changed = [name for name in files if files[name] != reference_files[name]]
    assert changed == ['resense/calibration.py', 'resense/detector.py', 'resense/health.py']
    baseline = read(ROOT / 'docs/evidence/results/regression_baseline_2026-09-29_shell_off.json')
    for name, expected in (('gate', measured), ('gate-reference', receipt['reference']['commit'])):
        report = read(HERE / (name + '.json'))
        assert report['code']['commit'] == expected
        freeze.check_gate(baseline, report, files[freeze.CONFIG])
        assert report['gate']['same'] == 208 and not report['gate']['better']
        assert gate.gate_summary(gate.compare(baseline, report, []), baseline,
                                 report['gate']['baseline'], []) == report['gate']

    env = dict(os.environ, OPENBLAS_CORETYPE='Haswell', OPENBLAS_NUM_THREADS='1',
               OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    helper = ROOT / 'docs/evidence/lidar_adaptation_2026-10-18/review_gate_frames.py'
    command = [sys.executable, str(helper), '--reference', str(HERE / 'gate-reference.json'),
               '--candidate', str(HERE / 'gate.json'), '--reference-work', str(WORK / 'gate-reference'),
               '--candidate-work', str(WORK / 'gate'), '--reference-source', str(REFERENCE),
               '--candidate-source', str(SOURCE), '--cache', '/home/resense/data/gate_cache',
               '--out', str(HERE / 'gate_frame_review.json')]
    if not (HERE / 'gate_frame_review.json').exists():
        subprocess.run(command, cwd=ROOT, env=env, check=True)
    review = read(HERE / 'gate_frame_review.json')
    for name, digest in review['input_sha256'].items():
        assert sha(ROOT / name) == digest
    for case in review['ordinary'].values():
        assert set(case['changed_fields']) <= {'added:mount.orientation_conflict'}
        assert not any(case[key] for key in ('lost_stop_frames', 'added_stop_frames',
            'frames_with_changed_or_missing_old_detection_payload', 'unconfirmed_orientation_guard_violations'))
    assert not review['set_F_parameter_changes']
    assert all(not c['changed_fields'] for c in review['set_F'])
    gate_stops = gate_intervals = 0
    for name in review['candidate_raw_hashes']:
        assert sha(WORK / 'gate' / name) == review['candidate_raw_hashes'][name]
        assert sha(WORK / 'gate-reference' / name) == review['reference_raw_hashes'][name]
        before, after = ([json.loads(line) for line in (WORK / tag / name).read_text().splitlines()]
                         for tag in ('gate-reference', 'gate'))
        assert spans(before) == spans(after)
        assert all(r['mount']['orientation_conflict'] is False for r in after)
        gate_stops += sum(r['obstacle'] for r in after)
        gate_intervals += len(spans(after))

    xhelper = ROOT / 'docs/evidence/lidar_adaptation_2026-10-18/review_x3.py'
    command = [sys.executable, str(xhelper), '--reference', str(WORK / 'x3-reference.json'),
               '--candidate', str(WORK / 'x3.json'), '--cache', '/home/resense/data/x3_reference/cache',
               '--out', str(HERE / 'x3_frame_review.json')]
    if not (HERE / 'x3_frame_review.json').exists():
        subprocess.run(command, cwd=ROOT, env=env, check=True, stdout=subprocess.DEVNULL)
    xr = read(HERE / 'x3_frame_review.json')
    for name, digest in xr['input_sha256'].items():
        assert sha(ROOT / name) == digest
    assert xr['candidate_gate_status'] == 'PASS' and xr['all_metrics_identical']
    assert xr['all_non_timing_fields_identical']
    x3_stops = x3_intervals = 0
    for tag in ('x3', 'x3-reference'):
        report = read(WORK / (tag + '.json'))
        assert report['status'] == 'PASS' and not report['errors']
        for entry in report['entries'].values():
            assert sha(Path(entry['raw_path'])) == entry['raw_sha256']
        shutil.copyfile(WORK / (tag + '.json'), HERE / (tag + '.json'))
        if tag == 'x3':
            for entry in report['entries'].values():
                rows = [json.loads(line) for line in Path(entry['raw_path']).read_text().splitlines()]
                x3_stops += sum(r['obstacle'] for r in rows)
                x3_intervals += len(spans(rows))
    b4 = read(HERE / 'b4_summary.json')
    assert b4['pass'] and all(row['pass'] for row in b4['checks'])
    for name, digest in b4['raw_sha256'].items():
        assert sha(WORK / 'b4' / name) == digest

    archives = {}
    for folder in ('gate-reference', 'gate', 'x3-reference.raw', 'x3.raw', 'b4'):
        archives[folder] = archive(WORK / folder, folder.replace('.', '_'))
    inputs += [helper, xhelper, HERE / 'run_measurements.py', HERE / 'gate.json',
               HERE / 'gate-reference.json', HERE / 'gate_frame_review.json', HERE / 'x3.json',
               HERE / 'x3-reference.json', HERE / 'x3_frame_review.json', HERE / 'b4_summary.json',
               HERE / 'directed.json', HERE / 'affected_tests.xml']
    result = {'status': 'PAIRED_MERGED_SOURCE_CHECKS_PASS', 'measured_commit': measured,
              'measurement_protocol_commit': subprocess.check_output(
                  ['git', 'rev-parse', '008a7ec'], cwd=ROOT, text=True).strip(),
              'reference_commit': receipt['reference']['commit'], 'source_sha256': freeze.source_digest(files),
              'frozen_files': len(files), 'changed_frozen_files_vs_main': changed,
              'native': receipt['source']['native'], 'ordinary_gate_rows': review['ordinary_rows'],
              'set_F_rows': review['set_F_rows'], 'ordinary_stop_frames': gate_stops,
              'ordinary_stop_intervals': gate_intervals, 'ordinary_payload_changes': 'only added false mount.orientation_conflict',
              'x3_cases': xr['case_count'], 'x3_rows': xr['rows_compared'],
              'x3_checks': sum(len(rows) for rows in xr['comparison_recomputed']['cases'].values()),
              'x3_stop_frames': x3_stops, 'x3_stop_intervals': x3_intervals,
              'b4_rows': 2 * 24 * (545 + 201), 'b4_checks': len(b4['checks']),
              'archives': {k: {'path': v['archive'], 'sha256': v['sha256'], 'members': len(v['members'])}
                           for k, v in archives.items()},
              'P4_final_acceptance': 'PENDING', 'release_authorized': False,
              'reviewer': 'Integrating agent mechanical frame/source audit; not independent P4 acceptance',
              'input_sha256': {str(p.relative_to(ROOT)): sha(p) for p in inputs}}
    write(HERE / 'acceptance.json', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('archives', 'input_sha256')}, indent=2))


if __name__ == '__main__':
    main()
