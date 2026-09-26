"""Export an exact local review candidate, retaining failed acceptance; reload offline and restore baseline."""
import datetime, hashlib, json, os, subprocess
from pathlib import Path
ROOT=Path('/home/resense/worktrees/monitoring-quality')
VALID=Path('/home/resense/validation/quality_cycle/freshness')
IMAGE='resense:quality-candidate'
VERSION='quality-0145cbb'
ARCHIVE=VALID/'archive'/f'resense-image-{VERSION}.tar.gz'
EXPECTED=json.loads((VALID/'candidate_image_receipt.json').read_text())['Id']

def call(cmd, **kwargs): return subprocess.check_output(cmd, cwd=ROOT, text=True, **kwargs).strip()
def image_id(tag): return call(['docker','image','inspect','-f','{{.Id}}',tag])
def main():
    required=['original_cold','original_warm','original_clear','original_cold_load','stock_switch','stock_switch_recording1','stock_switch_recording2']
    outcomes={name:json.loads((VALID/(name+'_result.json')).read_text())['exit_code'] for name in required}
    assert all(code in (0,1) for code in outcomes.values()), outcomes
    accepted=all(code==0 for code in outcomes.values())
    assert json.loads((VALID/'original_cold_load_workload_result.json').read_text())['valid']
    with (VALID/'archive_started.json').open('x') as f:
        json.dump({'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'image_id':EXPECTED,'version_tag':VERSION},f)
    assert image_id(IMAGE)==EXPECTED
    baseline=image_id('resense:latest')
    subprocess.check_call(['docker','tag','resense:latest','resense:p3d-reference'])
    assert image_id('resense:p3d-reference')==baseline
    env=os.environ.copy();env.update(SKIP_BUILD='1',SOURCE_IMAGE=IMAGE,VERSION=VERSION,WITH_BASE='1',OUT_DIR=str(VALID/'archive'))
    with (VALID/'archive_export.log').open('w') as out:
        subprocess.check_call([str(ROOT/'scripts/export_image.sh')],cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT)
    digest=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    assert (Path(str(ARCHIVE)+'.sha256').read_text().split()[0])==digest
    # No candidate tag remains available before loading. The old baseline tag remains intact.
    tags=json.loads(call(['docker','image','inspect','-f','{{json .RepoTags}}',IMAGE]))
    with (VALID/'archive_load.log').open('w') as out:
        subprocess.check_call(['docker','image','rm',*tags],stdout=out,stderr=subprocess.STDOUT)
        assert subprocess.run(['docker','image','inspect',EXPECTED],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
        subprocess.check_call([str(ROOT/'scripts/load_image.sh'),str(ARCHIVE)],cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
        assert image_id('resense:latest')==EXPECTED
        subprocess.check_call(['docker','tag','resense:latest',IMAGE],stdout=out,stderr=subprocess.STDOUT)
        subprocess.check_call(['docker','run','--rm','--network','none','-w','/', '-v',str(VALID)+':/evidence:ro',IMAGE,'python3','/evidence/inspect_candidate.py'],stdout=out,stderr=subprocess.STDOUT)
    app=call(['docker','run','--rm','--network','none','-w','/',IMAGE,'python3','-c','import json,resense; print(json.dumps({"version":resense.__version__,"module":resense.__file__}))'])
    receipt={'finished_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'archive':str(ARCHIVE),'sha256':digest,'bytes':ARCHIVE.stat().st_size,'image_id':EXPECTED,'image_revision':'0145cbb8dd26b3777084aedb3945f49dda741caf','package':json.loads(app),'inherited_oci_version':'22.04 (Ubuntu base; not application version)','baseline_preserved':{'tag':'resense:p3d-reference','image_id':baseline},'candidate_absent_before_load':True,'loaded_source_and_native_check':True,'public_release':False,'offline_build_cache_claim':False,'runtime_acceptance_passed':accepted,'runtime_outcomes':outcomes,'artifact_status':'local review candidate; release hold; standalone clear criterion failed' if not accepted else 'local validated candidate; release hold'}
    assert image_id('resense:p3d-reference')==baseline
    if not accepted:
        subprocess.check_call(['docker','tag','resense:p3d-reference','resense:latest'])
        assert image_id('resense:latest')==baseline
        receipt['baseline_restored_as_latest']=True
    (VALID/'archive_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
if __name__=='__main__': main()
