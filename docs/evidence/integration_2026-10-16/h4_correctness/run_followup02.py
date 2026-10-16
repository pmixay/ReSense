import json
import os
from pathlib import Path
import subprocess
import sys
import time
from run_linux import inventory,TARGET_ROOT,CONTROL_ROOT

OUT = Path('/review/run-004')
OUT.mkdir(exist_ok=False)
commands = []
jobs = [('control',[sys.executable,'/review/scene_runner.py',str(OUT/'control.json')],CONTROL_ROOT),
        ('audit',[sys.executable,'/review/audit_followup.py',str(OUT/'evidence_audit.json')],TARGET_ROOT),
        ('compare',[sys.executable,'/review/compare_followup.py',str(OUT)],TARGET_ROOT)]
for name,argv,root in jobs:
    started = time.time()
    with (OUT/(name+'.txt')).open('xb') as f:
        p = subprocess.run(argv,cwd=root,env=dict(os.environ,PYTHONPATH=str(root)),stdout=f,stderr=subprocess.STDOUT)
    row = dict(argv=argv,cwd=str(root),exit=p.returncode,elapsed_informational_s=time.time()-started)
    print(json.dumps(row),flush=True); commands.append(row)
(OUT/'source_after.json').write_text(json.dumps(dict(target=inventory(TARGET_ROOT,'candidate'),control=inventory(CONTROL_ROOT,'baseline')),indent=2,sort_keys=True)+'\n')
(OUT/'completion.json').write_text(json.dumps(dict(commands=commands),indent=2)+'\n')
raise SystemExit(int(any(r['exit'] for r in commands)))
