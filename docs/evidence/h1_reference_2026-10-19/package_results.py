"""Verify and package the retained H1 repair plus rejected reference attempts."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

from run_checks import ROOT, HERE, WORK, archived
from audit_results import old as audit_tools

spec = importlib.util.spec_from_file_location('h1_d_packager', ROOT / 'docs/evidence/h1_axis_range_2026-10-19/package_results.py')
old_package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old_package)
old_package.HERE = HERE
sys.path.insert(0, str(ROOT / 'scripts'))
import detector_freeze as freeze  # noqa: E402


def read(path):
    return json.loads(path.read_text())


def main():
    commit = subprocess.check_output(['git', 'rev-parse', '7d0f571'], cwd=ROOT, text=True).strip()
    snapshot = archived.sources(ROOT)
    receipts = {}
    for name in ['gate-e-candidate', 'probes-e-candidate-A-axis', 'probes-e-candidate-C-person',
                 'probes-e-candidate-E6', 'probes-e-candidate-Falcon', 'trace-e-candidate', 'x3-e-candidate']:
        row = read(HERE / f'{name}-execution.json')
        assert row['commit'] == commit and row['returncode'] == 0 and row['source_unchanged']
        assert row['source_sha256'] == snapshot
        assert old_package.sha(WORK / f'{name}.log') == row['log_sha256']
        receipts[name] = dict(commit=row['commit'], source_bytes_match=True)
    gate, probes, x3 = (read(HERE / f'audit-e-{phase}.json') for phase in ['gate', 'probes', 'x3'])
    assert gate['PASS'] and probes['PASS'] and x3['PASS']
    assert read(HERE / 'gate-e-candidate.json')['gate']['passed']
    physical = read(HERE / 'physical-e.json')
    assert physical['summary'] == dict(previous_matches=293, matched=320, outside_cases=280, false_STOP=0, moving_cases=12)
    assert all(c['matched'] == list(range(4, 14)) for c in physical['full'])
    trace = read(HERE / 'trace-ranges-e.json')
    assert trace['source_unchanged'] and trace['cases']['A-axis']['full_plain_traced_equal']
    # Comparator controls use captured positive detections, not a claimed hit bit.
    known = next(r['result'] for r in trace['cases']['A-axis']['rows'] if r['result']['detections'])
    planted = deepcopy(known)
    planted['detections'], planted['obstacle'] = [], False
    delta = audit_tools.compare([known], [planted], 'stamp', 'detections')
    assert delta['lost_STOP'] and delta['lost_payloads']
    planted = deepcopy(known)
    planted['track']['center'] += .01
    assert audit_tools.compare([known], [planted], 'stamp', 'detections')['changed_non_timing_rows']
    # F had no measurable benefit on the fixed screen and is not retained.
    f_range = read(WORK / 'f-screen-A.json')
    e_range = read(WORK / 'probes-e-candidate/A-axis.json')
    assert f_range == e_range
    f_physical = read(HERE / 'physical-f-screen.json')
    assert all(a['rows'] == b['rows'] for a, b in zip(physical['full'], f_physical['full'], strict=True))
    assert physical['moving'] == f_physical['moving']
    f_repo = Path('/tmp/opencode/h1-f-candidate')
    f_snapshot = archived.sources(f_repo)
    changed_f = [p for p in snapshot if snapshot[p] != f_snapshot[p]]
    assert changed_f == ['resense/clustering.py']
    reference = read(HERE / 'reference-validation.json')
    assert len(reference['rows']) == 36 and 'accepted' not in reference['gates']
    assert reference['nonzero_positive_control']['executed_gate'] == 'accepted'
    deskew = read(HERE / 'reference-validation-deskew.json')
    assert len(deskew['rows']) == 36 and 'accepted' not in deskew['gates']
    assert deskew['nonzero_positive_control']['executed_gate'] == 'accepted'
    assert sum(len(read(HERE / f'timestamp-alignment-{name}.json')) for name in ['A', 'C']) == 608
    inventory = read(HERE / 'raw-topic-inventory-checked.json')
    assert all(r['orphan_messages'] == 0 and r['total_messages'] == sum(t['messages'] for t in r['topics']) for r in inventory)
    tests = read(HERE / 'tests-e.json')
    assert tests['source_unchanged'] and tests['skipped'] == 0
    assert tests['failures'] == [dict(classname='tests.test_lidar_proxy_hook',
        name='test_child_process_inherits_hook_and_bad_source_fails_closed')]
    parsed = {}
    for path in WORK.glob('*.xml'):
        xml = ET.parse(path).getroot()
        parsed[path.name] = dict(tests=sum(int(s.attrib['tests']) for s in xml.iter('testsuite')),
            failures=[c.attrib['name'] for c in xml.iter('testcase') if c.find('failure') is not None or c.find('error') is not None])
    frozen = freeze.source_hashes(ROOT)
    for path, expected in frozen.items():
        assert hashlib.sha256(subprocess.check_output(['git', 'show', f'{commit}:{path}'], cwd=ROOT)).hexdigest() == expected
    assert (ROOT / 'configs/default.yaml').read_bytes() == (ROOT / 'ros2_ws/src/resense_ros/config/detector.yaml').read_bytes()
    source_paths = set(frozen) | {'resense/_resense_native.so'}
    source_paths.update(str(p.relative_to(ROOT)) for folder in ['tests', 'scripts'] for p in (ROOT / folder).rglob('*.py'))
    source_paths.update(str(p.relative_to(ROOT)) for p in HERE.glob('*.py'))
    source_paths.update(str(p.relative_to(ROOT)) for p in HERE.glob('*.md'))
    for directory in ['docs/evidence/judgement_2026-10-13/scripts', 'docs/evidence/h1_axis_range_2026-10-19',
                      'docs/evidence/h1_core_2026-10-19', 'docs/evidence/integration_2026-10-16/h3_selected/helpers']:
        source_paths.update(str(p.relative_to(ROOT)) for p in (ROOT / directory).glob('*.py'))
    source_archive = old_package.archive('final-source.tar.gz', [(ROOT / p, p) for p in source_paths])
    raw = [(p, str(p.relative_to(WORK))) for p in WORK.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    raw += [(p, 'reports/' + p.name) for p in HERE.glob('*.json') if not p.name.endswith('-manifest.json')]
    raw.append((f_repo / 'resense/clustering.py', 'rejected-F/resense/clustering.py'))
    raw_archive = old_package.archive('raw-evidence.tar.gz', raw)
    assert raw_archive['bytes'] < 95 * 1024 * 1024
    result = dict(status='H1_OPEN_BLOCKED_INDEPENDENT_FAR_AXIS_REFERENCE', source_commit=commit,
        source_files=frozen, source_fingerprint=freeze.source_digest(frozen), run_source_continuity=receipts,
        physical=physical['summary'], stationary_after_confirmation='all32 cases match every scan4..13',
        moving=[dict(geometry=c['geometry'], lateral=c['lateral'], continuous_from=c['continuous_from']) for c in physical['moving']],
        full_gate=dict(PASS=True, rows=sum(d['frames'] for d in gate['bags'].values()) + gate['Set_F_rows'],
                       metrics=gate['metric_verdicts'], non_timing_equal=True),
        X3=dict(PASS=True, cases=len(x3['cases']), rows=sum(c['frames'] for c in x3['cases'].values()), non_timing_equal=True),
        critical_probes=probes, tests=parsed, full_pytest_all_green=tests['all_green'],
        reference_status=reference['status'], reference_checks=reference['gates'], deskew_reference_checks=deskew['gates'],
        nonzero_reference_control='accepted', rejected_F='no output differences on A-axis and fixed physical screen',
        source_archive=source_archive, raw_archive=raw_archive, independent_P4_review='PENDING', P1_selection_reseal='PENDING',
        blocking_inputs=['Independent surveyed/annotated far track axis or a synchronized independently validated trajectory.',
                         'Current LiDAR-only retrospective reconstructions failed real cross-view validation.'],
        limitations=['Real far-axis error percentiles from both attempted reconstructions are unverified and not accepted.',
                     '63 A-axis visible unmatched rows remain; this injection follows the baseline detector axis.',
                     'No-rail scenes and plausible wrong-pair/route errors still lack a universal collision proof.',
                     'Additional-rail controls select the correct pair; they do not validate wrong-pair recovery.',
                     'No real-world 100m range or braking sufficiency is established.'])
    with (HERE / 'author-acceptance.json').open('x') as stream:
        json.dump(result, stream, indent=2)
    assert archived.sources(ROOT) == snapshot
    print(json.dumps(dict(commit=commit, fingerprint=result['source_fingerprint'], physical=result['physical'],
        source_archive=source_archive, raw_archive=raw_archive, tests=parsed, reference=reference['gates']), indent=2))


if __name__ == '__main__':
    main()
