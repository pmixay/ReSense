"""Revalidate gate rows and archive exact complete P3 author outputs."""
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET

root = Path('/home/aiops/resense')
here = root / 'docs/evidence/l16_s3_2026-10-19'
work = Path('/tmp/opencode/l16-s3/run4')
reference = Path('/tmp/opencode/l16-s3/reference')
sys.path.insert(0, str(root))
from scripts import detector_freeze as freeze  # noqa: E402
from scripts import regression_gate as gate  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archive(folder, name):
    path = here / (name + '.tar.gz')
    if path.exists():
        raise FileExistsError(path)
    inventory = {}
    with tarfile.open(path, 'w:gz', compresslevel=6) as stream:
        for item in sorted(folder.rglob('*')):
            if item.is_file():
                relative = item.relative_to(folder).as_posix()
                stream.add(item, arcname=relative, recursive=False)
                inventory[relative] = {'bytes': item.stat().st_size, 'sha256': sha(item)}
    with tarfile.open(path) as stream:
        actual = {}
        for item in stream:
            assert item.isfile() and item.name not in actual
            data = stream.extractfile(item).read()
            actual[item.name] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    assert inventory == actual
    receipt = {'archive': path.name, 'sha256': sha(path), 'members': inventory,
               'all_members_reopened_and_verified': True}
    (here / (name + '_manifest.json')).write_text(json.dumps(receipt, indent=2) + '\n')
    return {'path': path.name, 'sha256': receipt['sha256'], 'files': len(inventory)}


def source_archive(files):
    names = [*files, 'resense/_resense_native.so', 'tests/test_calibration.py',
             'tests/test_mount_ring_axis.py', 'tests/test_orientation_health.py',
             'tests/test_orientation_budget.py', 'tests/test_directional_orientation.py',
             'tests/test_directional_history.py', 'tests/test_orientation_numeric.py']
    path = here / 'candidate_source.tar.gz'
    inventory = {}
    with tarfile.open(path, 'w:gz') as stream:
        for name in names:
            stream.add(root / name, arcname=name, recursive=False)
            inventory[name] = sha(root / name)
    with tarfile.open(path) as stream:
        checked = {m.name: hashlib.sha256(stream.extractfile(m).read()).hexdigest() for m in stream}
    assert inventory == checked
    receipt = {'archive': path.name, 'sha256': sha(path), 'members': inventory,
               'all_members_reopened_and_verified': True}
    (here / 'candidate_source_manifest.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return {'path': path.name, 'sha256': receipt['sha256'], 'files': len(names)}


review = read(here / 'raw_review.json')
assert review['passed'] and not review['failures']
execution = read(here / 'gate_execution_v4.json')
assert execution['numpy_version'] == '1.26.4'
assert all(r['returncode'] == 0 and r['source_unchanged'] for r in execution['runs'])
candidate = read(here / 'gate-candidate-v4.json')
control = read(here / 'gate-reference-v2.json')
rows = gate.compare(control, candidate, [])
assert not any(r['fails'] or r['allowed'] for r in rows)
non_timing = [r for r in rows if not r['metric'].startswith('latency_ms.')]
assert len(non_timing) == 208 and all(r['verdict'] == 'same' for r in non_timing)
env = dict(os.environ, OPENBLAS_CORETYPE='Haswell', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
helper = root / 'docs/evidence/lidar_adaptation_2026-10-18/review_gate_frames.py'
command = [sys.executable, str(helper), '--reference', str(here / 'gate-reference-v2.json'),
           '--candidate', str(here / 'gate-candidate-v4.json'),
           '--reference-work', '/tmp/opencode/l16-s3/run2/gate-reference-work',
           '--candidate-work', str(work / 'gate-candidate-work'), '--reference-source', str(reference),
           '--candidate-source', str(root), '--cache', '/tmp/opencode/resense-b4-data/cache',
           '--out', str(here / 'gate_frame_review.json')]
subprocess.run(command, cwd=root, env=env, check=True)
frame_review = read(here / 'gate_frame_review.json')
for case in frame_review['ordinary'].values():
    assert not case['changed_fields'], case['changed_fields']
    assert not case['lost_stop_frames'] and not case['added_stop_frames']
assert not frame_review['set_F_parameter_changes']
assert all(not case['changed_fields'] for case in frame_review['set_F'])
suite = ET.parse(here / 'revision4-tests-final.xml')
testcases = list(suite.iter('testcase'))
assert len(testcases) == 226 and not any(t.find(k) is not None for t in testcases for k in ('failure', 'error', 'skipped'))
old = ET.parse(here / 'rejected-numeric-positive-control.xml')
old_failures = [t for t in old.iter('testcase') if t.find('failure') is not None]
assert old_failures and not list(old.iter('error'))
history_positive = ET.parse(here / 'rejected-history-positive-control.xml')
assert len(list(history_positive.iter('failure'))) == 1 and not list(history_positive.iter('error'))

archives = {}
for path in sorted(work.iterdir()):
    if path.is_dir() and ((path / 'summary.json').exists() or path.name == 'gate-candidate-work'):
        archives[path.name] = archive(path, path.name.replace('-', '_'))
archives['gate-reference-work'] = archive(Path('/tmp/opencode/l16-s3/run2/gate-reference-work'), 'gate_reference_work')
files = freeze.source_hashes(root)
base_files = freeze.source_hashes(reference)
changed = [name for name in files if files[name] != base_files[name]]
assert changed == ['resense/calibration.py', 'resense/detector.py'], changed
archives['source'] = source_archive(files)
for side, source in [('reference', reference), ('candidate', root)]:
    output = here / f'search-{side}-v4.json'
    subprocess.run([sys.executable, str(here / 'bench_search.py'), '--repo', str(source),
                    '--out', str(output)], env=env, check=True)
search = read(here / 'search-candidate-v4.json')
assert search['max_observation_points'] <= 60000
assert search['median_ms'] <= 60, search
result = {'status': 'P3_AUTHOR_CHECKS_PASS', 'base_commit': 'aec88d248fb1a48a275937607bd36c3587dc0dc9',
          'source_sha256': freeze.source_digest(files), 'source_files': files,
          'changed_frozen_files': changed, 'tests_passed': len(testcases),
          'old_numeric_tests_detecting_difference': len(old_failures),
          'gate_rows': frame_review['ordinary_rows'] + frame_review['set_F_rows'],
          'non_latency_gate_metrics_equal': len(non_timing), 'groups': {}, 'archives': archives,
          'search': search,
          'formal_committed_X3': 'NOT_RUN: source is uncommitted',
          'independent_P4_acceptance': 'PENDING', 'reseal': 'P1 after actual committed-source acceptance',
          'limits': review['not_closed']}
for name, group in review['groups'].items():
    result['groups'][name] = {'cases': len(group['cases']), 'frames_per_case': group['frames_per_case'],
                             'stop_count_distribution': dict(Counter(c['STOP_frames'] for c in group['cases'])),
                             'scope': group['scope']}
(here / 'author_acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k not in ('archives', 'source_files')}, indent=2))
