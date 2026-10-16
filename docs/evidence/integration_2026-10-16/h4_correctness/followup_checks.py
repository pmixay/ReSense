"""Narrow registered fixture/serialization fixes; original probe retained intact."""
import inspect
import json
from pathlib import Path
import sys

import independent_checks as base

name,out = sys.argv[1:3]
if name == 'boundaries':
    answer = base.boundaries()
else:
    fn = base.health_properties if name == 'health' else base.tracking_properties
    source = inspect.getsource(fn)
    old,new = ('np.linspace(-34., 34., 3000)', 'np.linspace(-34., 34., 24000)') if name == 'health' else (
        '(False, True, False, True, True, True, True, True)',
        '(False, True, False, True, True, True, True, True, True, True, True, True, True)')
    assert source.count(old) == 1
    # Transform only owned probe text, not any production source or loaded method.
    source = source.replace(old,new)
    scope = dict(vars(base))
    exec(compile(source,'/review/followup_checks.py:registered_fixture','exec'),scope)
    answer = scope[fn.__name__]()
answer = base.freeze(answer)
with Path(out).open('x') as f: json.dump(answer,f,indent=2,sort_keys=True); f.write('\n')
print(json.dumps({k:v for k,v in answer.items() if k not in ('rows','sequence')},indent=2))
raise SystemExit(int(bool(answer.get('failures'))))
