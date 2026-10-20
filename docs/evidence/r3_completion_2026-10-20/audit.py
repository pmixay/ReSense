"""Recount retained rows and source identities, not runner PASS labels."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/r3-completion-work')
sys.path.insert(0, str(ROOT / 'scripts'))
import regression_gate as gate  # noqa: E402
import robustness_battery as battery  # noqa: E402

spec = importlib.util.spec_from_file_location('prior_audit', ROOT / 'docs/evidence/l16_open_air_2026-10-20/audit_results.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


def load(path):
    return json.loads(path.read_text())


def rows(path):
    return [json.loads(line) for line in path.open()]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hit_set(rr, key):
    return {i for i, row in enumerate(rr) if row[key]}


def no_loss(a, b, key):
    lost = hit_set(a, key) - hit_set(b, key)
    assert not lost, (key, sorted(lost))
    return sorted(hit_set(b, key) - hit_set(a, key))


def control(a, key):
    damaged = deepcopy(a)
    first = next(i for i, r in enumerate(a) if r[key])
    damaged[first][key] = False
    try:
        no_loss(a, damaged, key)
    except AssertionError:
        return first
    raise AssertionError('loss control was not detected')


def gates():
    reports = [load(HERE / f'gate-a-{side}.json') for side in ('reference', 'candidate')]
    for report in reports:
        assert report['gate']['passed'] and not report['gate']['allow']
        assert not report['code']['uncommitted_detector_changes'] and not report['config']['set']
    metrics = [{k: v for k, v in gate.metrics(r).items() if not k.startswith('latency_ms.')}
               for r in reports]
    assert metrics[0] == metrics[1]
    dirs = [WORK / f'gate-a-{side}' for side in ('reference', 'candidate')]
    names = sorted(p.name for p in dirs[0].glob('*.jsonl'))
    assert names == sorted(p.name for p in dirs[1].glob('*.jsonl'))
    total = stops = 0
    by_file = {}
    for name in names:
        aa, bb = [rows(d / name) for d in dirs]
        for i, (a, b) in enumerate(zip(aa, bb, strict=True)):
            assert prior.normal(a) == prior.normal(b), (name, i)
        by_file[name] = dict(rows=len(bb), STOP=sum(bool(r['obstacle']) for r in bb))
        total += len(bb)
        stops += by_file[name]['STOP']
    sf = [load(d / 'setF_straight.json') for d in dirs]
    assert sf[0]['sequences'] == sf[1]['sequences']
    for value in sf:
        value['summary'].pop('wall_s')
    assert sf[0]['summary'] == sf[1]['summary']
    positive = next(rows(dirs[0] / name) for name in names if any(r['obstacle'] for r in rows(dirs[0] / name)))
    return dict(equal_non_timing_metrics=len(metrics[0]), ordinary_rows=total, STOP=stops,
                files=by_file, set_F_sequences=len(sf[0]['sequences']),
                set_F_rows=sum(len(s['rows']) for s in sf[0]['sequences']),
                lost_hit_positive_control_frame=control(positive, 'obstacle'),
                ride=reports[1]['ride'])


def replay():
    reports = [load(WORK / f'x3-a-{side}.json') for side in ('reference', 'candidate')]
    for report in reports:
        battery.validated_entries(report, Path('/tmp/opencode/resense-b4-data/decoded'), ROOT)
    assert reports[1]['status'] == 'PASS'
    counts = {}
    total = comparisons = 0
    for key, entry in reports[1]['entries'].items():
        old = reports[0]['entries'][key]
        aa, bb = [rows(Path(e['raw_path'])) for e in (old, entry)]
        for a, b in zip(aa, bb, strict=True):
            for field in ('i', 'stamp', 'decision', 'obstacle', 'dets', 'warns', 'dlevel', 'clear', 'mount', 'mount_h'):
                assert a[field] == b[field], (key, a['i'], field)
        calc = battery.compare_metrics(old['metrics'], entry['metrics'])
        assert all(r['passed'] for r in calc)
        total += len(bb)
        comparisons += len(calc)
        counts[key] = dict(rows=len(bb), STOP=sum(r['obstacle'] for r in bb))
    aa, bb = [rows(WORK / f'falcon-a-{side}.jsonl') for side in ('reference', 'candidate')]
    assert len(aa) == len(bb) == 4443
    for a, b in zip(aa, bb, strict=True):
        for field in ('i', 'stamp', 'decision', 'obstacle', 'dets', 'warns', 'dlevel', 'clear', 'mount', 'mount_h'):
            assert a[field] == b[field], ('falcon', a['i'], field)
    positive = reports[0]['entries']['doubleT_obstacle/nominal']['metrics']
    damaged = deepcopy(positive)
    damaged['stop_frames'] -= 3
    assert any(not r['passed'] for r in battery.compare_metrics(positive, damaged))
    hanging = reports[1]['entries']['cloud_with_fake_obj/nominal']['metrics']['objects']['thin_hanging']
    assert hanging['first_stop_m'] == 48.19 and hanging['stop_rows'] == 19
    return dict(cases=counts, rows=total, comparisons=comparisons, lost_STOP_or_payload=0,
                metric_loss_control_detected=True,
                falcon=dict(rows=len(bb), decisions=dict(Counter(r['decision'] for r in bb))),
                hanging_float32=hanging)


def analytic():
    aa, bb = [load(WORK / f'analytic-a-{side}.json')['cases'] for side in ('reference', 'candidate')]
    details = {}
    for name, b in bb.items():
        a = aa[name]
        for ar, br in zip(a['rows'], b['rows'], strict=True):
            assert ar['xyz_sha256'] == br['xyz_sha256'] and ar['box'] == br['box']
            for detection in ar['result']['detections']:
                assert detection in br['result']['detections'], (name, ar['frame'], detection)
        added = no_loss(a['rows'], b['rows'], 'matched')
        # Labels are independently derived from the known box relative to rails,
        # not from the detector's STOP or the ego-veto verdict.
        physical_positive = []
        for r in b['rows']:
            inside = False
            for x0, x1, y0, y1, z0, z1 in r['box']:
                inside |= (x1 > 0 and y0 < .25 + 1.05 and y1 > .25 - 1.05
                           and z1 > -1.5 + .18 + .12 and z0 < -1.5 + .18 + 3.)
            physical_positive.append(bool(inside))
            if name.endswith('outside') or name == 'empty':
                assert not inside and not r['matched'] and not r['result']['obstacle']
        on = [r['frame'] for r in b['rows'] if r['matched']]
        details[name] = dict(before=[r['frame'] for r in a['rows'] if r['matched']], after=on,
                             added=added, physically_in_gauge=sum(physical_positive))
    for data in (aa, bb):
        plain = data['tall-80-approach-known-on']['rows']
        traced = data['trace-control']['rows']
        for a, b in zip(plain, traced, strict=True):
            assert prior.normal(a['result']) == prior.normal(b['result'])
            assert a['tracks'] == b['tracks']
        assert any(r['trace'] for r in traced)
    far = bb['tall-80-approach-known-on']['rows']
    r = far[2]
    tr = next(t for t in r['tracks'] if t['cable_kind'] == 1)
    assert tr['cluster']['n_raw'] > len(tr['cluster']['points_idx'])
    support = tr['cluster']['current_support']
    assert support['height'] >= 1.5 and support['n_gauge'] >= 8 and support['footprint'] <= .15
    trace = bb['trace-control']['rows'][2]['trace']
    assert any(e['function'] == '_cable_kind' and e['returned'] == 1 for e in trace)
    assert any(e['function'] == '_cable_confirmed' and e['returned'] is True for e in trace)
    examples = []
    for name, k in [('tall-80-approach-known-on', 2), ('tall-80-carried-known-on', 5),
                    ('hanging-37-carried-on', 3), ('tall-outside', 5)]:
        row = bb[name]['rows'][k]
        examples.append(dict(case=name, frame=k, boxes=row['box'], raw_points=row['physical_points'][:8],
                             matched=row['matched'], tracks=[{k: t[k] for k in
                                 ('hits', 'cable_kind', 'cable_hits', 'carried_along', 'zone', 'reported')}
                                 for t in row['tracks']]))
    return dict(cases=details, paired_rows=sum(len(c['rows']) for c in bb.values()),
                plain_traced_equal_rows=36, accumulated_frame2_support=support, raw_examples=examples,
                planted_loss_detected_at=control(bb['tall-80-approach-known-on']['rows'], 'matched'))


def plots():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    data = load(WORK / 'analytic-a-candidate.json')['cases']
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, name, k in zip(axes, ['tall-80-approach-known-on', 'hanging-37-carried-on', 'tall-outside'],
                           [2, 3, 5], strict=True):
        row = data[name]['rows'][k]
        p = np.array(row['physical_points'])
        if p.size:
            ax.scatter(p[:, 1] - .25, p[:, 2] + 1.32, s=12, label='raw physical returns')
        ax.plot([-1.05, -1.05, 1.05, 1.05, -1.05], [.12, 3, 3, .12, .12], 'k--', label='physical envelope')
        box = row['box'][0]
        ax.plot([box[2]-.25, box[2]-.25, box[3]-.25, box[3]-.25, box[2]-.25],
                [box[4]+1.32, box[5]+1.32, box[5]+1.32, box[4]+1.32, box[4]+1.32], 'r-')
        ax.set(title=f'{name}, frame {k}\nmatched STOP: {row["matched"]}', xlabel='lateral from rails (m)',
               ylabel='height above rail head (m)', xlim=(-1.3, 2.3), ylim=(-.1, 5.5))
        ax.grid(True)
    fig.tight_layout()
    fig.savefig(HERE / 'raw-cable-controls.png', dpi=150)
    return dict(image='raw-cable-controls.png', physical_cases=3)


def ranges():
    aa, bb = [load(WORK / f'range-a-{side}.json') for side in ('reference', 'candidate')]
    assert aa == bb
    visible = [r for r in bb['rows'] if r['X'] is not None and r['X'] > 3 and r['n_obj'] > 0]
    hits = [r for r in visible if r['hit']]
    assert len(visible) == 59 and len(hits) == 34
    assert hits[0]['X'] == bb['summary']['first_stop_X'] == 86.25
    held, n = None, 0
    for i, r in enumerate(sorted(visible, key=lambda r: r['X']), 1):
        n += bool(r['hit'])
        if 10 * n >= 9 * i:
            held = r['X']
    assert held == bb['summary']['held_from_X'] == 61.28
    return dict(equal_rows=len(bb['rows']), visible=len(visible), hit=len(hits), first=86.25, held=held)


def sources():
    results = {}
    for path in HERE.glob('*-execution.json'):
        receipt = load(path)
        assert receipt['source_unchanged']
        archive = WORK / (receipt['name'] + '-source.tar.gz')
        assert sha(archive) == receipt['source_archive_sha256']
        assert sha(WORK / (receipt['name'] + '.log')) == receipt['log_sha256']
        with tarfile.open(archive) as tar:
            assert set(tar.getnames()) == set(receipt['source_sha256'])
            for name, digest in receipt['source_sha256'].items():
                assert hashlib.sha256(tar.extractfile(name).read()).hexdigest() == digest
        if receipt['name'].endswith('candidate'):
            assert all(sha(ROOT / name) == digest for name, digest in receipt['source_sha256'].items())
        results[receipt['name']] = dict(commit=receipt['commit'], exit=receipt['returncode'],
                                       source_members=len(receipt['source_sha256']))
    # Independent Git check covers all production files, including files outside
    # the receipt suffix filter (models, launch files and build inputs).
    subprocess.run(['git', 'diff', '--exit-code', '0a472d6', 'HEAD', '--',
                    'resense', 'native', 'configs', 'ros2_ws/src/resense_ros', 'pyproject.toml', 'setup.py'],
                   cwd=ROOT, check=True)
    return results


def tests():
    reports = {}
    for path in WORK.glob('tests-*-candidate.xml'):
        cases = list(ET.parse(path).iter('testcase'))
        failures = [c.attrib for c in cases if c.find('failure') is not None or c.find('error') is not None]
        reports[path.name] = dict(cases=len(cases), failures=failures,
                                 skipped=sum(c.find('skipped') is not None for c in cases))
        if path.name == 'tests-merged-candidate.xml':
            modules = {'test_' + module for module in (
                'cable_current_support', 'cable_confirmation', 'ego_veto', 'explained_run',
                'thin_hanging', 'fresh_stop_evidence', 'far_thin', 'near_escalation',
                'column_collision_core', 'column_axis_anchor', 'column_free_top', 'h4_spare_rearm',
                'modules', 'core', 'algorithm', 'native', 'low_height_keep', 'f1a_b1')}
            affected = [c for c in cases if any(m in c.attrib['classname'].split('.') for m in modules)]
            assert len(affected) >= 200
            assert all(c.find('failure') is None and c.find('error') is None and c.find('skipped') is None
                       for c in affected)
            reports[path.name]['affected_passed'] = len(affected)
            assert len(failures) == 1 and failures[0]['name'] == 'test_child_process_inherits_hook_and_bad_source_fails_closed'
    for side in ('reference', 'candidate'):
        cases = list(ET.parse(WORK / f'diagnose-merged-{side}.xml').iter('testcase'))
        failed = [c.attrib['name'] for c in cases if c.find('failure') is not None]
        assert failed == ['test_child_process_inherits_hook_and_bad_source_fails_closed']
        reports[f'diagnose-{side}'] = dict(passed=2, failed=failed)
    return reports


if __name__ == '__main__':
    checks = dict(gate=gates, replay=replay, analytic=analytic, range=ranges, sources=sources, tests=tests, plots=plots)
    p = argparse.ArgumentParser()
    p.add_argument('phase', choices=checks)
    p.add_argument('--revision', default='')
    a = p.parse_args()
    result = checks[a.phase]()
    suffix = f'-{a.revision}' if a.revision else ''
    with (HERE / f'audit-{a.phase}{suffix}.json').open('x') as stream:
        json.dump(result, stream, indent=2)
    print(json.dumps(result, indent=2))
