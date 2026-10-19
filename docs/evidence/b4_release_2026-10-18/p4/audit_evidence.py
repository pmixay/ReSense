#!/usr/bin/env python3
"""Independent, read-only B4 evidence audit. Outputs only to stdout / --out.

Run with the task Python and PYTHONPATH=<repo>; no detector replay or timing suite.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import xml.etree.ElementTree as ET


def sha(data):
    return hashlib.sha256(data).hexdigest()


def archive(path):
    with tarfile.open(path) as tf:
        return {m.name: tf.extractfile(m).read() for m in tf if m.isfile()}


def intervals(frames):
    out = []
    for i in sorted(frames):
        if out and out[-1][1] + 1 == i:
            out[-1][1] = i
        else:
            out.append([i, i])
    return out


def hits(rows, labels, one_to_one=False):
    from resense.metrics import _assign_detections, gt_objects
    found = {}
    ambiguous = []
    for row in rows:
        objects = [o for o in labels.get(f"{row['i']:05d}", [])
                   if o.get('in_gauge') and o.get('n_points', 1) != 0]
        assert not row['dets'] or row['decision'] == 'STOP'
        if one_to_one:
            ds = [{'distance': d['d'], 'lateral': d['lat']} for d in row['dets']]
            assigned = _assign_detections(ds, gt_objects(objects))
        else:
            assigned = {}
            used = Counter()
            for j, o in enumerate(objects):
                length, width = o.get('size', [0.5, 0.5])[:2]
                y = sum(b[1] for b in o['bbox']) / 2 if 'bbox' in o else o['lateral']
                matches = [k for k, d in enumerate(row['dets'])
                           if abs(d['d'] - o['distance']) <= max(2, .03 * o['distance']) + length / 2
                           and abs(d['c'][1] - y) <= 1 + width / 2]
                if matches:
                    assigned[j] = matches[0]
                    used.update(matches)
            if any(n > 1 for n in used.values()):
                ambiguous.append(row['i'])
        for j in assigned:
            o = objects[j]
            found.setdefault(o.get('label', o.get('name')), set()).add(row['i'])
    return found, ambiguous


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo', type=Path, default=Path('/home/aiops/resense'))
    ap.add_argument('--reference', type=Path, default=Path('/tmp/opencode/resense-b4-reference'))
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()
    root = args.repo
    evidence = root / 'docs/evidence/b4_orientation_fix_2026-10-18'
    labels_path = root / 'labels/doubleT_obstacle.json'
    labels = json.loads(labels_path.read_bytes())
    report = {'reviewer': 'independent AI P4', 'labels_sha256': sha(labels_path.read_bytes())}
    report['checksums'] = []
    for line in (evidence / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split()
        actual = sha((evidence / name).read_bytes())
        assert actual == expected, name
        report['checksums'].append({'file': name, 'sha256': actual})
    sources = archive(evidence / 'candidate_source.tar.xz')
    report['archived_sources_equal_worktree'] = {name: sha(raw) == sha((root / name).read_bytes())
                                                  for name, raw in sources.items()}
    assert all(report['archived_sources_equal_worktree'].values())
    report['candidate_source_sha256'] = {name: sha(raw) for name, raw in sources.items()}
    seal = json.loads((root / 'docs/evidence/detector_freeze_2026-10-16_1.1.0.json').read_bytes())
    report['reference_matches_all_sealed_files'] = {
        name: sha((args.reference / name).read_bytes()) == digest for name, digest in seal['files'].items()}
    assert all(report['reference_matches_all_sealed_files'].values())
    report['candidate_changed_sealed_files'] = [name for name, digest in seal['files'].items()
                                               if sha((root / name).read_bytes()) != digest]
    data = {name: json.loads(raw) for name, raw in archive(evidence / 'b4_raw.tar.xz').items()}
    summary = json.loads((evidence / 'summary.json').read_bytes())
    raw = archive(evidence / 'b4_raw.tar.xz')
    report['raw_receipts_match_summary'] = {name: sha(value) == summary['raw_sha256'][name]
                                           for name, value in raw.items()}
    assert all(report['raw_receipts_match_summary'].values())
    report['b4'] = []
    total = 0
    for bag, n in [('empty', 545), ('positive', 201)]:
        before = data[f'b4-baseline-{bag}.json']
        after = data[f'b4-candidate-{bag}.json']
        assert before['input_sha256'] == after['input_sha256']
        assert before['environment'] == after['environment']
        assert before['python'] == after['python']
        for tag, doc, checkout in [('baseline', before, args.reference), ('candidate', after, root)]:
            assert doc['script_sha256'] == sha((evidence / 'run_b4.py').read_bytes())
            for path, digest in doc['source_sha256'].items():
                assert sha((checkout / path).read_bytes()) == digest, (tag, path)
            assert sorted(c['index'] for c in doc['cases']) == list(range(24))
            for case in doc['cases']:
                assert [r['i'] for r in case['rows']] == list(range(n))
                assert case['decisions'] == dict(Counter(r['decision'] for r in case['rows'])) | {
                    k: sum(r['decision'] == k for r in case['rows'])
                    for k in ('GO', 'CAUTION', 'STOP', 'FAULT')}
                total += len(case['rows'])
        bases = {c['index']: c for c in before['cases']}
        for case in after['cases']:
            k = case['index']
            rows = case['rows']
            old = bases[k]['rows']
            expected = case['expected']
            from resense.calibration import axis_label, orientation_candidates
            rotation = orientation_candidates()[k]
            assert expected == axis_label(rotation.T)
            upright = abs(rotation[2, 2]) == 1
            assert upright == case['up_vertical']
            wrong = [r['i'] for r in rows if r['status'] in ('ok', 'identity', 'provisional')
                     and r['orientation'] != expected and not (k == 0 and r['orientation'] == 'configured')]
            assert not wrong
            first = next((r['i'] for r in rows if r['orientation'] == expected or
                          (k == 0 and r['mapping_confirmed'])), None)
            assert first is not None and first <= 1
            assert all(r['decision'] != 'GO' for r in rows if not r['mapping_confirmed'])
            item = {'bag': bag, 'rotation': k, 'upright': bool(upright), 'first_correct': first,
                    'baseline_counts': dict(Counter(r['decision'] for r in old)),
                    'candidate_counts': dict(Counter(r['decision'] for r in rows)),
                    'lost_stop_vs_same_rotation': intervals(r['i'] for r, b in zip(rows, old)
                                                           if b['decision'] == 'STOP' and r['decision'] != 'STOP'),
                    'nearest_changed_frames': [r['i'] for r, b in zip(rows, old) if r['nearest'] != b['nearest']]}
            if bag == 'empty':
                assert not any(r['decision'] == 'STOP' for r in rows)
            else:
                comparator = old if upright else bases[0]['rows']
                item['comparison'] = 'same rotation baseline' if upright else 'correct identity baseline'
                for mode in ('jury', 'gate_one_to_one'):
                    actual, ambiguous = hits(rows, labels, mode == 'gate_one_to_one')
                    reference, _ = hits(comparator, labels, mode == 'gate_one_to_one')
                    lost = {name: sorted(frames - actual.get(name, set())) for name, frames in reference.items()}
                    item[mode] = {'matched_intervals': {name: intervals(frames) for name, frames in actual.items()},
                                  'matched_counts': {name: len(frames) for name, frames in actual.items()},
                                  'lost_frames': lost, 'shared_detection_frames': ambiguous}
                    assert not any(lost.values()), (bag, k, mode, lost)
                item['first_stop'] = next((r['i'] for r in rows if r['decision'] == 'STOP'), None)
            report['b4'].append(item)
    report['b4_processed_frames'] = total
    assert total == 35808
    sys.path.insert(0, str(root / 'scripts'))
    import regression_gate as gate
    candidate = json.loads((evidence / 'gate.json').read_bytes())
    baseline = json.loads((root / 'docs/evidence/results/regression_baseline_2026-09-29_shell_off.json').read_bytes())
    comparison = gate.compare(baseline, candidate)
    report['author_gate_recomputed'] = gate.gate_summary(comparison, baseline, candidate['gate']['baseline'], [])
    assert report['author_gate_recomputed'] == candidate['gate']
    report['author_gate_gated_rows'] = sum(bool(r['gated']) for r in comparison)
    contents = archive(evidence / 'gate_raw.tar.xz')
    counts, stops = {}, {}
    report['gate_raw_schema_examples'] = {}
    for name, raw in contents.items():
        if name.endswith('.jsonl'):
            rows = [json.loads(line) for line in raw.splitlines() if line.strip()]
            counts[name] = len(rows)
            stops[name] = [r['frame'] for r in rows if r['obstacle']]
            assert len(set(r['frame'] for r in rows)) == len(rows)
            report['gate_raw_schema_examples'].setdefault('jsonl', rows[0])
    f = json.loads(contents['setF_straight.json'])
    report['gate_raw_schema_examples']['set_F_top_keys'] = list(f)
    report['gate_raw_recording_counts'] = counts
    report['gate_raw_stop_intervals'] = {name: intervals(frames) for name, frames in stops.items()}
    report['gate_raw_recording_total'] = sum(counts.values())
    seqs = f['sequences']
    report['gate_set_F_sequences'] = len(seqs)
    report['gate_set_F_rows'] = sum(len(s['rows']) for s in seqs)
    report['gate_set_F_sequence_details'] = [
        {'kind': s['kind'], 'frames': len(s['rows']),
         'matched_stop_positions': intervals(i for i, r in enumerate(s['rows']) if r['hit']),
         'first_detection_m': s['first'], 'false_detections': s['fp']}
        for s in seqs]
    assert len(seqs) == 30 and report['gate_set_F_rows'] == 3060
    assert Counter(s['kind'] for s in seqs) == {k: 6 for k in ('person', 'box1.0', 'box0.5', 'trolley', 'cable')}
    from resense.config import DetectorConfig
    cfg = DetectorConfig.from_yaml(root / 'configs/default.yaml')
    recomputed = {}
    with tempfile.TemporaryDirectory(prefix='p4-gate-raw-', dir='/tmp/opencode') as temp:
        temp = Path(temp)
        for name, value in contents.items():
            if name.endswith('.jsonl'):
                assert Path(name).name == name
                (temp / name).write_bytes(value)
        recomputed['recordings'] = {
            bag: gate.recording_entry(bag, [str(temp / f'{bag}.jsonl')], cfg,
                                      str(root / 'labels/doubleT_obstacle.json') if bag == 'doubleT_obstacle' else None)
            for bag in gate.SIX}
        recomputed['five_empty'] = {
            k: sum(recomputed['recordings'][bag][k] for bag in gate.FIVE_EMPTY)
            for k in ('frames', 'alarm_frames', 'alarm_events', 'stop_episodes', 'advisory_frames')}
        recomputed['set_O'] = gate.set_o_entry([str(temp / 'cloud_with_fake_obj.jsonl')],
                                              str(root / 'labels/cloud_with_fake_obj.json'))
        ride = gate.recording_entry('new_data', [str(temp / f'new_data_{i}.jsonl') for i in range(8)], cfg)
        recomputed['ride'] = {'available': True, 'chunks': 8,
                              **{k: v for k, v in ride.items() if k not in ('labelled', 'first_alarm_frame')}}
    recomputed['set_F_straight'] = {'available': True, 'parameters': dict(gate.SET_F_STRAIGHT), 'kinds': {
        kind: {'sequences': s['sequences'], 'detected': s['detected'],
               'first_detection_median_m': s['first_detection_median'],
               'sustained_median_m': s['sustained_median'], 'false_detections': s['false_detections'],
               'recall_by_bin': s['recall_by_bin']} for kind, s in f['summary']['per_kind'].items()}}
    report['author_gate_raw_recomputed_sections'] = {k: v == candidate[k] for k, v in recomputed.items()}
    assert all(report['author_gate_raw_recomputed_sections'].values())
    assert sum(counts.values()) == 15269
    xml = ET.fromstring((evidence / 'pytest.xml').read_bytes())
    cases = xml.findall('.//testcase')
    report['author_junit'] = {'cases': len(cases), 'failures': len(xml.findall('.//failure')),
                              'errors': len(xml.findall('.//error')), 'skipped': len(xml.findall('.//skipped')),
                              'files': dict(Counter(c.attrib['classname'] for c in cases))}
    assert len(cases) == 421 and not any(report['author_junit'][k] for k in ('failures', 'errors', 'skipped'))
    report['pass'] = True
    report['positive_case_summary'] = [
        {'rotation': c['rotation'], 'first_stop': c['first_stop'], 'counts': c['candidate_counts'],
         'jury_matches': c['jury']['matched_counts'], 'one_to_one_matches': c['gate_one_to_one']['matched_counts'],
         'lost_jury': c['jury']['lost_frames'], 'lost_one_to_one': c['gate_one_to_one']['lost_frames']}
        for c in report['b4'] if c['bag'] == 'positive']
    text = json.dumps(report, indent=2)
    if args.out:
        args.out.write_text(text + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in
                      ('b4', 'gate_raw_schema_examples', 'reference_matches_all_sealed_files',
                       'positive_case_summary', 'gate_set_F_sequence_details', 'gate_raw_stop_intervals')}, indent=2))


if __name__ == '__main__':
    main()
