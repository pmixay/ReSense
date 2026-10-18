"""Revalidate the version-only gate and archive its exact completed inputs/outputs."""
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
DATA = Path('/home/resense/data')
SOURCE = DATA / 'version_1_2_0_candidate'
COMMIT = 'e9d8fc649f2dd51dd5cd1e4b04ac8c306cc02569'
WORK = DATA / 'version_1_2_0_gate_work'
REFERENCE = ROOT / 'docs/evidence/lidar_adaptation_2026-10-18/default_off'
REFERENCE_WORK = DATA / 'final_gate_work_cecab1b'
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]

from scripts import detector_freeze as freeze  # noqa: E402
from scripts import regression_gate as gate  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def spans(rows):
    result = []
    for i, row in enumerate(rows):
        if row['obstacle']:
            if result and result[-1][1] == i - 1:
                result[-1][1] = i
            else:
                result.append([i, i])
    return result


def main():
    status_path = DATA / 'version_1_2_0_gate_status.json'
    status = read(status_path)
    assert status['status'] == 'finished' and status['returncode'] == 0
    assert status['source_commit'] == COMMIT and status['source_unchanged'] and status['native_unchanged']
    assert status['source_files'] == freeze.source_hashes(SOURCE) == freeze.source_hashes(ROOT)
    assert freeze.source_digest(status['source_files']) == status['source_sha256']
    for name, digest in status['source_files'].items():
        blob = subprocess.check_output(['git', 'show', f'{COMMIT}:{name}'], cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == digest
    for name, digest in status['native_libraries'].items():
        assert sha(SOURCE / name) == digest
    assert status['native_libraries'] == {
        str(path.relative_to(SOURCE)): sha(path) for path in (SOURCE / 'resense').glob('*.so')}
    for name, digest in status['input_receipt_sha256'].items():
        assert sha(Path(name)) == digest
    assert sha(HERE / 'gate.json') == status['report_sha256']
    assert sha(DATA / 'run_version_1_2_0_gate.py') == status['wrapper_sha256']
    report = read(HERE / 'gate.json')
    assert report['code']['commit'] == COMMIT and report['code']['uncommitted_detector_changes'] == []
    baseline_path = SOURCE / 'docs/evidence/results/regression_baseline_2026-09-29_shell_off.json'
    baseline = read(baseline_path)
    freeze.check_gate(baseline, report, status['source_files'][freeze.CONFIG])
    rebuilt = gate.gate_summary(gate.compare(baseline, report, []), baseline, report['gate']['baseline'], [])
    assert rebuilt == report['gate']
    helper = ROOT / 'docs/evidence/lidar_adaptation_2026-10-18/review_gate_frames.py'
    command = [sys.executable, str(helper), '--reference', str(REFERENCE / 'gate.json'),
               '--candidate', str(HERE / 'gate.json'), '--reference-work', str(REFERENCE_WORK),
               '--candidate-work', str(WORK), '--reference-source', str(DATA / 'final_lidar_cecab1b'),
               '--candidate-source', str(SOURCE), '--cache', str(DATA / 'gate_cache'),
               '--out', str(HERE / 'gate_frame_review.json')]
    env = {**os.environ, 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
           'MKL_NUM_THREADS': '1', 'OPENBLAS_CORETYPE': 'Haswell'}
    subprocess.run(command, check=True, cwd=ROOT, env=env)
    review = read(HERE / 'gate_frame_review.json')
    assert review['ordinary_rows'] == 15269 and review['set_F_rows'] == 3060
    for case in review['ordinary'].values():
        assert not any(case[key] for key in ('changed_fields', 'lost_stop_frames', 'added_stop_frames',
            'frames_with_changed_or_missing_old_detection_payload', 'unconfirmed_orientation_guard_violations'))
    for case in review['set_F']:
        assert not any(case[key] for key in ('changed_fields', 'lost_hits', 'added_hits'))
    assert review['set_F_parameter_changes'] == []
    assert not any(row['fails'] or row['allowed'] for row in review['gate_metrics'])
    assert all(row['verdict'] == 'same' or row['metric'].startswith('latency_ms.')
               for row in review['gate_metrics'])
    pieces = []
    for name in sorted(review['candidate_raw_hashes']):
        left, right = ([json.loads(line) for line in (folder / name).read_text().splitlines()]
                       for folder in (REFERENCE_WORK, WORK))
        assert spans(left) == spans(right)
        assert [row['obstacle'] for row in left] == [row['obstacle'] for row in right]
        pieces.append({'capture': name, 'rows': len(right), 'stop_frames': sum(r['obstacle'] for r in right),
                       'stop_intervals': spans(right), 'all_stop_boundaries_identical': True})
    assert sum(p['rows'] for p in pieces) == 15269
    assert sum(p['stop_frames'] for p in pieces) == 805
    assert sum(len(p['stop_intervals']) for p in pieces) == 51

    members = {f'gate/work/{p.name}': p for p in WORK.iterdir() if p.is_file()}
    members.update({'gate/report.json': HERE / 'gate.json', 'gate/run/status.json': status_path,
                    'gate/run/wrapper.py': DATA / 'run_version_1_2_0_gate.py',
                    'gate/run/console.txt': DATA / 'logs/version_1_2_0_gate.log',
                    'gate/run/wrapper_console.txt': DATA / 'logs/version_1_2_0_wrapper.log'})
    members.update({f'gate/intake/{Path(path).name}': Path(path) for path in status['input_receipt_sha256']})
    archive_path = HERE / 'raw/gate.tar.gz'
    archive_path.parent.mkdir(exist_ok=True)
    manifest = []
    with archive_path.open('xb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0) as stream:
            with tarfile.open(fileobj=stream, mode='w') as archive:
                for name, path in sorted(members.items()):
                    assert path.is_file() and not path.is_symlink()
                    info = archive.gettarinfo(str(path), arcname=name)
                    info.uid = info.gid = info.mtime = 0
                    info.uname = info.gname = ''
                    with path.open('rb') as source:
                        archive.addfile(info, source)
                    manifest.append({'member': name, 'source': str(path), 'bytes': path.stat().st_size,
                                     'sha256': sha(path)})
    expected = {row['member']: row for row in manifest}
    seen = set()
    with tarfile.open(archive_path, 'r:gz') as archive:
        for info in archive:
            assert info.isfile() and info.name not in seen and info.name in expected
            row = expected[info.name]
            assert info.size == row['bytes']
            with archive.extractfile(info) as stream:
                assert hashlib.sha256(stream.read()).hexdigest() == row['sha256']
            seen.add(info.name)
    assert seen == set(expected)
    write(HERE / 'raw/gate_manifest.json', {'archive_sha256': sha(archive_path),
          'archive_bytes': archive_path.stat().st_size, 'members': manifest, 'member_count': len(manifest),
          'all_members_reopened_and_verified': True})
    (HERE / 'gate_execution.json').write_bytes(status_path.read_bytes())
    result = {'status': 'COMPLETE_GATE_AND_VERSION_ONLY_PARITY_PASS',
              'reviewed_utc': datetime.now(timezone.utc).isoformat(), 'source_commit': COMMIT,
              'source_sha256': status['source_sha256'], 'ordinary_rows': 15269, 'set_F_rows': 3060,
              'ordinary_stop_frames': 805, 'ordinary_stop_intervals': 51, 'pieces': pieces,
              'all_shared_non_timing_fields_exact': True, 'all_set_F_rows_exact': True,
              'p4_final_review': 'PENDING; this is an agent evidence-integrity review, not P4 approval',
              'set_F_limit': review['set_F_limit'], 'exclusions': review['exclusions'],
              'input_sha256': {str(p): sha(p) for p in (Path(__file__), helper, HERE / 'gate.json',
                  HERE / 'gate_frame_review.json', HERE / 'gate_execution.json',
                  HERE / 'raw/gate_manifest.json', REFERENCE / 'gate.json')}}
    write(HERE / 'gate_acceptance.json', result)
    print(json.dumps({key: result[key] for key in ('status', 'source_commit', 'ordinary_rows',
                      'set_F_rows', 'ordinary_stop_frames', 'ordinary_stop_intervals')}))


if __name__ == '__main__':
    main()
