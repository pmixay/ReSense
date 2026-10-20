"""Show the detection payloads around the changed ride frames in both runs."""
import json
from pathlib import Path

WORK = Path('/tmp/opencode/f1a-completion-work')
CAND, REF = WORK / 'gate-b-candidate', WORK / 'gate-b-reference'
WINDOWS = {'new_data_7.jsonl': range(618, 628), 'new_data_1.jsonl': range(1255, 1270),
           'new_data_4.jsonl': range(74, 92)}


def rows(path):
    return [json.loads(line) for line in path.open() if line.strip()]


def main():
    for name, window in WINDOWS.items():
        a, b = rows(REF / name), rows(CAND / name)
        print(f'\n=== {name}')
        for i in window:
            x, y = a[i], b[i]
            if x['obstacle'] == y['obstacle'] and x.get('detections') == y.get('detections'):
                continue
            print(f"  row {i} ref obst={x['obstacle']} dets={[(d.get('id'), d.get('distance'), d.get('zone'), d.get('reason')) for d in x['detections']]}")
            print(f"  row {i} can obst={y['obstacle']} dets={[(d.get('id'), d.get('distance'), d.get('zone'), d.get('reason')) for d in y['detections']]}")


if __name__ == '__main__':
    main()
