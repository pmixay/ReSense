"""One-time explicit lock construction from the already committed evidence, never executed in CI."""
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BASE = '492e407'


def blob(path, ref=BASE):
    return subprocess.check_output(['git', 'show', f'{ref}:{path}'], cwd=ROOT)


def record(path):
    data = blob(path)
    return dict(path=path, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                git_blob=hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest())


def main():
    inspection = json.loads((HERE / 'provenance-inspection.json').read_text())
    excluded, needed, roots = [], set(), set()
    for entry in inspection['files']:
        path = entry['path']
        if entry['indexes']:
            index = next(p for p in entry['indexes'] if path.startswith(str(Path(p).parent).replace('\\', '/') + '/'))
            folder = str(Path(index).parent).replace('\\', '/')
            relative = path[len(folder) + 1:]
            document = json.loads(blob(index))
            files = document.get('files', document)
            pointer = ['files'] if 'files' in document else []
            if isinstance(files, list):
                number = next(i for i, r in enumerate(files) if r['path'] == relative)
                pointer += [number, 'sha256']
            else:
                pointer += [relative]
                if isinstance(files[relative], dict):
                    pointer += ['sha256']
            provenance = dict(kind='package-sha256', path=index, pointer=pointer)
        else:
            assert path.endswith('/h4_fixes/rearm/verify.py'), path
            folder = str(Path(path).parent).replace('\\', '/')
            index = folder + '/green-bb62b94/launch.json'
            launch = json.loads(blob(index))
            print('launch keys:', list(launch))
            # Locate the recorded command string without guessing its array offset.
            matches = []

            def walk(value, pointer):
                if isinstance(value, str) and path in value and 'checkout' in value:
                    matches.append(pointer)
                elif isinstance(value, dict):
                    for key, child in value.items():
                        walk(child, pointer + [key])
                elif isinstance(value, list):
                    for i, child in enumerate(value):
                        walk(child, pointer + [i])
            walk(launch, [])
            assert len(matches) == 1
            ref = 'bb62b94d69425e00079be88e9adb835978f8282e'
            assert blob(path, ref) == blob(path), 'recorded launch source differs'
            provenance = dict(kind='git-pinned-launch', path=index, pointer=matches[0], commit=ref,
                              source_blob=entry['git_blob'])
        needed.add(index)
        roots.add(folder)
        excluded.append(dict(path=path, provenance=provenance))
    tracked = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE], cwd=ROOT, text=True).splitlines()
    for path in tracked:
        if path.endswith('.py') and any(path.startswith(folder + '/') for folder in roots):
            needed.add(path)
    # Nested withdrawal package is already inventoried by its parent; keep roots disjoint.
    roots = {r for r in roots if not any(r.startswith(p + '/') for p in roots if p != r)}
    lock = dict(schema='resense-archived-lint-v1', ruff='0.15.8', baseline_commit=subprocess.check_output(
        ['git', 'rev-parse', BASE], cwd=ROOT, text=True).strip(), python_roots=sorted(roots),
        exclusions=excluded, files=[record(p) for p in sorted(needed)])
    output = (json.dumps(lock, indent=2) + '\n').encode()
    with (HERE / 'snapshot_lock.json').open('xb') as f:
        f.write(output)
    print('lock sha256:', hashlib.sha256(output).hexdigest())
    print('immutable files:', len(needed), 'exclusions:', len(excluded))


if __name__ == '__main__':
    main()
