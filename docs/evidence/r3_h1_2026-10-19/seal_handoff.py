"""Verify archive receipts and retain the final attribution follow-up separately."""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
W=Path('/tmp/opencode/r3-h1')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


manifest={}
target=HERE/'carry-trace.tar.gz'
with tarfile.open(target,'x:gz') as t:
    for p in sorted(W.glob('carry-final*')):
        if p.is_file():
            manifest[p.name]={'bytes':p.stat().st_size,'sha256':sha(p)}
            t.add(p,arcname=p.name,recursive=False)
with tarfile.open(target) as t:
    actual={}
    for m in t:
        data=t.extractfile(m).read()
        actual[m.name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
assert actual==manifest
receipt=dict(archive=target.name,bytes=target.stat().st_size,sha256=sha(target),
             all_members_reopened_and_verified=True,members=manifest)
(HERE/'carry-trace-manifest.json').write_text(json.dumps(receipt,indent=2)+'\n')
author=json.loads((HERE/'author-acceptance.json').read_text())
author['archive_receipts'].append({k:v for k,v in receipt.items() if k!='members'})
for name,h in author['source_files'].items():
    assert sha(ROOT/name)==h
    blob=subprocess.check_output(['git','show',f"{author['source_commit']}:{name}"],cwd=ROOT)
    assert hashlib.sha256(blob).hexdigest()==h
for item in author['archive_receipts']:
    assert sha(HERE/item['archive'])==item['sha256']
author['R3']['unmatched_alarm_followup']='unmatched-alarm-audit.json; all7 new rows retained; nominal1/7 branch checked'
(HERE/'author-acceptance.json').write_text(json.dumps(author,indent=2)+'\n')
gate=json.loads((HERE/'final-gate-frame-review.json').read_text())
x3=json.loads((HERE/'x3-final-candidate.json').read_text())
audit=json.loads((HERE/'final-raw-audit.json').read_text())
print('gated metrics',sum(r['gated'] for r in gate['gate_metrics']))
print('X3 comparisons',sum(len(v) for v in x3['comparison']['cases'].values()))
print('attribution rows independently checked',sum(len(v['checked']) for v in audit['attribution'].values()))
print('carry trace',receipt['sha256'])
print('source and all archive receipts verified')
