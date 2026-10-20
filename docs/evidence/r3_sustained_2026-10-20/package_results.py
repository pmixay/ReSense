"""Package immutable raw runs and measured source; reopen every archived member."""
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/r3-sustained')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    receipt = json.loads((HERE / 'on-execution.json').read_text())
    measured = receipt['commit']
    original_repo = Path(receipt['command'][1]).parents[1]
    members = {f'raw/{p.name}': p.read_bytes() for p in WORK.iterdir() if p.is_file()}
    for relative, expected in receipt['source_sha256'].items():
        if relative.endswith('.so'):
            data = (original_repo / relative).read_bytes()
        else:
            data = subprocess.check_output(['git', 'show', f'{measured}:{relative}'], cwd=ROOT)
        assert digest(data) == expected, relative
        members[f'measured-source/{relative}'] = data
    verification = json.loads((HERE / 'reporting-verification.json').read_text())
    for relative, expected in verification['reporting_source_sha256'].items():
        data = (ROOT / relative).read_bytes()
        assert digest(data) == expected, relative
        members[f'reporting-source/{relative}'] = data
    for side in ('off', 'on'):
        r = json.loads((HERE / f'{side}-execution.json').read_text())
        assert digest(members[f'raw/{side}.json']) == r['raw_sha256']
        assert digest(members[f'raw/{side}.log']) == r['log_sha256']
    assert digest(members['raw/r3-off.yaml']) == json.loads((HERE / 'off-execution.json').read_text())['config_sha256']
    assert digest(members['measured-source/configs/default.yaml']) == receipt['config_sha256']
    manifest = {name: dict(bytes=len(data), sha256=digest(data)) for name, data in sorted(members.items())}
    archive = HERE / 'raw-evidence.tar.gz'
    with tarfile.open(archive, 'x:gz') as out:
        for name, data in sorted(members.items()):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            out.addfile(info, io.BytesIO(data))
    with tarfile.open(archive) as reopened:
        assert set(reopened.getnames()) == set(manifest)
        for member in reopened:
            data = reopened.extractfile(member).read()
            assert digest(data) == manifest[member.name]['sha256']
            assert len(data) == manifest[member.name]['bytes']
    with (HERE / 'raw-manifest.json').open('x') as out:
        json.dump(manifest, out, indent=2)
    package = dict(file=archive.name, bytes=archive.stat().st_size, sha256=digest(archive.read_bytes()),
        members=len(manifest), all_member_hashes_verified=True, measured_commit=measured,
        note='Raw paired replay plus additive reporting reanalysis; no new full gate/X3/Falcon replay.')
    with (HERE / 'package.json').open('x') as out:
        json.dump(package, out, indent=2)
    print(json.dumps(package, indent=2))


if __name__ == '__main__':
    main()
