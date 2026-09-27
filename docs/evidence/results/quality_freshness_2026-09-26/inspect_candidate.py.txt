import hashlib, importlib, inspect, json
from pathlib import Path
from resense import _native
assert _native.AVAILABLE and _native.enabled(), _native.status()
protocol=json.loads(Path('/evidence/combined_runtime_protocol.json').read_text())
actual={}
for rel, expected in protocol['sources'].items():
    if rel.startswith('resense/'):
        path=Path(inspect.getfile(importlib.import_module(rel[:-3].replace('/','.'))))
    else:
        path=Path('/opt/resense')/rel
    actual[rel]={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    assert actual[rel]['sha256']==expected, (rel, actual[rel], expected)
print(json.dumps({'native':_native.status(),'sources':actual,'passed':True},indent=2))
