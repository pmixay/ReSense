"""Committed-source paired gate and X3. Raw logs/results are never overwritten."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
WORK = Path('/tmp/opencode/r3-h1')
REF = WORK/'reference'
DATA = Path('/tmp/opencode/resense-b4-data')
HERE = Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(name, repo, args):
    sources = {str(p.relative_to(repo)):sha(p) for folder in ['resense','native','configs',
               'ros2_ws/src/resense_ros/config'] for p in (repo/folder).rglob('*')
               if p.is_file() and p.suffix in ['.py','.so','.cpp','.yaml'] and '__pycache__' not in str(p)}
    command = [sys.executable, *map(str,args)]
    env=dict(os.environ,RESENSE_REPO=str(repo),PYTHONPATH=str(repo),OPENBLAS_CORETYPE='Haswell',
             OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',
             LD_LIBRARY_PATH='/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu')
    entry=dict(name=name,repo=str(repo),command=command,source_sha256=sources,
               commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
               started=datetime.now(timezone.utc).isoformat())
    print('START',name,flush=True)
    with (WORK/f'{name}.log').open('x') as log:
        result=subprocess.run(command,cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT)
    entry.update(returncode=result.returncode,finished=datetime.now(timezone.utc).isoformat(),
                 source_unchanged=all(sha(repo/p)==s for p,s in sources.items()),
                 log_sha256=sha(WORK/f'{name}.log'))
    (HERE/f'{name}-execution.json').write_text(json.dumps(entry,indent=2)+'\n')
    print('END',name,result.returncode,flush=True)
    return entry


def main():
    p=argparse.ArgumentParser()
    p.add_argument('phase',choices=['gate','x3'])
    p.add_argument('--revision',default='')
    p.add_argument('--candidate-only',action='store_true')
    a=p.parse_args()
    assert np.__version__=='1.26.4'
    binary=ROOT/'resense/_resense_native.so'
    target=REF/'resense/_resense_native.so'
    if not target.exists():
        shutil.copy2(binary,target)
    assert sha(binary)==sha(target)
    if a.phase=='gate':
        def one(pair):
            side,repo=pair
            name=f'gate-{a.revision+"-" if a.revision else ""}{side}'
            return run(name,repo,[repo/'scripts/regression_gate.py',
                       '--cache',DATA/'cache','--jobs','4',
                       '--baseline',repo/'docs/evidence/results/regression_baseline_2026-09-29_shell_off.json',
                       '--out',HERE/f'{name}.json','--work',WORK/f'{name}-work'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            pairs=[('candidate',ROOT)] if a.candidate_only else [('reference',REF),('candidate',ROOT)]
            entries=list(pool.map(one,pairs))
    else:
        entries=[]
        for side,repo in [('reference',REF),('candidate',ROOT)]:
            if a.candidate_only and side=='reference':
                continue
            name=f'x3-{a.revision+"-" if a.revision else ""}{side}'
            args=[ROOT/'scripts/robustness_battery.py','--repo',repo,'--cache',DATA/'decoded',
                  '--out',WORK/f'{name}.json','-j','2']
            if side=='candidate':
                args+=['--reference',WORK/'x3-reference.json']
            entries.append(run(name,repo,args))
            shutil.copy2(WORK/f'{name}.json',HERE/f'{name}.json')
    assert all(e['source_unchanged'] for e in entries)
    return 1 if any(e['returncode'] for e in entries) else 0


if __name__=='__main__':
    sys.exit(main())
