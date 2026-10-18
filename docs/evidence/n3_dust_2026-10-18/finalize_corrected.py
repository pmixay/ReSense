"""Wait for both immutable corrected batteries; never certify a partial/failed run."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time

HERE = Path('/home/resense/ReSense/docs/evidence/n3_dust_2026-10-18')
DATA = Path('/home/resense/data/dust')
STATUS = DATA / 'corrected_finalizer_status.json'
os.nice(10)
pending = {'regular', 'set_f'}
results = {}
env = {**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'}
while pending:
    for name in sorted(pending):
        path = DATA / ('corrected_regular_status.json' if name == 'regular' else 'set_f_corrected_status.json')
        try:
            state = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if (state.get('state') == 'failed' or state.get('status') == 'failed'
                or any(job.get('status') == 'failed' for job in state.get('jobs', []))):
            raise RuntimeError(f'{name} measurement failed; no completeness report certified')
        if state.get('state', state.get('status')) != 'complete':
            continue
        command = ([sys.executable, str(HERE / 'summarize_regular_dust.py')] if name == 'regular'
                   else [sys.executable, str(HERE / 'summarize_set_f.py'),
                         '--out', str(HERE / 'set_f_baseline_pose_fixed'),
                         '--bank', str(DATA / 'set_f_bank_pose_fixed')])
        print(json.dumps({'verifying': name, 'command': command}), flush=True)
        completed = subprocess.run(command, cwd=HERE.parents[2], env=env)
        results[name] = {'returncode': completed.returncode, 'utc_epoch': time.time()}
        STATUS.write_text(json.dumps({'pid': os.getpid(), 'results': results}, indent=2) + '\n')
        if completed.returncode:
            raise RuntimeError(f'{name} complete-only verification failed')
        pending.remove(name)
    if pending:
        time.sleep(30)
STATUS.write_text(json.dumps({'pid': os.getpid(), 'status': 'complete', 'results': results}, indent=2) + '\n')
print('Both corrected batteries passed complete-coverage/provenance verification; acceptance remains in their measured results.', flush=True)
