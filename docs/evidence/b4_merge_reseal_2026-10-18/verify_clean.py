"""Verify the real seal in a fresh checkout before and after a source native build."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source, out = args.checkout.resolve(), args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(source / 'scripts'))
    import detector_freeze as freeze

    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def git(*words):
        return subprocess.check_output(['git', *words], cwd=source, text=True).strip()

    assert not git('status', '--porcelain')
    assert not list((source / 'resense').glob('*.so'))
    manifest = json.loads((source / freeze.DEFAULT_MANIFEST).read_text())
    before = freeze.source_hashes(source)
    assert before == manifest['files']
    for ref in manifest['reviewed_supporting_evidence'] + [manifest['baseline'], manifest['validation']]:
        path = source / ref['path']
        assert sha(path) == ref['sha256']
        blob = subprocess.check_output(['git', 'show', f"{manifest['source_commit']}:{ref['path']}"], cwd=source)
        assert hashlib.sha256(blob).hexdigest() == ref['sha256']
    env = dict(os.environ, PATH=str(Path(sys.executable).parent) + ':' + os.environ['PATH'],
               OPENBLAS_CORETYPE='Haswell', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
               MKL_NUM_THREADS='1', PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE='1')
    commands = [
        ('verify_before', ['/usr/bin/python3', 'scripts/detector_freeze.py', 'verify']),
        ('native_build', ['bash', 'scripts/build_native.sh']),
        ('verify_after', ['/usr/bin/python3', 'scripts/detector_freeze.py', 'verify']),
        ('native_loaded', [sys.executable, '-c',
                           'from resense import _native; assert _native.enabled(); print(_native.status())'])]
    runs = []
    for name, command in commands:
        result = subprocess.run(command, cwd=source, env=env, text=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        path = out / (name + '.log')
        path.write_text(result.stdout)
        runs.append({'name': name, 'command': command, 'exit': result.returncode,
                     'log': path.name, 'sha256': sha(path)})
        assert result.returncode == 0, result.stdout
        assert before == freeze.source_hashes(source)
    native = {p.name: sha(p) for p in (source / 'resense').glob('*.so')}
    assert native == {'_resense_native.so': '67fa0887e5480e24ca67138ec5271969742917a5c5869d9ab4e634599d8c7394'}
    assert not git('status', '--porcelain')
    result = {'status': 'CLEAN_CHECKOUT_SEAL_PASS_BEFORE_AND_AFTER_NATIVE_BUILD',
              'checked_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'checkout': str(source), 'checkout_commit': git('rev-parse', 'HEAD'),
              'measured_commit': manifest['measured_commit'], 'manifest': freeze.DEFAULT_MANIFEST,
              'manifest_sha256': sha(source / freeze.DEFAULT_MANIFEST), 'source_files': len(before),
              'fingerprint_before': freeze.source_digest(before),
              'fingerprint_after': freeze.source_digest(freeze.source_hashes(source)),
              'supporting_refs_checked_against_committed_blobs': len(manifest['reviewed_supporting_evidence']),
              'native': native, 'tracked_tree_clean': True, 'commands': runs,
              'verifier_sha256': sha(Path(__file__)), 'release_authorized': False}
    (out / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
