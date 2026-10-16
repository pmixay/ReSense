"""Write-once owned evidence inventory, excluding itself and ignored Python caches."""
import ast
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
rows = []
python_files = 0
for path in sorted(HERE.rglob('*')):
    if not path.is_file() or '__pycache__' in path.parts or path.name == 'HASHES.json': continue
    data = path.read_bytes()
    if path.suffix == '.py':
        ast.parse(data,filename=str(path)); python_files += 1
    rows.append(dict(path=path.relative_to(HERE).as_posix(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest()))
with (HERE/'HASHES.json').open('x',encoding='utf-8',newline='\n') as f:
    json.dump(dict(argv=sys.argv,python_syntax_files=python_files,files=rows),f,indent=2,sort_keys=True); f.write('\n')
print(json.dumps(dict(files=len(rows),bytes=sum(r['bytes'] for r in rows),python_syntax_files=python_files)))
