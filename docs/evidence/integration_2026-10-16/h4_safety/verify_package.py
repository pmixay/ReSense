"""Read-only byte check of the compact package and staged evidence."""
import hashlib,json,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent
repo=P.parents[3]
prefix=P.relative_to(repo).as_posix()
inventory=json.loads((P/'HASHES.json').read_text())
for name,expected in inventory.items():
    data=(P/name).read_bytes()
    assert len(data)==expected['bytes'] and hashlib.sha256(data).hexdigest()==expected['sha256'],name
    if name!='PROTOCOL.md':
        staged=subprocess.check_output(['git','show',':'+prefix+'/'+name],cwd=repo)
        assert staged==data,('staged byte mismatch',name)
protocol=prefix+'/PROTOCOL.md'
assert subprocess.check_output(['git','show','e39a011:'+protocol],cwd=repo)==subprocess.check_output(['git','show',':'+protocol],cwd=repo)
staged_names=subprocess.check_output(['git','diff','--cached','--name-only'],cwd=repo,text=True).splitlines()
assert all(n.startswith(prefix+'/') for n in staged_names),staged_names
print(json.dumps(dict(compact_files_verified=len(inventory),staged_files=len(staged_names),
    protocol_unchanged=True,safety_verdict='BLOCKED'),indent=2))
