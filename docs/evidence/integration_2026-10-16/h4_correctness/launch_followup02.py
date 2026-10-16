import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
argv = ['docker','run','-d','--name','resense-h4-correctness-20261016-05',
        '--volumes-from','resense-h4-correctness-20261016-01','--cpus','2','--memory','5g','--network','none',
        '--mount',r'type=bind,source=C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-20261016-runs,target=/h3-external,readonly',
        '--env','OMP_NUM_THREADS=1','--env','OPENBLAS_NUM_THREADS=1','--env','MKL_NUM_THREADS=1',
        '--env','NUMEXPR_NUM_THREADS=1','--env','PYTHONHASHSEED=0','--entrypoint','python3',
        'sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19','/review/run_followup02.py']
with (HERE/'followup02-launch.json').open('x') as f: json.dump(dict(argv=argv),f,indent=2); f.write('\n')
p = subprocess.run(argv,capture_output=True,text=True)
with (HERE/'followup02-launch-result.json').open('x') as f: json.dump(dict(exit=p.returncode,stdout=p.stdout,stderr=p.stderr),f,indent=2); f.write('\n')
print(p.stdout,p.stderr)
raise SystemExit(p.returncode)
