"""Paired P3 author full gate, without waivers; not a committed-source seal."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

root = Path('/home/aiops/resense')
here = root / 'docs/evidence/l16_s3_2026-10-19'
base = Path('/tmp/opencode/l16-s3/run4')
assert np.__version__ == '1.26.4'
receipt = {'scope': 'P3 uncommitted author full gate, not reseal', 'numpy_version': np.__version__,
           'reference': str(here / 'gate-reference-v2.json'),
           'reference_scope': 'Complete aec88d2 control measured before revision3, same native/Haswell/NumPy 1.26.4', 'runs': []}
for name, repo in [('candidate', root)]:
    output = here / ('gate-' + name + '-v4.json')
    log_path = base / ('gate-' + name + '.log')
    if output.exists() or log_path.exists():
        raise FileExistsError(output)
    env = dict(os.environ, RESENSE_REPO=str(repo), PYTHONPATH=str(repo), OPENBLAS_CORETYPE='Haswell',
               OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
               LD_LIBRARY_PATH='/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu')
    command = ['/tmp/opencode/resense-b4-venv/bin/python', str(repo / 'scripts/regression_gate.py'),
               '--cache', '/tmp/opencode/resense-b4-data/cache', '--jobs', '4',
               '--baseline', str(repo / 'docs/evidence/results/regression_baseline_2026-09-29_shell_off.json'),
               '--out', str(output), '--work', str(base / ('gate-' + name + '-work'))]
    sources = [repo / 'resense/calibration.py', repo / 'resense/detector.py']
    fingerprint = {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    run = {'name': name, 'command': command, 'source_sha256': fingerprint,
           'started': datetime.now(timezone.utc).isoformat()}
    print('START', name, flush=True)
    with log_path.open('w') as log:
        result = subprocess.run(command, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
    run.update(returncode=result.returncode, finished=datetime.now(timezone.utc).isoformat(),
               source_unchanged={str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources} == fingerprint,
               log_sha256=hashlib.sha256(log_path.read_bytes()).hexdigest())
    receipt['runs'].append(run)
    (here / 'gate_execution_v4.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('FINISH', name, result.returncode, flush=True)
    if result.returncode:
        print(log_path.read_text(), flush=True)
        sys.exit(result.returncode)
