"""Launch owned immutable runs; receipts are written by run_checks.py."""
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = Path('/tmp/opencode/r3-completion-work')
WORK.mkdir(exist_ok=True)
env = dict(os.environ, OPENBLAS_CORETYPE='Haswell', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
           LD_LIBRARY_PATH='/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu')
jobs = {}
for phase in ('gate', 'x3', 'falcon', 'analytic', 'range'):
    for side in ('reference', 'candidate'):
        name = f'{phase}-a-{side}'
        command = [sys.executable, str(HERE / 'run_checks.py'), phase, '--side', side]
        with (WORK / f'{name}-driver.log').open('x') as log:
            child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                     start_new_session=True)
        jobs[name] = dict(pid=child.pid, command=command)
with (WORK / 'jobs-a.json').open('x') as stream:
    json.dump(jobs, stream, indent=2)
print(json.dumps(jobs, indent=2))
