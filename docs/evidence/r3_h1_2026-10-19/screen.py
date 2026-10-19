"""Run unchanged range/probe on a fixed object-free current-main placement."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
WORK = Path('/tmp/opencode/r3-h1')
DATA = Path('/tmp/opencode/resense-b4-data')
A = 'roundT_squareT_pressureGate_squareT'
p = argparse.ArgumentParser()
p.add_argument('tag')
p.add_argument('--repo', type=Path, default=ROOT)
a = p.parse_args()
assert np.__version__ == '1.26.4'
out = WORK / a.tag
out.mkdir(exist_ok=False)
j = ROOT / 'docs/evidence/judgement_2026-10-13/scripts'
commands = [
    [j/'range_test.py',WORK/'baseline/cache'/A,WORK/'baseline'/f'icp_{A}.json',out/'E6',
     '--obj','0.05,0.05,2.6','--start','150','--d0','230','--end','340','--base','0.2'],
    [j/'probe.py', DATA/'decoded/cloud_with_fake_obj',out/'setO']]


def one(args):
    import os
    env = dict(os.environ, RESENSE_REPO=str(a.repo), PYTHONPATH=str(a.repo))
    with (out/f'{Path(args[0]).stem}.log').open('w') as log:
        proc = subprocess.run([sys.executable,*map(str,args)],cwd=a.repo,env=env,
                              stdout=log,stderr=subprocess.STDOUT)
    assert proc.returncode == 0
    return dict(command=list(map(str,args)),returncode=proc.returncode)


with ThreadPoolExecutor(max_workers=2) as pool:
    receipt = list(pool.map(one,commands))
(out/'commands.json').write_text(json.dumps(receipt,indent=2))
print(out)
