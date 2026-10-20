"""Locate the exact payload fields that differ between the physical runs."""
import json
from pathlib import Path

WORK = Path('/tmp/opencode/f1a-completion-work')


def diff(a, b, path=''):
    if isinstance(a, dict) and isinstance(b, dict):
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                yield (f'{path}.{key}', 'missing', 'missing')
            else:
                yield from diff(a[key], b[key], f'{path}.{key}')
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            yield (path, f'len {len(a)}', f'len {len(b)}')
        else:
            for i, (x, y) in enumerate(zip(a, b, strict=True)):
                yield from diff(x, y, f'{path}[{i}]')
    elif a != b:
        yield (path, a, b)


def main():
    a = json.loads((WORK / 'physical-b-reference.json').read_text())
    b = json.loads((WORK / 'physical-b-candidate.json').read_text())
    seen = {}
    for scene in a:
        for ra, rb in zip(a[scene], b[scene], strict=True):
            for path, x, y in diff(ra['result'], rb['result']):
                key = path.split('[')[0]
                seen.setdefault(key, []).append((scene, ra['frame'], x, y))
    for key, items in sorted(seen.items()):
        print(key, 'count', len(items), 'example', items[0])


if __name__ == '__main__':
    main()
