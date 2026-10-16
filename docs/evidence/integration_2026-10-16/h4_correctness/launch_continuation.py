"""Host-side exact invocation and Docker adoption provenance, write-once outputs."""
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
IMAGE = 'sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19'
OLD = 'resense-h4-correctness-20261016-01'
ATTEMPT = sys.argv[1] if len(sys.argv) > 1 else '02'
NEW = 'resense-h4-correctness-20261016-' + ATTEMPT
EXTERNAL = r'C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-20261016-runs'


def save(name,data):
    with (HERE/name).open('x',encoding='utf-8',newline='\n') as f: json.dump(data,f,indent=2); f.write('\n')


original = json.loads(subprocess.check_output(['docker','inspect',OLD]))[0]
assert original['State']['ExitCode'] == 0 and not original['State']['Running']
assert original['Image'] == IMAGE
save('adopted-container-'+ATTEMPT+'.json',original)
with (HERE/('adopted-container-log-'+ATTEMPT+'.txt')).open('xb') as f:
    subprocess.run(['docker','logs','--timestamps',OLD],stdout=f,stderr=subprocess.STDOUT,check=True)
argv = ['docker','run','-d','--name',NEW,'--volumes-from',OLD,'--cpus','2','--memory','5g','--network','none',
        '--mount',f'type=bind,source={EXTERNAL},target=/h3-external,readonly',
        '--label','resense.integration.owner=h4-correctness-20261016',
        '--env','OMP_NUM_THREADS=1','--env','OPENBLAS_NUM_THREADS=1','--env','MKL_NUM_THREADS=1',
        '--env','NUMEXPR_NUM_THREADS=1','--env','PYTHONHASHSEED=0','--entrypoint','python3',IMAGE,'/review/resume_linux.py']
save('continuation-launch-'+ATTEMPT+'.json',dict(argv=argv,adopted=OLD,reused_volume='resense-h4-correctness-20261016-01'))
p = subprocess.run(argv,capture_output=True,text=True)
save('continuation-launch-result-'+ATTEMPT+'.json',dict(exit=p.returncode,stdout=p.stdout,stderr=p.stderr))
print(p.stdout,p.stderr)
raise SystemExit(p.returncode)
