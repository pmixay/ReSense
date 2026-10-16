"""Continue the adopted volume; never re-run setup_units or overwrite run-001."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from run_linux import inventory, TARGET_ROOT, CONTROL_ROOT

OUT = Path('/review/run-002')


def run(name, argv, root=TARGET_ROOT):
    env = dict(os.environ, PYTHONPATH=str(root), RESENSE_REPO=str(root), PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    before = time.time()
    with (OUT/(name+'.txt')).open('xb') as f:
        p = subprocess.run(argv, cwd=root, env=env, stdout=f, stderr=subprocess.STDOUT)
    row = dict(name=name, argv=argv, cwd=str(root), exit=p.returncode, elapsed_informational_s=time.time()-before)
    with (OUT/'commands.jsonl.txt').open('a') as f: f.write(json.dumps(row)+'\n')
    print(json.dumps(row), flush=True)
    return row


def main():
    OUT.mkdir(exist_ok=False)
    results = []
    for mode in ('boundaries','health','tracking','cache','final_axis','node','ast'):
        results.append(run(mode, [sys.executable,'/review/independent_checks.py',mode,str(OUT/(mode+'.json'))]))
    for name, root, mode in (('target_on',TARGET_ROOT,'on'),('target_off',TARGET_ROOT,'off'),('control',CONTROL_ROOT,'off')):
        results.append(run(name, [sys.executable,'/review/independent_checks.py','scenes_'+mode,str(OUT/(name+'.json'))],root))
    results.append(run('evidence_audit',[sys.executable,'/review/evidence_audit.py',str(OUT/'evidence_audit.json')]))
    results.append(run('compare_scenes',[sys.executable,'/review/compare_scenes.py',str(OUT)]))
    source = dict(target=inventory(TARGET_ROOT,'candidate'),control=inventory(CONTROL_ROOT,'baseline'))
    (OUT/'source_after.json').write_text(json.dumps(source,indent=2,sort_keys=True)+'\n')
    (OUT/'completion.json').write_text(json.dumps(dict(results=results),indent=2)+'\n')
    return int(any(r['exit'] for r in results))


if __name__ == '__main__': raise SystemExit(main())
