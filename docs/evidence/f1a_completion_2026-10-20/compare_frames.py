"""Per-frame comparison of the candidate and reference gate work for the ride."""
import json
from pathlib import Path

WORK = Path('/tmp/opencode/f1a-completion-work')
CAND, REF = WORK / 'gate-b-candidate', WORK / 'gate-b-reference'


def rows(path):
    return [json.loads(line) for line in path.open() if line.strip()]


def main():
    changed = []
    for name in sorted(p.name for p in CAND.glob('new_data_*.jsonl')):
        a, b = rows(REF / name), rows(CAND / name)
        assert len(a) == len(b), (name, len(a), len(b))
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            if x['obstacle'] != y['obstacle'] or bool(x.get('warning')) != bool(y.get('warning')):
                changed.append((name, i, x['obstacle'], y['obstacle'],
                                [round(d.get('distance', -1), 1) for d in x['detections']],
                                [round(d.get('distance', -1), 1) for d in y['detections']]))
    print('changed frames', len(changed))
    for row in changed:
        print('  ', row)
    stop_only = [c for c in changed if not c[2] and c[3]]
    print('\nnew STOP frames', len(stop_only), 'lost STOP frames', len([c for c in changed if c[2] and not c[3]]))


if __name__ == '__main__':
    main()
