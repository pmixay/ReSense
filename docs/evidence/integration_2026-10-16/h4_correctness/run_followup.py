import json
import os
from pathlib import Path
import subprocess
import sys
import time
from run_linux import inventory,TARGET_ROOT,CONTROL_ROOT

OUT = Path('/review/run-003')
OUT.mkdir(exist_ok=False)
commands = []
for mode in ('boundaries','health','tracking'):
    argv = [sys.executable,'/review/followup_checks.py',mode,str(OUT/(mode+'.json'))]
    started = time.time()
    with (OUT/(mode+'.txt')).open('xb') as f:
        p = subprocess.run(argv,cwd=TARGET_ROOT,env=dict(os.environ,PYTHONPATH=str(TARGET_ROOT)),stdout=f,stderr=subprocess.STDOUT)
    row = dict(argv=argv,cwd=str(TARGET_ROOT),exit=p.returncode,elapsed_informational_s=time.time()-started)
    print(json.dumps(row),flush=True); commands.append(row)
(OUT/'source_after.json').write_text(json.dumps(dict(target=inventory(TARGET_ROOT,'candidate'),control=inventory(CONTROL_ROOT,'baseline')),indent=2,sort_keys=True)+'\n')
(OUT/'completion.json').write_text(json.dumps(dict(commands=commands),indent=2)+'\n')
raise SystemExit(int(any(r['exit'] for r in commands)))
