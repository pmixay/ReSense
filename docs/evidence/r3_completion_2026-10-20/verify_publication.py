"""Independent publication verification: archives, source Git blobs and links."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
from urllib.parse import unquote

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def digest(stream):
    value = hashlib.sha256()
    while block := stream.read(1024 * 1024):
        value.update(block)
    return value.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    inventory = json.loads((HERE / 'raw-manifest.json').read_text())
    package = json.loads((HERE / 'package.json').read_text())
    count = 0
    hashes = {}
    for name, expected in package['archives'].items():
        path = HERE / name
        with path.open('rb') as stream:
            actual = digest(stream)
        assert actual == expected['sha256'] and path.stat().st_size == expected['bytes']
        hashes[name] = actual
        members = {r['path']: r for r in inventory if r['archive'] == name}
        with tarfile.open(path) as archive:
            entries = archive.getmembers()
            assert len(entries) == len(members) == expected['verified_members']
            assert {e.name for e in entries} == set(members)
            for entry in entries:
                assert entry.isfile() and entry.size == members[entry.name]['bytes']
                assert digest(archive.extractfile(entry)) == members[entry.name]['sha256']
                count += 1
    assert count == package['total_verified_members'] == len(inventory)
    manifest = json.loads((ROOT / 'docs/evidence/detector_freeze_2026-10-20_1.2.0_r3.json').read_text())
    for path, expected in manifest['files'].items():
        with (ROOT / path).open('rb') as stream:
            assert digest(stream) == expected
        blob = subprocess.check_output(['git', 'show', f'{manifest["measured_commit"]}:{path}'], cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == expected
    links = 0
    documents = [ROOT / name for name in ('docs/BACKLOG.md', 'docs/DETECTOR_FREEZE.md', 'docs/ALGORITHM.md',
                                         'docs/README.md', 'CHANGELOG.md')]
    documents += list(HERE.glob('*.md'))
    for document in documents:
        for target in re.findall(r'\]\(([^)]+)\)', document.read_text()):
            if target.startswith(('http:', 'https:', '#', 'mailto:')):
                continue
            target = unquote(target.split('#')[0])
            if target:
                assert (document.parent / target).exists(), (document.name, target)
                links += 1
    subprocess.run(['git', 'merge-base', '--is-ancestor', '5d83c5b', 'HEAD'], cwd=ROOT, check=True)
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    report = dict(commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  archives=hashes, verified_members=count, measured_Git_source_files=len(manifest['files']),
                  verified_local_links=links, integrated_main='5d83c5b',
                  independent_bundle_acceptance='pending')
    with args.out.open('x') as stream:
        json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
