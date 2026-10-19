"""Author suite coordinator: explicit sources, immutable outputs and commands."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

repo = Path('/home/aiops/resense')
reference = Path('/tmp/opencode/l16-s3/reference')
work = Path('/tmp/opencode/l16-s3/run4')
here = repo / 'docs/evidence/l16_s3_2026-10-19'
python = '/tmp/opencode/resense-b4-venv/bin/python'
env = dict(os.environ, OPENBLAS_CORETYPE='Haswell', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
           MKL_NUM_THREADS='1', LD_LIBRARY_PATH='/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu')
all_cases = ','.join(map(str, range(24)))
commands = []
for name, cache, cases, keep in (
    ('falcon', '/tmp/opencode/l16-s3/falcon-decoded', all_cases, False),
    ('pandar-empty-ringfree', '/tmp/opencode/resense-b4-data/decoded/roundT_squareT_pressureGate_squareT', all_cases, False),
    ('pandar-positive-ringfree', '/tmp/opencode/resense-b4-data/decoded/doubleT_obstacle', all_cases, False),
    ('pandar-positive-ring', '/tmp/opencode/resense-b4-data/decoded/doubleT_obstacle', all_cases, True),
    ('pandar-empty-ring', '/tmp/opencode/resense-b4-data/decoded/roundT_squareT_pressureGate_squareT', all_cases, True),
):
    if not keep and not (work / (name + '-reference') / 'summary.json').exists():
        commands.append((name + '-reference', [python, str(here / 'replay.py'), '--repo', str(reference),
                         '--cache', cache, '--out', str(work / (name + '-reference')), '--cases', '0,4,5,12', '--jobs', '4']))
    ordered = '0,4,5,12,' + ','.join(str(k) for k in range(24) if k not in (0, 4, 5, 12)) if name == 'falcon' else cases
    commands.append((name + '-candidate', [python, str(here / 'replay.py'), '--repo', str(repo),
                     '--cache', cache, '--out', str(work / (name + '-candidate')), '--cases', ordered,
                     '--jobs', '4', *(['--keep-ring'] if keep else [])]))

commands.extend([
    ('instrumentation-plain', [python, str(here / 'replay.py'), '--repo', str(repo),
       '--cache', '/tmp/opencode/l16-s3/falcon-decoded', '--out', str(work / 'instrumentation-plain'),
       '--cases', '0,4', '--end', '100', '--jobs', '2']),
    ('instrumentation-traced', [python, str(here / 'replay.py'), '--repo', str(repo),
       '--cache', '/tmp/opencode/l16-s3/falcon-decoded', '--out', str(work / 'instrumentation-traced'),
       '--cases', '0,4', '--end', '100', '--jobs', '2', '--trace']),
])
receipt = {'scope': 'uncommitted P3 author source; not formal committed-source acceptance',
           'reference': 'Reused complete same-runtime aec88d2 / NumPy 1.26.4 controls from run2, linked explicitly.', 'runs': []}
source = repo / 'resense/calibration.py'
receipt['calibration_sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
for name, command in commands:
    log_path = work / (name + '.log')
    if log_path.exists():
        raise FileExistsError(log_path)
    run = {'name': name, 'command': command, 'started': datetime.now(timezone.utc).isoformat()}
    print('START', name, flush=True)
    with log_path.open('w') as log:
        result = subprocess.run(command, cwd=repo, env=env, stdout=log, stderr=subprocess.STDOUT)
    run.update(returncode=result.returncode, finished=datetime.now(timezone.utc).isoformat(),
               log_sha256=hashlib.sha256(log_path.read_bytes()).hexdigest())
    receipt['runs'].append(run)
    (here / 'suite_execution_v4.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('FINISH', name, result.returncode, flush=True)
    if result.returncode:
        print(log_path.read_text(), flush=True)
        sys.exit(result.returncode)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == receipt['calibration_sha256']
print('COMPLETE', flush=True)
