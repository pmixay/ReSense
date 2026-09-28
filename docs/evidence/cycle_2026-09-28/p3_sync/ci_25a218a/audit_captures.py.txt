"""Read-only audit of downloaded CI cold-bag captures against original header stamps."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import math
import sys

ROOT = Path('/workspace/ReSense-p3-sync')
sys.path[:0] = [str(ROOT), str(ROOT / 'scripts')]
from check_dry_run import load, read_bag, match_recording, freshness_failures, detected_obstacle, percentile
from resense.metrics import load_gt, gt_objects, _assign_detections

OUT = Path('/cycle/p3_sync/ci_25a218a')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
GT = load_gt(str(ROOT / 'labels/doubleT_obstacle.json'))

def strict_current(frame):
    f = frame.get('freshness', {})
    def bounded(value, lo, hi):
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and lo <= value <= hi
    return (frame.get('snapshot_kind') == 'frame' and f.get('valid') is True
            and f.get('reason') == 'current' and not frame.get('node', {}).get('catchup')
            and bounded(f.get('source_age_s'), -.05, .5)
            and bounded(f.get('residence_age_s'), 0, .5)
            and bounded(f.get('queue_lag_s'), 0, 1e-6)
            and not freshness_failures([frame]))

def intervals(ids):
    out = []
    for i in ids:
        if out and i == out[-1][1]+1: out[-1][1]=i
        else: out.append([i,i])
    return out

sources = {}
report = {'schema': 'resense-ci-original-bag-audit-v1', 'audit_sha256': sha(Path(__file__)),
          'checker_sha256': sha(ROOT / 'scripts/check_dry_run.py'),
          'labels_sha256': sha(ROOT / 'labels/doubleT_obstacle.json'),
          'fresh_rule': 'frame snapshot; freshness.valid=true, reason=current; no catchup; registered source/residence/queue age bounds; freshness contract valid; actual current detector STOP, not held',
          'sustained_definition': 'at least five consecutive original source frame indices with fresh matched STOP',
          'runs': {}}
for folder in ('pr_f577a7c', 'experimental'):
    base = OUT / folder
    run = json.loads((base / 'run.json').read_text())
    entry = {'run': run['url'], 'head_sha': run['headSha'], 'conclusion': run['conclusion'], 'recordings': {}}
    assert 'commit: ' + run['headSha'] in (base / 'cold-bags/provenance.txt').read_text()
    for bag, capture in (('doubleT_obstacle', 'dry_run'), ('roundT_doubleT', 'roundT_doubleT')):
        path = base / 'cold-bags' / capture / 'status.jsonl'
        frames, skipped = load(path)
        if bag not in sources:
            sources[bag] = read_bag('/data/for_hackathon/' + bag, frames[0]['node']['input_topic'])
        source = sources[bag]
        assert source is not None
        mapping = match_recording([f['stamp'] for f in frames], source[1], .1)
        missing = sorted(set(range(len(source[1]))) - set(mapping))
        counts = Counter(mapping)
        duplicates = {str(i): n for i, n in counts.items() if n > 1}
        item = {'capture_sha256': sha(path), 'frames': len(frames), 'source_frames': len(source[1]),
                'exact_header_sequence_complete': mapping == list(range(len(source[1]))),
                'header_stamps_sha256': hashlib.sha256(json.dumps(source[1]).encode()).hexdigest(),
                'missing_frame_indices': missing, 'unmatched_header_stamps': counts.get(None, 0),
                'duplicate_indices': duplicates, 'non_frame_snapshots': skipped,
                'freshness_failures': freshness_failures(frames),
                'fresh_frames': sum(strict_current(f) for f in frames),
                'declared_valid_but_not_strict_current': [i for i,f in zip(mapping,frames) if f['freshness']['valid'] and not strict_current(f)],
                'invalid_reason_counts': dict(Counter(f['freshness']['reason'] for f in frames if not f['freshness']['valid'])),
                'invalid_frame_indices': [i for i,f in zip(mapping,frames) if not f['freshness']['valid']],
                'decision_counts': dict(Counter(f['decision'] for f in frames)),
                'current_detector_stop_frames': sum(detected_obstacle(f) for f in frames),
                'held_stop_frames': sum(f.get('stop_held', False) for f in frames),
                'p95_decode_detect_ms': percentile([f['node']['latency_ms'] for f in frames], 95),
                'p95_valid_end_to_end_ms': percentile([1000*f['freshness']['source_age_s'] for f in frames if f['freshness']['valid']], 95),
                'last_dropped_counter': frames[-1]['node'].get('dropped_frames')}
        if bag == 'doubleT_obstacle':
            targets, rail75 = {}, {'hits': 0, 'frames': 0, 'missed_indices': []}
            unmatched = []
            for index, frame in zip(mapping, frames):
                if index is None:
                    continue
                gs = [g for g in gt_objects(GT.get(f'{index:05d}', [])) if g.in_gauge]
                ds = frame['detections'] if detected_obstacle(frame) and strict_current(frame) and frame['decision']=='STOP' else []
                matched = _assign_detections(ds, gs)
                used = set(matched.values())
                unmatched.extend({'frame': index, **d} for j,d in enumerate(ds) if j not in used)
                for gi,g in enumerate(gs):
                    target = targets.setdefault(g.label, {'hits': 0, 'frames': 0, 'missed_indices': [], 'matched_indices': []})
                    target['hits'] += gi in matched
                    target['frames'] += 1
                    if gi not in matched: target['missed_indices'].append(index)
                    else: target['matched_indices'].append(index)
                    if g.label == 'object_on_rail' and index >= 75:
                        rail75['hits'] += gi in matched; rail75['frames'] += 1
                        if gi not in matched: rail75['missed_indices'].append(index)
            raw_targets = {}
            for index, frame in zip(mapping, frames):
                if index is None: continue
                gs = [g for g in gt_objects(GT.get(f'{index:05d}', [])) if g.in_gauge]
                ds = frame['detections'] if detected_obstacle(frame) else []
                matched = _assign_detections(ds, gs)
                for gi,g in enumerate(gs):
                    target = raw_targets.setdefault(g.label, {'hits': 0, 'frames': 0})
                    target['hits'] += gi in matched
                    target['frames'] += 1
            for target in targets.values():
                spans = intervals(target['matched_indices'])
                first = next(iter(target['matched_indices']), None)
                sustained = next((a for a,b in spans if b-a+1 >= 5), None)
                target.update(first_fresh_stop_frame=first,
                              first_fresh_stop_stamp=None if first is None else source[1][first],
                              first_sustained_five_frame_fresh_stop=sustained,
                              first_sustained_five_frame_stamp=None if sustained is None else source[1][sustained],
                              fresh_stop_intervals=spans,
                              missed_intervals=intervals(target['missed_indices']))
            item.update(raw_current_targets=raw_targets, fresh_current_targets=targets,
                        fresh_rail_from_frame75=rail75, fresh_unmatched_detections=unmatched)
        entry['recordings'][bag] = item
    entry['fast_input'] = json.loads((base / 'cold-bags/fast_input.json').read_text())
    entry['artifact_files'] = {str(p.relative_to(base)): sha(p) for p in sorted(base.rglob('*')) if p.is_file()}
    report['runs'][folder] = entry
(OUT / 'capture_audit.json').write_text(json.dumps(report, indent=2)+'\n')
for name, r in report['runs'].items():
    print(name,r['head_sha'],r['conclusion'])
    for bag, x in r['recordings'].items():
        print(bag,{k:x[k] for k in ('frames','source_frames','exact_header_sequence_complete','fresh_frames','freshness_failures','decision_counts','p95_decode_detect_ms','p95_valid_end_to_end_ms')})
        if 'raw_current_targets' in x: print('raw',x['raw_current_targets'],'fresh', {n:[t['hits'],t['frames']] for n,t in x['fresh_current_targets'].items()}, 'rail75',x['fresh_rail_from_frame75'])
