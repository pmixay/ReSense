"""Package immutable evidence and reopen every member to verify its hash."""
import hashlib
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/r3-completion-work')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    groups = {'replay': [], 'controls': []}
    for path in sorted(WORK.rglob('*')):
        if not path.is_file():
            continue
        name = str(path.relative_to(WORK))
        key = 'replay' if name.startswith(('gate-', 'x3-', 'falcon-')) else 'controls'
        groups[key].append((name, path))
    for name in ('r3-completion-red.xml', 'r3-completion-targeted-v2.xml', 'r3-completion-targeted-v3.xml'):
        path = Path('/tmp/opencode') / name
        assert path.is_file()
        groups['controls'].append(('early-tests/' + name, path))
    manifest, archives = [], {}
    for group, files in groups.items():
        archive = HERE / f'raw-{group}.tar.gz'
        expected = {name: dict(path=name, bytes=path.stat().st_size, sha256=sha(path), archive=archive.name)
                    for name, path in files}
        assert len(expected) == len(files)
        with tarfile.open(archive, 'x:gz') as tar:
            for name, path in files:
                tar.add(path, arcname=name)
        with tarfile.open(archive) as tar:
            assert set(tar.getnames()) == set(expected)
            for member in tar:
                content = tar.extractfile(member).read()
                assert len(content) == expected[member.name]['bytes']
                assert hashlib.sha256(content).hexdigest() == expected[member.name]['sha256']
        manifest.extend(expected.values())
        archives[archive.name] = dict(bytes=archive.stat().st_size, sha256=sha(archive),
                                     verified_members=len(expected))
    with (HERE / 'raw-manifest.json').open('x') as stream:
        json.dump(manifest, stream, indent=2)
    with (HERE / 'package.json').open('x') as stream:
        json.dump(dict(archives=archives, total_verified_members=len(manifest)), stream, indent=2)
    print(json.dumps(archives, indent=2))


if __name__ == '__main__':
    main()
