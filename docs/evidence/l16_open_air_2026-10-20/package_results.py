"""Portable measured outputs; exclude the reacquired raw organizer database."""
import hashlib
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = Path('/tmp/opencode/l16-open-air-work')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


paths = [p for p in WORK.rglob('*') if p.is_file() and p.suffix != '.db3']
manifest, archives = {}, []
groups = {'recordings': [], 'regression': [], 'support': []}
for path in paths:
    name = str(path.relative_to(WORK))
    group = ('recordings' if name.startswith(('prefix-', 'full-')) else
             'regression' if name.startswith(('gate-', 'x3-')) else 'support')
    groups[group].append((name, path))
for path in [ROOT / 'tests/test_open_air_orientation.py', ROOT / 'tests/conftest.py']:
    groups['support'].append(('tested-tests/' + path.name, path))
for group, entries in groups.items():
    archive = HERE / f'raw-evidence-{group}.tar.gz'
    with tarfile.open(archive, 'x:gz', compresslevel=6) as tar:
        for name, path in entries:
            manifest[name] = {'sha256': sha(path), 'bytes': path.stat().st_size, 'archive': archive.name}
            tar.add(path, arcname=name, recursive=False)
    with tarfile.open(archive) as tar:
        assert set(tar.getnames()) == {name for name, _ in entries}
        for member in tar:
            assert hashlib.sha256(tar.extractfile(member).read()).hexdigest() == manifest[member.name]['sha256']
    assert archive.stat().st_size < 100_000_000
    archives.append({'file': archive.name, 'sha256': sha(archive), 'bytes': archive.stat().st_size,
                     'members': len(entries)})
(HERE / 'raw-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
receipt = {'archives': archives,
           'members': len(manifest), 'every_archived_member_reopened_and_verified': True,
           'excluded_organizer_input': 'new_data_0.db3; its acquisition/row hashes are retained'}
(HERE / 'package.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
