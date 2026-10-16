"""Same registered scene-function ASTs, imports common to sealed and target sources."""
import ast
from dataclasses import fields,is_dataclass
import hashlib
import json
from pathlib import Path
import sys
import itertools
import numpy as np
import open3d
import resense
from resense import _native
from resense.config import DetectorConfig
from resense.detector import Detector
from resense.frame import Frame

ROOT = Path(resense.__file__).resolve().parents[1]
assert ROOT == Path.cwd() == Path('/work/control') and _native.enabled()
tree = ast.parse(Path('/review/independent_checks.py').read_text())
selected = [n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('freeze','scene','scenes')]
assert len(selected) == 3
exec(compile(ast.Module(body=selected,type_ignores=[]),'/review/independent_checks.py:scene-AST','exec'))
answer = scenes('off')
with Path(sys.argv[1]).open('x') as f: json.dump(answer,f,indent=2,sort_keys=True); f.write('\n')
print(json.dumps(dict(root=str(ROOT),frames=len(answer['rows']),native=_native.status(),numpy=np.__version__,open3d=open3d.__version__,native_path=resense.__file__)))
