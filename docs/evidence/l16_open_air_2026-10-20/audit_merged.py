"""Final committed merge: rederive checks and compare with F1a's retained raw run."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import audit_results as audit

HERE, WORK = audit.HERE, audit.WORK
PRIOR = Path('/tmp/opencode')


def checked_F1a_path(path):
    directory = audit.ROOT / 'docs/evidence/f1a_b1_2026-10-20'
    if not directory.exists():
        directory = Path('/tmp/opencode/l16-final-checkout/docs/evidence/f1a_b1_2026-10-20')
    manifest = {entry['path']: entry for entry in audit.load(directory / 'raw-manifest.json')}
    name = str(path.relative_to(PRIOR))
    assert audit.sha(path) == manifest[name]['sha256'], name
    return path


def gate():
    current = audit.load(HERE / 'gate-merged-candidate.json')
    previous = audit.load(checked_F1a_path(PRIOR / 'f1a-b1-gate-final.json'))
    assert current['gate']['passed'] and not current['gate']['allow']
    assert not current['code']['uncommitted_detector_changes'] and current['native']['path'] == 'native'
    metrics = [{k: v for k, v in audit.gate.metrics(r).items() if not k.startswith('latency_ms.')}
               for r in (previous, current)]
    assert metrics[0] == metrics[1]
    directories = [PRIOR / 'f1a-b1-gate-final-work', WORK / 'gate-merged-candidate']
    names = sorted(p.name for p in directories[0].glob('*.jsonl'))
    assert names == sorted(p.name for p in directories[1].glob('*.jsonl')) and len(names) == 15
    count = 0
    for name in names:
        checked_F1a_path(directories[0] / name)
        aa, bb = [audit.rows(d / name) for d in directories]
        for index, (a, b) in enumerate(zip(aa, bb, strict=True)):
            assert audit.normal(a) == audit.normal(b), (name, index)
            count += 1
    checked_F1a_path(directories[0] / 'setF_straight.json')
    sf = [audit.load(d / 'setF_straight.json') for d in directories]
    assert sf[0]['sequences'] == sf[1]['sequences']
    for value in sf:
        value['summary'].pop('wall_s')
    assert sf[0]['summary'] == sf[1]['summary']
    return {'passed_without_waivers': True, 'commit': current['code']['commit'],
            'equal_F1a_author_non_timing_metrics': len(metrics[1]), 'equal_F1a_author_ordinary_rows': count,
            'equal_set_F_sequences': len(sf[1]['sequences']),
            'equal_set_F_rows': sum(len(s['rows']) for s in sf[1]['sequences']),
            'ride': current['ride'], 'inherited_F1a_ride_cost_is_not_attributed_to_L16': True}


def falcon():
    aa, bb = [audit.rows(p) for p in (checked_F1a_path(PRIOR / 'f1a-b1-falcon-final.jsonl'), WORK / 'falcon-merged-candidate.jsonl')]
    assert len(aa) == len(bb) == 4443
    for a, b in zip(aa, bb, strict=True):
        for key in ('i', 'stamp', 'decision', 'dets', 'warns', 'dlevel', 'mount', 'mount_h'):
            assert a[key] == b[key], (a['i'], key)
    return {'frames': len(bb), 'decisions': dict(Counter(r['decision'] for r in bb)),
            'equal_to_F1a_author_decisions_detections_warnings_and_mount': True}


def x3():
    current = audit.load(WORK / 'x3-merged-candidate.json')
    reference = audit.load(WORK / 'x3-a-reference.json')
    assert current['status'] == 'PASS' and current['comparison']['passed']
    audit.battery.validated_entries(current, Path('/tmp/opencode/resense-b4-data/decoded'), audit.ROOT)
    count, comparisons, lost = 0, 0, 0
    changes = {}
    for key, entry in current['entries'].items():
        old = reference['entries'][key]
        aa, bb = [audit.rows(Path(v['raw_path'])) for v in (old, entry)]
        assert [r['i'] for r in aa] == [r['i'] for r in bb]
        loss = {r['i'] for r in aa if r['obstacle']} - {r['i'] for r in bb if r['obstacle']}
        lost += len(loss)
        changes[key] = {field: [a['i'] for a, b in zip(aa, bb, strict=True) if a[field] != b[field]]
                        for field in ('decision', 'dets', 'warns')}
        calc = audit.battery.compare_metrics(old['metrics'], entry['metrics'])
        assert calc == current['comparison']['cases'][key] and all(r['passed'] for r in calc)
        count += len(bb)
        comparisons += len(calc)
    assert lost == 0
    return {'passed': True, 'cases': len(current['entries']), 'rows': count, 'comparisons': comparisons,
            'lost_STOP_rows': lost, 'changes_vs_pre_F1a_reference': changes}


def tests():
    cases = list(ET.parse(WORK / 'affected-merged-candidate.xml').iter('testcase'))
    assert not any(c.find('failure') is not None or c.find('error') is not None or c.find('skipped') is not None
                   for c in cases)
    assert len(cases) >= 461
    log = (WORK / 'affected-merged-candidate.log').read_text()
    deselections = re.search(r'(\d+) deselected', log)
    assert deselections and int(deselections[1]) == 1
    return {'passed': len(cases), 'skips': 0, 'external_path_deselections': int(deselections[1])}


def analytic():
    previous, current = [audit.load(WORK / name) for name in ('analytic-a-candidate.json', 'analytic-merged-candidate.json')]
    result = {}
    for key, value in current['cases'].items():
        old = previous['cases'][key]
        assert old['xyz_sha256'] == value['xyz_sha256']
        for a, b in zip(old['rows'], value['rows'], strict=True):
            assert audit.normal(a['result']) == audit.normal(b['result']) and a['state'] == b['state']
        result[key] = dict(Counter(r['decision'] for r in value['rows']))
    return {'unchanged_from_accepted_L16_analytic_cases': result}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    checks = {'gate': gate, 'falcon': falcon, 'x3': x3, 'tests': tests, 'analytic': analytic}
    parser.add_argument('phase', choices=list(checks))
    args = parser.parse_args()
    result = checks[args.phase]()
    (HERE / f'audit-merged-{args.phase}.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
