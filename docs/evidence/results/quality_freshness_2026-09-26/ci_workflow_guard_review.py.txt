import contextlib,io,json,shlex,subprocess,sys,tempfile,types
from pathlib import Path
import yaml
root=Path('/home/resense/ReSense')
workflow=yaml.safe_load((root/'.github/workflows/ci.yml').read_text())
checks=[]
for job in workflow['jobs'].values():
 for step in job['steps']:
  run=step.get('run','')
  for line in run.splitlines():
   if 'docker run -d --name' in line and '_node ' in line:
    assert 'freshness_mode:=replay' in line, line
    checks.append('inline node explicitly replays')
   if line.strip().startswith('python3 scripts/check_dry_run.py '):
    assert '--require-freshness' in line,line
    checks.append('inline checker requires freshness')
for rel in ('scripts/smoke_test.sh','scripts/console_test.sh','scripts/internal_net_test.sh'):
 s=(root/rel).read_text()
 assert 'freshness_mode:=replay' in s and '--require-freshness' in s,rel
 checks.append(rel+' enforces replay+freshness')
step=next(s for s in workflow['jobs']['offline-build']['steps'] if 'resense_rt_node --network' in s.get('run',''))
run=step['run']
with tempfile.NamedTemporaryFile('w',suffix='.sh') as f:
 f.write(run);f.flush();subprocess.run(['bash','-n',f.name],check=True)
checks.append('loaded runtime step Bash syntax')
line=next(l for l in run.replace('\\\n',' ').splitlines() if 'from resense import _native as n;' in l)
tokens=shlex.split(line);code=tokens[tokens.index('-c')+1]
original=sys.modules.get('resense')
try:
 for available,enabled in ((False,False),(False,True),(True,False),(True,True)):
  n=types.SimpleNamespace(AVAILABLE=available,enabled=lambda:enabled,status=lambda:'stub')
  sys.modules['resense']=types.SimpleNamespace(_native=n)
  failed=False
  try:
   with contextlib.redirect_stdout(io.StringIO()):exec(code)
  except AssertionError:failed=True
  assert failed is not (available and enabled),(available,enabled)
  checks.append(f'native available={available}, enabled={enabled}: '+('reject' if failed else 'accept'))
finally:
 if original is None:sys.modules.pop('resense',None)
 else:sys.modules['resense']=original
print(json.dumps({'passed':True,'checks':checks},indent=2))
