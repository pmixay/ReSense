"""Verify the final source/evidence and package exact immutable raw run bytes."""
import hashlib
import json
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET

from run_checks import HERE, ROOT, WORK, sources

sys.path.insert(0, str(ROOT / 'scripts'))
import detector_freeze as freeze  # noqa: E402


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def archive(name, files):
    target = HERE / name
    manifest = {}
    with tarfile.open(target, 'x:gz') as t:
        for path, member in sorted(files, key=lambda pair: pair[1]):
            assert member not in manifest
            manifest[member] = dict(sha256=sha(path), bytes=path.stat().st_size)
            t.add(path, arcname=member)
    with tarfile.open(target) as t:
        actual = {m.name: m for m in t if m.isfile()}
        assert set(actual) == set(manifest)
        for member, info in manifest.items():
            payload = t.extractfile(actual[member]).read()
            assert len(payload) == info['bytes'] and hashlib.sha256(payload).hexdigest() == info['sha256']
    result = dict(file=name, sha256=sha(target), bytes=target.stat().st_size, members=manifest,
                  every_member_reopened_and_verified=True)
    (HERE / (name.removesuffix('.tar.gz') + '-manifest.json')).write_text(json.dumps(result, indent=2) + '\n')
    return {k: result[k] for k in ['file', 'sha256', 'bytes', 'every_member_reopened_and_verified']}


assert subprocess.check_output(['git', 'diff', '--', 'resense', 'native', 'configs',
    'ros2_ws/src/resense_ros/config'], cwd=ROOT) == b''
snapshot = sources(ROOT)
source_commit = subprocess.check_output(['git', 'rev-parse', 'fd89712'], cwd=ROOT, text=True).strip()
for name in ['gate-c-candidate', 'x3-c-candidate', 'supplement-c-candidate-E6',
             'supplement-c-candidate-A-axis', 'supplement-c-candidate-C-person', 'supplement-c-candidate-Falcon']:
    r = read(HERE / f'{name}-execution.json')
    assert r['source_unchanged'] and r['source_sha256'] == snapshot and r['returncode'] == 0
    assert r['commit'] == source_commit
    assert sha(WORK / f'{name}.log') == r['log_sha256']
gate = read(HERE / 'gate-c-candidate.json')
assert not gate['code']['uncommitted_detector_changes'] and gate['gate']['passed']
assert all(not gate['gate'][k] for k in ['allow', 'worse_gated', 'missing_gated', 'worse_allowed', 'missing_allowed'])
assert (ROOT / 'configs/default.yaml').read_bytes() == (ROOT / 'ros2_ws/src/resense_ros/config/detector.yaml').read_bytes()
frozen = freeze.source_hashes(ROOT)
for path, expected in frozen.items():
    assert hashlib.sha256(subprocess.check_output(['git', 'show', f'fd89712:{path}'], cwd=ROOT)).hexdigest() == expected
src = [(ROOT / path, path) for path in frozen]
src += [(ROOT / path, path) for path in ['tests/test_column_collision_core.py', 'tests/fixtures/h1_physical.py',
                                       'resense/_resense_native.so']]
source_archive = archive('final-source.tar.gz', src)
raw_files = [(p, str(p.relative_to(WORK))) for p in WORK.rglob('*')
             if p.is_file() and '__pycache__' not in p.parts]
raw_archive = archive('raw-evidence.tar.gz', raw_files)
assert raw_archive['bytes'] < 95 * 1024 * 1024
audit = read(HERE / 'raw-audit-c.json')
trace = read(HERE / 'axis-trace-c.json')
assert trace['full_plain_traced_equal'] and len(trace['added_matched_states']) == 23
assert trace['added_matched_rows'] == audit['probes']['A-axis']['added_matches']
moving = read(HERE / 'moving-trace-c.json')
moving_summary = []
for case in moving['cases']:
    assert case['plain_traced_equal'] and case['frames'] == 56
    rows = case['rows']
    count = 0
    held = None
    for i, r in enumerate(sorted(rows, key=lambda r: r['distance']), 1):
        count += bool(r['hit'])
        if i >= 5 and count >= .9 * i:
            held = r['distance']
    moving_summary.append(dict(lateral=case['lateral'], speed_mps=22.,
        first_matched_STOP_m=next((r['distance'] for r in rows if r['hit']), None),
        held90_m=held, matched_rows=sum(r['hit'] for r in rows), visible_rows=len(rows)))
tests = {}
for name in ['units-c-final.xml', 'full-tests-c.xml', 'baseline-unrelated-test.xml',
             'timing-reference.xml', 'timing-candidate.xml']:
    root = ET.parse(HERE / name).getroot()
    tests[name] = dict(tests=int(root.find('testsuite').attrib['tests']),
                      failures=[n.attrib['name'] for n in root.iter('testcase') if n.find('failure') is not None],
                      errors=[n.attrib['name'] for n in root.iter('testcase') if n.find('error') is not None])
result = dict(status='P3_AUTHOR_ACCEPTANCE_FOR_BOUNDED_CANDIDATE',
    source_commit=source_commit,
    source_files=frozen, source_fingerprint=freeze.source_digest(frozen),
    independent_P4_review='PENDING', P1_reseal='PENDING', inherited_High_overall='OPEN',
    reproduced_case45='fixed in component and standing full-detector physical controls',
    full_gate=dict(passed=True, ordinary_rows=sum(r['frames'] for r in audit['gate'].values()),
                   set_F_rows=audit['Set_F']['rows'], raw_non_timing_equal=True,
                   non_timing_metrics=audit['gate_non_timing_metrics']),
    X3=dict(cases=len(audit['X3']), rows=sum(r['frames'] for r in audit['X3'].values()),
            raw_non_timing_equal=True),
    physical=audit['physical'], moving_opaque_body=moving_summary, probes=audit['probes'],
    tests=tests, source_archive=source_archive, raw_archive=raw_archive,
    limitations=['Nine long-range physical positive cases remain misses.',
                 'Boundary hull is a consistency guard, not a calibrated true-axis uncertainty bound.',
                 'Moving-body first STOP is not sustained 100 m detection or braking sufficiency.',
                 'Full pytest is not green: inherited proxy-hook failure and a full-run timing failure; isolated timing passes.',
                 'No new ROS/DDS, image, release, J1 or G3 execution.'])
(HERE / 'author-acceptance.json').write_text(json.dumps(result, indent=2) + '\n')
assert snapshot == sources(ROOT)
print('SOURCE', result['source_commit'], result['source_fingerprint'])
print('ARCHIVES', source_archive, raw_archive)
print('MOVING', moving_summary)
print('TESTS', tests)
