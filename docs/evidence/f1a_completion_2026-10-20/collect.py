"""Collect the F1a completion evidence artifacts from the immutable work directory."""
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/f1a-completion-work')
OUT = HERE
sys.path.insert(0, str(ROOT / 'scripts'))
import regression_gate as gate  # noqa: E402


def load(path):
    return json.loads(Path(path).read_text())


def rows(path):
    return [json.loads(line) for line in Path(path).open() if line.strip()]


def main():
    OUT.mkdir(exist_ok=True)
    for side in ('reference', 'candidate'):
        source = HERE / f'gate-c-{side}.json'
        if source.resolve() != (OUT / f'gate-c-{side}.json').resolve():
            shutil.copy2(source, OUT / f'gate-c-{side}.json')
    reference, candidate = load(HERE / 'gate-c-reference.json'), load(HERE / 'gate-c-candidate.json')

    # the gated rows, candidate against reference
    lines = []
    for name in sorted(set(reference['recordings']) | set(candidate['recordings'])):
        a, b = reference['recordings'][name], candidate['recordings'][name]
        for key in ('frames', 'alarm_frames', 'alarm_events', 'stop_episodes', 'advisory_frames'):
            if a.get(key) != b.get(key):
                lines.append(f'{name}.{key}: reference {a.get(key)} -> candidate {b.get(key)}')
    for label, obj in sorted(candidate['set_O']['objects'].items()):
        other = reference['set_O']['objects'].get(label, {})
        for key in ('stop_frames', 'first_stop_m', 'advisory_frames'):
            if obj.get(key) != other.get(key):
                lines.append(f'set_O.{label}.{key}: reference {other.get(key)} -> candidate {obj.get(key)}')
    for key in ('alarm_events', 'stop_episodes', 'alarm_frames'):
        lines.append(f'ride.{key}: reference {reference["ride"].get(key)} -> candidate {candidate["ride"].get(key)}')
    lines.append('recorded pre-repair 8c2bf51: ride alarm_events 18, stop_episodes 24, alarm_frames 102')
    lines.append('gate: reference passed %s, candidate passed %s, candidate waivers %s'
                 % (reference['gate']['passed'], candidate['gate']['passed'], candidate['gate']['allow']))
    (OUT / 'gate-rows.txt').write_text('\n'.join(lines) + '\n')

    # the changed frames
    changed = []
    for name in sorted(p.name for p in (WORK / 'gate-c-candidate').glob('*.jsonl')):
        a, b = rows(WORK / 'gate-c-reference' / name), rows(WORK / 'gate-c-candidate' / name)
        for i, (x, y) in enumerate(zip(a, b, strict=True)):
            if x['obstacle'] != y['obstacle'] or x.get('warning') != y.get('warning'):
                changed.append((name, i, bool(x['obstacle']), bool(y['obstacle']),
                                [round(d.get('distance', -1), 1) for d in x.get('detections', [])],
                                [round(d.get('distance', -1), 1) for d in y.get('detections', [])]))
    text = [f'{name} row {i}: reference STOP={x} candidate STOP={y} reference distances {xd} candidate distances {yd}'
            for name, i, x, y, xd, yd in changed]
    text.append(f'changed frames {len(changed)}; removed STOP frames '
                f'{sum(1 for c in changed if c[2] and not c[3])}; added STOP frames '
                f'{sum(1 for c in changed if not c[2] and c[3])}')
    (OUT / 'changed-frames.txt').write_text('\n'.join(text) + '\n')

    # the physical scenes
    a, b = load(WORK / 'physical-b-reference.json'), load(WORK / 'physical-c-candidate.json')
    physical = []
    for scene in a:
        same = all(ra['matched_stop'] == rb['matched_stop'] for ra, rb in zip(a[scene], b[scene]))
        physical.append(f'{scene}: reference STOP rows {sum(r["matched_stop"] for r in a[scene])}, '
                        f'candidate {sum(r["matched_stop"] for r in b[scene])}, identical {same}')
    physical.append(f'scenes {len(a)}; differing rows '
                    f'{sum(1 for s in a for ra, rb in zip(a[s], b[s]) if ra["matched_stop"] != rb["matched_stop"])}')
    (OUT / 'physical-compare.txt').write_text('\n'.join(physical) + '\n')

    # the flip analysis
    flips = load(WORK / 'continuation-production.json')
    (OUT / 'flips.json').write_text(json.dumps(flips, indent=2) + '\n')

    for name in ('targeted-c.xml', 'tests-c-candidate.xml'):
        source = WORK / name
        if source.exists():
            shutil.copy2(source, OUT / ('targeted-tests.xml' if name.startswith('targeted') else 'full-tests.xml'))
    print('\n'.join(lines))
    print('\n'.join(text[-1:]))
    print((OUT / 'physical-compare.txt').read_text().splitlines()[-1])


if __name__ == '__main__':
    main()
