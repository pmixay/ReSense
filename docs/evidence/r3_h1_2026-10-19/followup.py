"""Fixed post-selection perturbations and critical controls on explicit sources."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
W=Path('/tmp/opencode/r3-h1')
DATA=Path('/tmp/opencode/resense-b4-data')
REF=W/'reference'
A='roundT_squareT_pressureGate_squareT'
C='roundT_pressureGate_roundT'
J=ROOT/'docs/evidence/judgement_2026-10-13/scripts'
p=argparse.ArgumentParser()
p.add_argument('mode',choices=['range','falcon'])
p.add_argument('--revision',default='')
p.add_argument('--candidate-only',action='store_true')
a=p.parse_args()
assert np.__version__=='1.26.4'
out=W/f'supplement-{a.revision+"-" if a.revision else ""}{a.mode}'
out.mkdir(exist_ok=False)


def call(job):
    name,repo,args=job
    command=[sys.executable,*map(str,args)]
    env=dict(os.environ,RESENSE_REPO=str(repo),PYTHONPATH=str(repo))
    start=datetime.now(timezone.utc).isoformat()
    with (out/f'{name}.log').open('x') as log:
        proc=subprocess.run(command,cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT)
    assert proc.returncode==0,name
    return dict(name=name,repo=str(repo),command=command,returncode=proc.returncode,
                commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),
                started=start,finished=datetime.now(timezone.utc).isoformat())


jobs=[]
if a.mode=='range':
    if a.candidate_only:
        decoded=W/'supplement-range/decoded'
        icp=W/'supplement-range'/f'icp_{C}.json'
        assert (decoded/C/'meta.json').exists() and icp.exists()
    else:
        decoded=out/'decoded'
        decoded.mkdir()
        call(('decode-C',REF,[J/'cache_decoded.py',DATA/'for_hackathon'/C,decoded/C]))
        with tarfile.open(ROOT/'docs/evidence/p4_eval_1.1.0_2026-10-16/raw/p4_raw_2026-10-16.tar.xz') as t:
            icp=out/f'icp_{C}.json'
            icp.write_bytes(t.extractfile(f'x1/icp/icp_{C}.json').read())
        call(('placement-C',REF,['-c',f"import sys; sys.path.insert(0,'{J}'); import range_test as t; "
              f"t.baseline('{decoded/C}', '{decoded}/{C}_baseline.json')"]))
    for side,repo in [('reference',REF),('candidate',ROOT)]:
        if a.candidate_only and side=='reference':
            continue
        for variant in ['nominal','pitch_p2','pitch_m2','roll_p2','drop30_s1','drop30_s2','drop30_s3','drop30_s7','dedup']:
            name=f'{side}-E6-{variant}'
            jobs.append((name,repo,[HERE/'cable_probe.py',variant,W/'baseline/cache'/A,
                         W/'baseline'/f'icp_{A}.json',out/name,'--obj','0.05,0.05,2.6',
                         '--start','150','--d0','230','--end','340','--base','0.2']))
        name=f'{side}-A-axis'
        jobs.append((name,repo,[J/'range_test.py',W/'baseline/cache'/A,W/'baseline'/f'icp_{A}.json',
                     out/name,'--obj','0.3,0.3,2.8','--start','150','--d0','230','--end','340']))
        name=f'{side}-C-person'
        jobs.append((name,repo,[J/'range_test.py',decoded/C,icp,out/name,
                     '--obj','0.5,0.5,1.75','--start','0','--d0','230']))
else:
    for side,repo in [('reference',REF),('candidate',ROOT)]:
        if a.candidate_only and side=='reference':
            continue
        name=f'{side}-Falcon'
        jobs.append((name,repo,[J/'probe.py','/tmp/opencode/l16-s3/falcon-decoded',out/name]))

with ThreadPoolExecutor(max_workers=2) as pool:
    receipt=list(pool.map(call,jobs))
(HERE/f'supplement-{a.revision+"-" if a.revision else ""}{a.mode}-execution.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(out)
