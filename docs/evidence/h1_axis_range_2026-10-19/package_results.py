"""Verify source continuity and package complete H1 follow-up run evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET

from run_checks import ROOT, HERE, WORK, archived

sys.path.insert(0, str(ROOT / 'scripts'))
import detector_freeze as freeze  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archive(name, files):
    manifest = {}
    target = HERE / name
    with tarfile.open(target, 'x:gz') as output:
        for path, member in sorted(files, key=lambda pair: pair[1]):
            assert member not in manifest
            manifest[member] = dict(sha256=sha(path), bytes=path.stat().st_size)
            output.add(path, arcname=member, recursive=False)
    with tarfile.open(target) as reopened:
        actual = {m.name: m for m in reopened if m.isfile()}
        assert set(actual) == set(manifest)
        for member, info in manifest.items():
            data = reopened.extractfile(actual[member]).read()
            assert len(data) == info['bytes'] and hashlib.sha256(data).hexdigest() == info['sha256']
    result = dict(file=name, sha256=sha(target), bytes=target.stat().st_size,
                  members=manifest, every_member_reopened_and_verified=True)
    with (HERE / (name.removesuffix('.tar.gz') + '-manifest.json')).open('x') as stream:
        json.dump(result, stream, indent=2)
    return {k: v for k, v in result.items() if k != 'members'}


def main():
    source_commit = subprocess.check_output(['git', 'rev-parse', '8fce584'], cwd=ROOT, text=True).strip()
    snapshot = archived.sources(ROOT)
    receipts = {}
    for name in ['gate-d-candidate', 'probes-d-candidate-A-axis', 'probes-d-candidate-C-person',
                 'probes-d-candidate-E6', 'probes-d-candidate-Falcon', 'trace-d-candidate', 'x3-d2-candidate']:
        receipt = read(HERE / f'{name}-execution.json')
        assert receipt['source_unchanged'] and receipt['source_sha256'] == snapshot and receipt['returncode'] == 0
        assert sha(WORK / f'{name}.log') == receipt['log_sha256']
        assert sha(WORK / f'{name}-source.tar.gz') == receipt['source_archive_sha256']
        receipts[name] = dict(commit=receipt['commit'], source_bytes_match=True)
    frozen = freeze.source_hashes(ROOT)
    for path, expected in frozen.items():
        assert hashlib.sha256(subprocess.check_output(['git', 'show', f'{source_commit}:{path}'], cwd=ROOT)).hexdigest() == expected
    assert (ROOT / 'configs/default.yaml').read_bytes() == (ROOT / 'ros2_ws/src/resense_ros/config/detector.yaml').read_bytes()
    assert read(HERE / 'audit-d-gate.json')['PASS']
    assert read(HERE / 'audit-d-probes.json')['PASS']
    assert read(HERE / 'audit-d2-x3.json')['PASS']
    gate_report = read(HERE / 'gate-d-candidate.json')
    assert gate_report['gate']['passed']
    assert all(not gate_report['gate'][key] for key in ['allow', 'worse_gated', 'missing_gated', 'worse_allowed', 'missing_allowed'])
    physical = read(WORK / 'physical-audit-d.json')
    assert physical['source_unchanged'] and physical['summary']['lost'] == 0
    assert physical['summary']['false_cores'] == physical['summary']['false_stops'] == 0
    trace = read(HERE / 'trace-ranges-d.json')
    assert trace['source_unchanged'] and trace['cases']['A-axis']['full_plain_traced_equal']
    probe_audit = read(HERE / 'audit-d-probes.json')
    added_axis_states = []
    for index in probe_audit['ranges']['A-axis']['added_matches']:
        row = trace['cases']['A-axis']['rows'][index]
        assert row['i'] == index
        reported_ids = {d['id'] for d in row['result']['detections']}
        actual = [a for a in row['assignments'] if a['id'] in reported_ids]
        assert actual
        added_axis_states.append(dict(frame=index, info=row['info'],
            detections=row['result']['detections'], executed_assignment_snapshots=actual))
    tests = {}
    for path in sorted(WORK.glob('*.xml')):
        tree = ET.parse(path).getroot()
        tests[path.name] = dict(tests=sum(int(s.attrib['tests']) for s in tree.iter('testsuite')),
            skipped=sum(int(s.attrib.get('skipped', 0)) for s in tree.iter('testsuite')),
            failures=[dict(classname=c.attrib.get('classname'), name=c.attrib['name'])
                      for c in tree.iter('testcase') if c.find('failure') is not None or c.find('error') is not None])
    final_tests = read(HERE / 'tests-final-d.json')
    assert final_tests['source_unchanged'] and final_tests['skipped'] == 0
    assert final_tests['failures'] == [dict(classname='tests.test_lidar_proxy_hook',
        name='test_child_process_inherits_hook_and_bad_source_fails_closed')]
    base_failures = tests['proxy-base-control.xml']['failures']
    assert base_failures == final_tests['failures']
    source_paths = set(frozen)
    source_paths.add('resense/_resense_native.so')
    source_paths.update(str(p.relative_to(ROOT)) for p in (ROOT / 'tests').rglob('*.py'))
    source_paths.update(str(p.relative_to(ROOT)) for p in (ROOT / 'scripts').glob('*.py'))
    source_paths.update(str(p.relative_to(ROOT)) for p in HERE.glob('*.py'))
    source_paths.update(str(p.relative_to(ROOT)) for p in HERE.glob('*.md'))
    source_paths.update(str(p.relative_to(ROOT)) for p in
        (ROOT / 'docs/evidence/judgement_2026-10-13/scripts').glob('*.py'))
    source_paths.update(['docs/evidence/h1_core_2026-10-19/run_checks.py',
        'docs/evidence/integration_2026-10-16/h3_selected/helpers/frame_diff.py'])
    source_archive = archive('final-source.tar.gz', [(ROOT / path, path) for path in source_paths])
    raw = [(p, str(p.relative_to(WORK))) for p in WORK.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    raw += [(p, 'reports/' + p.name) for p in HERE.glob('*.json') if not p.name.endswith('-manifest.json')]
    raw += [(Path('/tmp/opencode') / name, 'diagnostics/' + name) for name in
        ['h1-axis-diagnosis.json', 'h1-axis-d-diagnosis.json', 'h1-axis-d-diagnosis.log',
         'h1-axis-d-units-first.xml', 'h1-axis-d-units.xml']]
    raw_archive = archive('raw-evidence.tar.gz', raw)
    assert raw_archive['bytes'] < 95 * 1024 * 1024
    gate_audit, x3 = read(HERE / 'audit-d-gate.json'), read(HERE / 'audit-d2-x3.json')
    nominal = read(Path('/tmp/opencode/h1-axis-d-diagnosis.json'))
    moving = []
    for case in nominal['cases']:
        if case['moving']:
            rows = case['rows']
            moving.append(dict(lateral=case['lateral'], matched=sum(r['hit'] for r in rows),
                continuous_from=next((r['distance'] for i, r in enumerate(rows) if all(s['hit'] for s in rows[i:])), None),
                first=next((r['distance'] for r in rows if r['hit']), None)))
    receipt = dict(status='P3_BOUNDED_AUTHOR_CHECKS_COMPLETE_H1_OVERALL_OPEN', source_commit=source_commit,
        source_files=frozen, source_fingerprint=freeze.source_digest(frozen), run_source_continuity=receipts,
        full_gate=dict(ordinary_rows=sum(r['frames'] for r in gate_audit['bags'].values()),
                       set_F_rows=gate_audit['Set_F']['rows'], non_timing_equal=True, metrics=gate_audit['metric_verdicts']),
        X3=dict(cases=len(x3['cases']), rows=sum(r['frames'] for r in x3['cases'].values()), non_timing_equal=True),
        physical=physical['summary'], moving_nominal=moving,
        critical_probes=probe_audit, added_axis_states=added_axis_states, tests=tests,
        full_suite_all_green=final_tests['full_suite_all_green'], source_archive=source_archive, raw_archive=raw_archive,
        independent_P4_review='PENDING', P1_selection_reseal='PENDING', H1_overall='OPEN',
        limitations=['Observed consistency interval is not a calibrated real-world true-axis bound.',
            'The ordinary rail finder can share wrong-pair/route or floor-reference errors with the track model.',
            'No-rail case45 no longer supplies an absolute collision proof; raw hash/shape control is retained.',
            'Three left-137m standing opaque cases have only one matched scan in the fixed 14-scan window.',
            'A-axis injected-body pooled held90 is only 11.02m despite early isolated matches.',
            'Ideal physical scenes establish no real-data 100m braking sufficiency.',
            'Full pytest retains the independently reproduced base proxy-hook assertion failure.'])
    with (HERE / 'author-acceptance.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
    assert archived.sources(ROOT) == snapshot
    print(json.dumps(dict(source_commit=source_commit, fingerprint=receipt['source_fingerprint'],
                          source_archive=source_archive, raw_archive=raw_archive,
                          full_gate=receipt['full_gate'], X3=receipt['X3'], tests=tests), indent=2))


if __name__ == '__main__':
    main()
