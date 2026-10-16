"""Normalize generated compact evidence and inventory this owned package."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
prior=P/'PACKAGE_TRANSFORMS.json'
transforms=json.loads(prior.read_text()) if prior.exists() else []
for p in sorted((P/'results').glob('*.json')):
    old=p.read_bytes(); new=old.replace(b'\r\n',b'\n')
    json.loads(new)
    if old!=new:
        p.write_bytes(new)
        transforms.append(dict(path=p.relative_to(P).as_posix(),
            before_sha256=hashlib.sha256(old).hexdigest(),after_sha256=hashlib.sha256(new).hexdigest()))
(P/'PACKAGE_TRANSFORMS.json').write_bytes((json.dumps(transforms,indent=2)+'\n').encode())
files={}
for p in sorted(P.rglob('*')):
    if p.is_file() and p.name!='HASHES.json':
        b=p.read_bytes(); files[p.relative_to(P).as_posix()]=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
(P/'HASHES.json').write_bytes((json.dumps(files,indent=2)+'\n').encode())
print(json.dumps(dict(files=len(files),bytes=sum(x['bytes'] for x in files.values())),indent=2))
