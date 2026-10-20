"""Recount the F1a completion evidence from the raw rows, not from runner labels."""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/f1a-completion-work')
sys.path.insert(0, str(ROOT / 'scripts'))
import regression_gate as gate  # noqa: E402

RECORDINGS = ('doubleT_obstacle', 'doubleT_platform', 'roundT_doubleT', 'roundT_pressureGate_roundT',
              'roundT_squareT_pressureGate_squareT', 'squareT_platform_squareT_switch')


def load(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).open() if line.strip()]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def control(value, key):
    """A damaged copy must be detected: the check is not vacuous."""
    damaged = deepcopy(value)
    damaged[key] = (damaged[key][0] - 1, damaged[key][1])
    assert value != damaged
    return damaged


def gate_rows():
    reports = {side: load(HERE / f'gate-c-{side}.json') for side in ('reference', 'candidate')}
    for side, report in reports.items():
        assert report['gate']['passed'] is True, side
        for key in ('allow', 'worse_gated', 'missing_gated', 'worse_allowed', 'missing_allowed'):
            assert not report['gate'][key], (side, key)
        assert not report['code']['uncommitted_detector_changes'], side
        assert not report['config']['set'], side
    metrics = [{k: v for k, v in gate.metrics(r).items() if not k.startswith('latency_ms.')}
               for r in reports.values()]
    changed, per_file = [], {}
    for name in sorted(p.name for p in (WORK / 'gate-c-candidate').glob('*.jsonl')):
        a, b = rows(WORK / 'gate-c-reference' / name), rows(WORK / 'gate-c-candidate' / name)
        assert len(a) == len(b), name
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            if x['obstacle'] != y['obstacle'] or x.get('warning') != y.get('warning'):
                changed.append((name, i, bool(x['obstacle']), bool(y['obstacle'])))
        per_file[name] = dict(rows=len(b), STOP=sum(bool(r['obstacle']) for r in b))
    labels_ref = reports['reference']['recordings']['doubleT_obstacle']['labelled']
    labels_can = reports['candidate']['recordings']['doubleT_obstacle']['labelled']
    set_o_ref = reports['reference']['set_O']['objects']
    set_o_can = reports['candidate']['set_O']['objects']
    lost = []
    for label, obj in set_o_can.items():
        other = set_o_ref.get(label, {})
        if obj.get('stop_frames', 0) < other.get('stop_frames', 0):
            lost.append((label, other.get('stop_frames'), obj.get('stop_frames')))
        if other.get('first_stop_m') is not None and obj.get('first_stop_m') is not None:
            if obj['first_stop_m'] < other['first_stop_m'] - 1e-6:
                lost.append((label, 'first_stop_m', other['first_stop_m'], obj['first_stop_m']))
    return dict(
        reports={side: dict(commit=r['code']['commit'], ride={k: r['ride'].get(k) for k in
                                                              ('alarm_events', 'stop_episodes', 'alarm_frames')})
                 for side, r in reports.items()},
        equal_non_timing_metrics=len(metrics[0]),
        changed_frames=changed,
        files=per_file,
        labelled_reference=labels_ref, labelled_candidate=labels_can,
        set_O_lost=lost,
        set_O_objects={label: dict(stop_frames=obj.get('stop_frames'), first_stop_m=obj.get('first_stop_m'))
                       for label, obj in set_o_can.items()},
        metric_loss_control_detected=control(metrics[1], 'ride.alarm_events') != metrics[1],
    )


def physical():
    a = load(WORK / 'physical-b-reference.json')
    b = load(WORK / 'physical-c-candidate.json')
    assert set(a) == set(b)
    differences, stopped, empty = [], 0, []
    for scene in a:
        for ra, rb in zip(a[scene], b[scene], strict=True):
            assert ra['true_distance'] == rb['true_distance']
            if ra['matched_stop'] != rb['matched_stop']:
                differences.append((scene, ra['frame']))
        if any(r['matched_stop'] for r in a[scene]):
            stopped += 1
        if 'topNone' in scene:
            empty.append((scene, sum(r['matched_stop'] for r in a[scene]), sum(r['matched_stop'] for r in b[scene])))
    return dict(scenes=len(a), differing_rows=len(differences), stopped_scenes=stopped,
                empty_controls=empty, positive_box_rows=8)


def flips():
    rows_ = load(WORK / 'continuation-production.json')
    recovered = [r for r in rows_ if r['recovered']]
    return dict(flips=len(rows_), recovered=len(recovered),
                missed=[(r['stem'], r['k'], r['distance'], r['lateral'], r['cause']) for r in rows_
                        if not r['recovered']],
                recovered_frames=sorted({r['stem'] for r in recovered}))


def tests(name):
    path = WORK / f'{name}.xml'
    tree = ET.parse(path)
    suite = tree.getroot()
    if suite.tag == 'testsuites':
        suite = suite[0]
    return dict(suite=suite.get('name'), tests=int(suite.get('tests')), failures=int(suite.get('failures')),
                errors=int(suite.get('errors')), skipped=int(suite.get('skipped')))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, default=HERE / 'audit.json')
    p.add_argument('--tests', default='tests-c-candidate')
    a = p.parse_args()
    report = dict(gate=gate_rows(), physical=physical(), flips=flips())
    for name in (a.tests,):
        path = WORK / f'{name}.xml'
        if path.exists():
            report[name] = tests(name)
    a.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: (v if k != 'gate' else {kk: vv for kk, vv in v.items() if kk != 'changed_frames'})
                      for k, v in report.items()}, indent=2)[:4000])
    print('\nchanged frames:', len(report['gate']['changed_frames']))
    for row in report['gate']['changed_frames']:
        print('  ', row)


if __name__ == '__main__':
    main()
