"""Plain/traced equality on both sources, with identical diagnostic-latency inputs."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
W=Path('/tmp/opencode/r3-h1')
A='roundT_squareT_pressureGate_squareT'
p=argparse.ArgumentParser()
p.add_argument('--revision',default='')
p.add_argument('--candidate-only',action='store_true')
a=p.parse_args()
out=W/f'trace{("-"+a.revision) if a.revision else ""}'
out.mkdir(exist_ok=False)


def one(job):
    side,repo,case=job
    prefix=out/f'{side}-{case}'
    if case=='E6':
        args=['range',W/'baseline/cache'/A,W/'baseline'/f'icp_{A}.json','OUT',
              '--obj','0.05,0.05,2.6','--start','150','--d0','230','--end','340','--base','0.2']
        extra,index,ext=[],3,'.json'
    else:
        args=['probe','/tmp/opencode/resense-b4-data/decoded/cloud_with_fake_obj','OUT','--end','791']
        extra=['--labels',ROOT/'labels/cloud_with_fake_obj.json','--window','thin_hanging:760:790']
        index,ext=2,'.jsonl'
    env=dict(os.environ,RESENSE_REPO=str(repo),PYTHONPATH=str(repo))
    commands=[]
    for mode in ['off','on']:
        aa=args.copy()
        aa[index]=str(prefix)+'.'+mode
        command=[sys.executable,str(HERE/'run_observed.py'),'run','--repo',str(repo),'--out',str(prefix),
                 *map(str,(['--hooks-off'] if mode=='off' else extra+['--keep-frames'])),*map(str,aa)]
        with Path(str(prefix)+f'.{mode}.log').open('x') as log:
            result=subprocess.run(command,cwd=repo,env=env,stdout=log,stderr=subprocess.STDOUT)
        assert result.returncode==0, prefix
        commands.append(command)
    on=Path(str(prefix)+'.on'+ext)
    off=Path(str(prefix)+'.off'+ext)
    command=[sys.executable,str(ROOT/'scripts/range_attrib.py'),'verify',str(prefix),str(on),str(off)]
    result=subprocess.run(command,cwd=repo,env=env,check=True)
    return dict(side=side,case=case,returncode=result.returncode,commands=commands)


sources=[('candidate',ROOT)] if a.candidate_only else [('reference',W/'reference'),('candidate',ROOT)]
jobs=[(side,repo,case) for side,repo in sources
      for case in ['E6','setO']]
with ThreadPoolExecutor(max_workers=2) as pool:
    runs=list(pool.map(one,jobs))
(HERE/f'trace{("-"+a.revision) if a.revision else ""}-execution.json').write_text(json.dumps(runs,indent=2))
