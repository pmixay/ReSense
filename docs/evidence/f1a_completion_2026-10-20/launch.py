"""Launch explicitly selected owned jobs, retaining immutable driver logs."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WORK = Path('/tmp/opencode/f1a-completion-work')
p = argparse.ArgumentParser()
p.add_argument('jobs', nargs='+', help='phase:side, e.g. gate:reference gate:candidate')
p.add_argument('--revision', default='b')
a = p.parse_args()
env = dict(os.environ, OPENBLAS_CORETYPE='Haswell', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
           LD_LIBRARY_PATH='/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu')
jobs = {}
for job in a.jobs:
    phase, side = job.split(':')
    name = f'{phase}-{a.revision}-{side}'
    command = [sys.executable, str(HERE / 'run_checks.py'), phase, '--side', side, '--revision', a.revision]
    with (WORK / f'{name}-driver.log').open('x') as log:
        child = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
    jobs[name] = dict(pid=child.pid, command=command)
with (WORK / ('jobs-' + '-'.join(jobs) + '.json')).open('x') as stream:
    json.dump(jobs, stream, indent=2)
print(json.dumps(jobs, indent=2))
