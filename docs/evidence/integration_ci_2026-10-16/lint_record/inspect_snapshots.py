"""Capture original CI diagnostics and inspect existing historical hash provenance; no replay."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
BASE = '492e407'
LEGACY = 'docs/evidence/cycle_2026-09-28/complete_timing/default/run_gate.py'


def blob(path):
    return subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--ruff', required=True)
    args = cli.parse_args()
    result = subprocess.run([args.ruff, 'check', '--no-cache', '--output-format', 'json',
                             '--exclude', LEGACY, '.'], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 1, result.stderr
    diagnostics = json.loads(result.stdout)
    for d in diagnostics:
        d['filename'] = Path(d['filename']).relative_to(ROOT).as_posix()
    (HERE / 'original-diagnostics.json').write_text(json.dumps(diagnostics, indent=2) + '\n', encoding='utf-8')
    log = subprocess.check_output(['gh', 'run', 'view', '38895681129', '--log-failed'], cwd=ROOT)
    (HERE / 'original-ci-failure.txt').write_bytes(log)
    paths = sorted({d['filename'] for d in diagnostics} | {LEGACY})
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', BASE, '--',
                                     'docs/evidence/integration_2026-10-16',
                                     'docs/evidence/cycle_2026-09-28/complete_timing/default'], cwd=ROOT, text=True).splitlines()
    indexes = {p: json.loads(blob(p)) for p in names
               if p.endswith(('HASHES.json', 'artifact_manifest.json', 'helper_source_identity.json'))}
    rows = []
    for path in paths:
        data = blob(path)
        sha = hashlib.sha256(data).hexdigest()
        matches = [p for p, index in indexes.items() if sha in json.dumps(index)]
        row = {'path': path, 'sha256': sha, 'git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest(),
               'bytes': len(data), 'worktree_exact': (ROOT / path).read_bytes() == data,
               'indexes': matches, 'diagnostics': dict(Counter(d['code'] for d in diagnostics if d['filename'] == path))}
        rows.append(row)
    report = {'baseline': BASE, 'diagnostics': len(diagnostics), 'codes': dict(Counter(d['code'] for d in diagnostics)),
              'files': rows}
    (HERE / 'provenance-inspection.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
