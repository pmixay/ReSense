"""Package precise measured sources and raw evidence; reopen and hash every member."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
W=Path('/tmp/opencode/r3-h1')
SOURCE='b14cfd0'


def read(p):
    return json.loads(p.read_text())


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def package(name,paths,base):
    target=HERE/f'{name}.tar.gz'
    members={}
    with tarfile.open(target,'x:gz') as t:
        for path in sorted(paths):
            rel=str(path.relative_to(base))
            members[rel]={'bytes':path.stat().st_size,'sha256':sha(path)}
            t.add(path,arcname=rel,recursive=False)
    verified={}
    with tarfile.open(target) as t:
        for m in t:
            assert m.isfile()
            data=t.extractfile(m).read()
            verified[m.name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    assert members==verified
    manifest={'archive':target.name,'bytes':target.stat().st_size,'sha256':sha(target),
              'all_members_reopened_and_verified':True,'members':members}
    (HERE/f'{name}-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return {k:v for k,v in manifest.items() if k!='members'}


audit=read(HERE/'final-raw-audit.json')
supp=read(HERE/'final-supplement-audit.json')
gate=read(HERE/'gate-final-candidate.json')
x3=read(HERE/'x3-final-candidate.json')
assert gate['code']['commit'].startswith(SOURCE)
assert not gate['code']['uncommitted_detector_changes'] and gate['config']['set']==[]
assert x3['status']=='PASS' and not x3['errors']
assert not any(v['lost_STOP'] for v in audit['X3'].values())
assert not any(v['lost'] for v in audit['gate'].values())
assert not audit['set_F_lost_hits']
assert not any(v['lost_matched'] or v['new_off_object_STOP_decisions'] for v in supp['range'].values())
tests=list(ET.parse(HERE/'affected-final.xml').iter('testcase'))
assert len(tests)==287 and not any(t.find(k) is not None for t in tests for k in ['failure','error','skipped'])
e6=supp['range']['E6-nominal']['candidate']
hanging=x3['entries']['cloud_with_fake_obj/nominal']['metrics']['objects']['thin_hanging']
assert e6['first_stop_X']>=80 and e6['held_from_X']>=60 and hanging['first_stop_m']>=45
false_changes=[]
for key,entry in x3['entries'].items():
    old=read(HERE/'x3-reference.json')['entries'][key]['metrics']
    new=entry['metrics']
    for metric in ['false_stop_episodes','outside_false_stop_episodes','unmatched_stop_episodes']:
        if metric in old and new[metric]!=old[metric]:
            false_changes.append(dict(case=key,metric=metric,baseline=old[metric],candidate=new[metric]))
freeze=subprocess.run([sys.executable,str(ROOT/'scripts/detector_freeze.py'),'verify'],cwd=ROOT,
                      capture_output=True,text=True)
(HERE/'predecessor-freeze-verification.txt').write_text(freeze.stdout+freeze.stderr)
assert freeze.returncode!=0
files=read(ROOT/'docs/evidence/detector_freeze_2026-10-18_b4_merged.json')['files']
source_hashes={name:sha(ROOT/name) for name in files}
for name,h in source_hashes.items():
    data=subprocess.check_output(['git','show',f'{SOURCE}:{name}'],cwd=ROOT)
    assert hashlib.sha256(data).hexdigest()==h,name
assert (ROOT/'configs/default.yaml').read_bytes()==(ROOT/'ros2_ws/src/resense_ros/config/detector.yaml').read_bytes()
assert sha(ROOT/'resense/_resense_native.so')==sha(W/'reference/resense/_resense_native.so')
source_paths=[ROOT/name for name in files]+[ROOT/'resense/_resense_native.so',ROOT/'tests/test_cable_confirmation.py']
source=package('final-source',source_paths,ROOT)
raw_paths=[p for p in W.rglob('*') if p.is_file() and not p.is_symlink()
           and p.relative_to(W).parts[0]!='reference' and 'decoded' not in p.relative_to(W).parts
           and p.suffix not in ['.npz','.pyc']]
raw=package('raw-evidence',raw_paths,W)
shutil.copy2(HERE/'gate-final-candidate.json',HERE/'proposed-regression-baseline.json')
receipt=dict(status='P3_AUTHOR_R3_ACCEPTANCE_PASS',source_commit=gate['code']['commit'],
             reference_commit=read(HERE/'gate-reference.json')['code']['commit'],
             source_sha256=hashlib.sha256(json.dumps(source_hashes,sort_keys=True).encode()).hexdigest(),
             source_files=source_hashes,tests_passed=len(tests),
             R3=dict(E6=e6,hanging_node=hanging,
                     hanging_compact_gate=gate['set_O']['objects']['thin_hanging'],
                     lost_old_gate_STOP=0,lost_old_X3_STOP=0,lost_old_SetF_hits=0,
                     empty_gate_added_STOP=0,nominal_E6_added_unmatched=0,
                     X3_false_episode_changes=false_changes),
             H1=dict(status='HIGH_OPEN_DIAGNOSIS_AND_NEW_APPROACH_DELIVERED',
                     free_top_enabled=False,prototype=read(HERE/'h1-prototype.json')),
             X3=dict(cases=len(x3['entries']),rows=sum(v['metrics']['frames'] for v in x3['entries'].values()),
                     formal_same_input_current_main_comparison='PASS',
                     historical_1_1_0_numerical_comparison=audit['historical_1_1_0']['numerical_checks_pass'],
                     historical_strict_container_parity=False,
                     limitation='Canonical Windows comparison is exact for3132/3133 inputs; known Set O332 mismatch persists.'),
             archive_receipts=[source,raw],
             source_matches_measured_git_blobs=True,native_sha256=sha(ROOT/'resense/_resense_native.so'),
             independent_P4_review='PENDING',P1_reseal='PENDING',
             predecessor_seal_verify_returncode=freeze.returncode)
(HERE/'author-acceptance.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('source',source)
print('raw',raw)
print('X3 false episode changes',false_changes)
print(receipt['status'],receipt['source_sha256'])
