"""Host-side read-only runtime/source review records and compact result summary."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def save(name,answer):
    with (HERE/name).open('x',encoding='utf-8',newline='\n') as f: json.dump(answer,f,indent=2,sort_keys=True); f.write('\n')


def load(rel): return json.loads((HERE/rel).read_text())


containers = []
for i in range(1,6):
    name = 'resense-h4-correctness-20261016-'+str(i).zfill(2)
    raw = json.loads(subprocess.check_output(['docker','inspect',name]))[0]
    assert not raw['State']['Running']
    save('container-final-'+str(i).zfill(2)+'.json',raw)
    with (HERE/('container-log-'+str(i).zfill(2)+'.txt')).open('xb') as f:
        subprocess.run(['docker','logs','--timestamps',name],stdout=f,stderr=subprocess.STDOUT,check=True)
    containers.append(dict(name=name,id=raw['Id'],image=raw['Image'],state=raw['State']))

commands = []
for name,argv in (
    ('reviewed-core-diff.txt',['git','diff','707ea9c','7cc640f','--','resense','configs/default.yaml','ros2_ws/src/resense_ros/config/detector.yaml']),
    ('reviewed-runtime-diff.txt',['git','diff','3fdc87957f5d09ff32573eabe6637924b91ea376','7cc640f','--','ros2_ws/src/resense_ros/resense_ros/detector_node.py','ros2_ws/src/resense_ros/launch/detector.launch.py']),
    ('scope-current-core-diff.txt',['git','diff','7cc640f','HEAD','--','resense','native','configs','ros2_ws/src/resense_ros','scripts/decision_policy_import.py','scripts/rescore_decisions.py','scripts/build_native.sh','pyproject.toml']),
):
    p = subprocess.run(argv,cwd=ROOT,capture_output=True)
    assert p.returncode == 0
    with (HERE/name).open('xb') as f: f.write(p.stdout); f.write(p.stderr)
    if name == 'scope-current-core-diff.txt': assert p.stdout == b''
    commands.append(dict(argv=argv,cwd=str(ROOT),exit=p.returncode,output=name))

families = defaultdict(list)
comparison = load('run-004/scene_comparison.json')
for row in comparison['rows']:
    families[json.dumps(row['key'][:3])].append(row)
family_summary = []
for key,rows in families.items():
    last = rows[-1]
    family_summary.append(dict(scene=json.loads(key),frames=len(rows),finite_caps=sum(r['wall_drift']<1e9 for r in rows),
                               stops=sum(r['obstacle'] for r in rows),last={k:last[k] for k in ('wall_drift','error_at_cap_bin','monitored','clear','obstacle')}))

source_checks = []
for rel in ('run-001/source_before.json','run-001/source_after_units.json','run-002/source_after.json','run-003/source_after.json','run-004/source_after.json'):
    data = load(rel)
    for role in ('target','control'):
        assert len(data[role]['files']) == 36
        assert all(v['matches_git'] and v['matches_h3'] and not v['crlf'] for v in data[role]['files'].values())
        assert not data[role]['tracked_status'] and not data[role]['windows_pyd']
    source_checks.append(dict(path=rel,target_head=data['target']['head'],control_head=data['control']['head'],target_files=36,control_files=36))

audit = load('run-004/evidence_audit.json')
answer = dict(argv=sys.argv,verdict='PASS',remaining_medium_or_higher_findings=[],containers=containers,
              source_checks=source_checks,reviewed_commands=commands,
              units=dict(passed=572,failed=0,skipped=0,files=22),
              independent=dict(boundaries=load('run-003/boundaries.json')['cases'],health=load('run-003/health.json'),
                               spare_histories=load('run-003/tracking.json')['spare_cases'],actual_track_clear_cap_cases=load('run-003/tracking.json')['actual_track_clear_cap_cases'],
                               cache=load('run-002/cache.json'),final_axis=load('run-002/final_axis.json'),node=load('run-002/node.json'),ast=load('run-002/ast.json'),
                               scene_comparison={k:v for k,v in comparison.items() if k != 'rows'},scene_families=family_summary),
              retained_h3=dict(package_hashes=audit['package_hashes'],external_hashes=audit['external_hashes'],copy_mappings=audit['copy_mappings'],counts=audit['counts'],classified_non_axis_changes=audit['classified_non_axis_changes']))
save('RESULTS.json',answer)
print(json.dumps(dict(verdict=answer['verdict'],scene_families=family_summary,source_checks=len(source_checks),containers=[dict(name=r['name'],exit=r['state']['ExitCode'],oom=r['state']['OOMKilled']) for r in containers]),indent=2))
