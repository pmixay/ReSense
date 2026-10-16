"""Probe one newly added H4 test dependency through Docker's actual context filtering."""
import hashlib
import json
from pathlib import Path
import subprocess


def main():
    here = Path(__file__).resolve().parent
    root = here.parents[2]
    out = here / 'fixture-probe'
    out.mkdir(exist_ok=False)
    relative = 'docs/evidence/integration_2026-10-16/h4_safety/results/rearm_witness.json'
    fixture = root / relative
    command = ['docker', 'build', '--network', 'none', '--pull=false', '--progress=plain',
               '-f', str(here / 'Dockerfile.fixture-probe'), '.']
    result = subprocess.run(command, cwd=root, text=True, capture_output=True, timeout=90)
    transcript = '\n'.join(line.rstrip() for line in (result.stdout + result.stderr).splitlines()) + '\n'
    (out / 'build.log').write_text(transcript, encoding='utf-8')
    dockerfile = (root / 'docker/Dockerfile').read_text(encoding='utf-8')
    copied = any(line.startswith('COPY ') and relative in line for line in dockerfile.splitlines())
    report = {'result': 'PASS' if result.returncode == 0 and copied else 'BLOCKED',
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
              'fixture': relative, 'source_fixture_bytes': fixture.stat().st_size,
              'source_fixture_sha256': hashlib.sha256(fixture.read_bytes()).hexdigest(),
              'production_copy_present': copied, 'context_probe_exit': result.returncode, 'command': command,
              'scope': 'one Docker COPY dependency probe; no installed-detector or full-suite claim'}
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['result'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
