"""Prepare isolated, owned F1a work and authenticated historical snapshots."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

ROOT = Path(__file__).resolve().parents[3]
WORK = Path('/tmp/opencode/f1a-completion-work')


def main():
    WORK.mkdir(exist_ok=False)
    native = Path('/home/aiops/resense/resense/_resense_native.so')
    for repo in (ROOT, Path('/tmp/opencode/f1a-completion-reference')):
        shutil.copy2(native, repo / 'resense/_resense_native.so')
        assert (repo / 'resense/_resense_native.so').read_bytes() == native.read_bytes()
    archive = ROOT / 'docs/evidence/f1a_acceptance_2026-10-20/out/trace_fix_records.tar.xz'
    destination = WORK / 'historical-p4'
    destination.mkdir()
    with tarfile.open(archive) as t:
        t.extractall(destination, filter='data')
        members = t.getnames()
    print(json.dumps(dict(native_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),
                          archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                          members=len(members), first=members[:12]), indent=2))


if __name__ == '__main__':
    main()
