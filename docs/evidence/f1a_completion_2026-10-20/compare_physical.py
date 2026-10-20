"""Compare the physical scenes on decision-relevant fields only (timing excluded)."""
import json
from pathlib import Path

WORK = Path('/tmp/opencode/f1a-completion-work')
TIMING = {'ms', 'total_ms', 'detect_ms', 'decode_ms', 'latency_ms', 'latency_p95_ms', 'timing_ms'}
# The latency budget health level and its message follow the wall clock, not the geometry.
TIMING_HEALTH = {'level', 'messages', 'decision_level'}


def strip(value):
    if isinstance(value, dict):
        return {k: strip(v) for k, v in value.items()
                if k not in TIMING and not (k == 'health' and TIMING_HEALTH)}
    if isinstance(value, list):
        return [strip(v) for v in value]
    return value


def main():
    a = json.loads((WORK / 'physical-b-reference.json').read_text())
    b = json.loads((WORK / 'physical-b-candidate.json').read_text())
    assert set(a) == set(b)
    differences, stops = [], {}
    for scene in a:
        rows_a, rows_b = a[scene], b[scene]
        assert len(rows_a) == len(rows_b)
        for ra, rb in zip(rows_a, rows_b, strict=True):
            assert ra['true_distance'] == rb['true_distance']
            if ra['matched_stop'] != rb['matched_stop']:
                differences.append((scene, ra['frame'], ra['matched_stop'], rb['matched_stop']))
            if strip(ra['result']) != strip(rb['result']):
                differences.append((scene, ra['frame'], 'payload', 'payload'))
        stops[scene] = (sum(r['matched_stop'] for r in rows_a), sum(r['matched_stop'] for r in rows_b))
    moved = [k for k in stops if k.startswith('moving/')]
    print(json.dumps(dict(scenes=len(stops), differing_rows=len(differences), differences=differences[:20],
                          stopped_scenes=sum(1 for k, v in stops.items() if v[0] or v[1]),
                          moving=[(k, stops[k]) for k in moved],
                          empty_controls=[(k, stops[k]) for k in stops if 'topNone' in k]), indent=2))
    assert not differences


if __name__ == '__main__':
    main()
