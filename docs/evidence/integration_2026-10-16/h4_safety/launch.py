"""Host launcher; retained sources/data are read-only; one <=2 GiB worker."""
import argparse,json,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parent
S=Path(r'C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-h4-safety-20261016')
TEMP=S.parent
assert TEMP.is_dir()
S.mkdir(exist_ok=True)
ap=argparse.ArgumentParser()
ap.add_argument('task',choices=['replay','components'])
ap.add_argument('source',choices=['sealed','candidate'])
ap.add_argument('--mode',default='all')
ap.add_argument('--run',default='run-001')
a=ap.parse_args()
run=S/a.run
run.mkdir(exist_ok=True)
name=f'rs-h4-safety-{a.run}-{a.task}-{a.source}-{a.mode}'
vol='rs-gate-'+('baseline-707ea9cda051-20261016t060147z-68fb3429' if a.source=='sealed' else 'candidate-f8c088dc4f32-20261016t073403z-4b64ec55')+'-checkout'
sub='baseline-707ea9cda051-20261016T060147Z-68fb3429' if a.source=='sealed' else 'candidate-f8c088dc4f32-20261016T073403Z-4b64ec55'
repo='/source/'+sub
cmd=['docker','run','--detach','--name',name,'--label','resense.integration.owner=h4-safety-20261016',
     '--network','none','--cpus','2','--memory','2048m','--memory-swap','3072m',
     '--mount',f'type=volume,source={vol},target=/source,readonly',
     '--mount',r'type=bind,source=C:\Users\alikh\OneDrive\Desktop\projects\ReSense\.git,target=/source.git,readonly',
     '--mount',f'type=bind,source={P},target=/review,readonly',
     '--mount',f'type=bind,source={S},target=/out',
     '--mount',r'type=bind,source=C:\Users\alikh\AppData\Local\Temp\opencode\resense-p3-data\cache,target=/data/cache,readonly',
     '--mount',r'type=bind,source=C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-20261016-runs,target=/h3,readonly',
     '--workdir',repo]
for k,v in dict(PYTHONPATH=repo,RESENSE_REPO=repo,H4_SOURCE=a.source,RESENSE_NATIVE='1',
                H4_OUT=f'/out/{a.run}/{a.task}-{a.source}-{a.mode}',
                OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
                NUMEXPR_NUM_THREADS='1',PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1').items():
    cmd+=['--env',k+'='+v]
cmd+=['--entrypoint','python3','sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19',
      '/review/worker.py',a.task,'--mode',a.mode]
r=subprocess.run(cmd,capture_output=True,text=True)
(run/(name+'.launch.json')).write_text(json.dumps(dict(argv=cmd,stdout=r.stdout,stderr=r.stderr,returncode=r.returncode),indent=2)+'\n')
print(r.stdout+r.stderr)
sys.exit(r.returncode)
