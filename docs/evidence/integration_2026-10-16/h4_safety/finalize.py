"""Archive owned runtime states and verify final evidence consistency."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ap=argparse.ArgumentParser(); ap.add_argument('--root',required=True); ap.add_argument('--out',required=True)
a=ap.parse_args(); R=Path(a.root); O=Path(a.out)
assert R.is_dir() and O.is_dir()
states=[]
for launch in sorted(R.glob('*.launch.json')):
    d=json.loads(launch.read_text()); cmd=d['argv']; name=cmd[cmd.index('--name')+1]
    full=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
    assert full['State']['Status']=='exited' and full['State']['ExitCode']==0 and not full['State']['OOMKilled'],name
    assert full['Image']=='sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19'
    assert full['HostConfig']['Memory']<=2*1024**3
    for m in full['Mounts']:
        if m['Destination']!='/out': assert not m['RW'],(name,m)
    states.append(dict(name=name,image=full['Image'],state=full['State'],mounts=full['Mounts'],
        memory_limit=full['HostConfig']['Memory'],nano_cpus=full['HostConfig']['NanoCpus'],argv=cmd))
(O/'runtime.json').write_text(json.dumps(states,indent=2)+'\n')
checks={}
for d in R.iterdir():
    if not d.is_dir(): continue
    c=d/'completion.json'
    if c.exists():
        completion=json.loads(c.read_text()); assert completion['ok']; checks[d.name]=completion
        ident=json.loads((d/'identity.json').read_text())
        assert len(ident['files'])==36
        expected='075a20df9fcdba6605a92e6505ae4dfdb3bf410ec09d17a8b3c79ce714db9292' if '-sealed-' in d.name else 'a34cb1612f3f212d063370ebe0ad8648657aa15b62d751a69964eb1c825d3618'
        assert ident['source_sha256']==expected
dark=json.loads((O/'dark_inherited_comparison.json').read_text())
assert [len(dark[b]['excess']) for b in ['ride_1','ride_3']]==[9,5]
assert all(not dark[b]['lost'] for b in dark)
matches=json.loads((O/'dark_inherited_track_matches.json').read_text())
assert len(matches)==14 and all(x['center_distance']==0.0 for x in matches)
real=json.loads((O/'real_comparison.json').read_text())
assert all(v['stop_sets_equal'] and v['warning_sets_equal'] and not v['descriptor_changes'] for v in real.values())
span=json.loads((O/'span-corrected-fixture.json').read_text())
assert all(bool(x['parts'])==(x['actual_deg']>=.1) for x in span)
assert json.loads((O/'azimuth.json').read_text())['total_mismatches']==0
prom=json.loads((O/'promotion.json').read_text())['witness'][0]
assert prom['tracks_by_object_identity'][0]['id']==422
assert prom['tracks_by_object_identity'][0]['column_held']
assert prom['output_membership']==[dict(id=422,detection=False,warning=False)]
v=json.loads((O/'tall_miss_witness.json').read_text())
assert all(not f['STOP_ids'] for f in v['per_frame'])
rearm=json.loads((O/'rearm_witness.json').read_text())[0]
fs=rearm['frames']
assert fs[8]['STOP_ids'] and fs[9]['STOP_ids'] and not fs[10]['STOP_ids'] and not fs[11]['STOP_ids'] and fs[12]['STOP_ids']
assert fs[11]['pre'][0]['zone']=='gauge' and fs[11]['pre'][0]['n_gauge']==72
assert fs[11]['tracks'][0]['fresh_blocked'] and not fs[11]['tracks'][0]['column_held']
hold=json.loads((O/'hold_release.json').read_text())
delays=json.loads((O/'rearm_delays.json').read_text())
assert hold['STOP_on_first_return']+len(delays)==hold['reported_before_dropout']
assert hold['STOP_on_second_return']==hold['reported_before_dropout']
(O/'verification.json').write_text(json.dumps(dict(artifact_checks='PASS',safety_verdict='BLOCKED',
    completed_workers=checks,notes='Evidence integrity checks are not safety acceptance.'),indent=2)+'\n')
print(json.dumps(dict(completed_workers=len(checks),integrity='PASS',safety='BLOCKED'),indent=2))
