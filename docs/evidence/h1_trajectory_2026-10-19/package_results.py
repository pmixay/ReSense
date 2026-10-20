"""Pin input/source continuity and verify portable source/raw evidence archives."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/h1-trajectory')


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(8 * 1024 * 1024):
            value.update(block)
    return value.hexdigest()


def archive(target, files):
    manifest = {name: dict(bytes=path.stat().st_size, sha256=sha(path)) for name, path in sorted(files.items())}
    with tarfile.open(target, 'x:gz') as stream:
        for name, path in sorted(files.items()):
            stream.add(path, arcname=name, recursive=False)
    with tarfile.open(target, 'r:gz') as stream:
        members = stream.getmembers()
        assert {member.name for member in members} == set(manifest)
        for member in members:
            value = hashlib.sha256()
            with stream.extractfile(member) as data:
                while block := data.read(8 * 1024 * 1024):
                    value.update(block)
            assert member.size == manifest[member.name]['bytes']
            assert value.hexdigest() == manifest[member.name]['sha256']
    receipt = dict(file=target.name, bytes=target.stat().st_size, sha256=sha(target), members=len(manifest), all_member_hashes_verified=True)
    return receipt, manifest


def main():
    audit = json.loads((HERE / 'audit-final.json').read_text())
    assert audit['status'] == 'H1_OPEN_REFERENCE_NOT_VALIDATED'
    # Importing Open3D is unnecessary just to recover the two pinned cache paths.
    caches = {'A': Path('/tmp/opencode/r3-h1/baseline/cache/roundT_squareT_pressureGate_squareT'),
              'C': Path('/tmp/opencode/r3-h1/supplement-range/decoded/roundT_pressureGate_roundT')}
    inputs = {}
    for name, cache in caches.items():
        old = json.loads((Path('/tmp/opencode/h1-reference') / f'sequence-{name}-v2.json').read_text())['rows']
        current = json.loads((WORK / f'local-gicp-{name}-seeded.json').read_text())['rows']
        assert len(old) == len(current)
        values = []
        for original, actual in zip(old, current, strict=True):
            assert original['i'] == actual['i']
            path = cache / f"f_{actual['i']:05d}.npz"
            digest = sha(path)
            assert digest == original['input_sha256'] == actual['sha256']
            values.append(dict(frame=actual['i'], sha256=digest))
        inputs[name] = dict(cache=str(cache), frames=len(values), rows=values)
    code = {}
    for name, expected in audit['source_files'].items():
        path = ROOT / name
        assert sha(path) == expected
        if path.suffix != '.so':
            measured = subprocess.check_output(['git', 'show', f'0f02b28:{name}'], cwd=ROOT)
            assert hashlib.sha256(measured).hexdigest() == expected
        code[name] = path
    for path in HERE.iterdir():
        if path.suffix in ['.py', '.md']:
            code[str(path.relative_to(ROOT))] = path
    # Prior reference helpers are runtime imports, so include their exact bytes.
    for name in ['reference.py', 'deskew_reference.py', 'direct-reference.json', 'direct-reference-deskew.json']:
        path = ROOT / 'docs/evidence/h1_reference_2026-10-19' / name
        code[str(path.relative_to(ROOT))] = path
    raw = {str(path.relative_to(WORK)): path for path in WORK.rglob('*') if path.is_file() and '__pycache__' not in path.parts}
    raw.update({str(path.relative_to(ROOT)): path for path in HERE.glob('*.json')})
    source_receipt, source_manifest = archive(HERE / 'source.tar.gz', code)
    raw_receipt, raw_manifest = archive(HERE / 'raw-evidence.tar.gz', raw)
    (HERE / 'source-manifest.json').write_text(json.dumps(source_manifest, indent=2))
    (HERE / 'raw-manifest.json').write_text(json.dumps(raw_manifest, indent=2))
    receipt = dict(status=audit['status'], detector_commit='0f02b283a9a8ebeb8bccae76a7b12f23862206df',
        integrated_remote_main='0acb18c', remote_main_pushed=False,
        python=platform.python_version(), packages={name: importlib.metadata.version(name) for name in ['numpy', 'scipy', 'open3d', 'matplotlib']},
        inputs=inputs, source=source_receipt, raw=raw_receipt)
    with (HERE / 'package.json').open('x') as stream:
        json.dump(receipt, stream, indent=2)
    print(json.dumps({key: value for key, value in receipt.items() if key != 'inputs'}, indent=2))


if __name__ == '__main__':
    main()
