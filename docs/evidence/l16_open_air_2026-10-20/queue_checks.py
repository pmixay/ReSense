"""Run an explicit queue of immutable evidence commands; no detector edits."""
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/l16-open-air-work')
WORK.mkdir(exist_ok=True)
kind = sys.argv[1]
if kind == 'regression':
    tasks = [(phase, side) for phase in ('gate', 'x3') for side in ('reference', 'candidate')]
elif kind == 'gate-followup':
    # The original serial orchestrator may be replaced after full pytest exits.
    # Its already running reference gate keeps its own process and receipt.
    receipt = HERE / 'gate-a-reference-execution.json'
    deadline = time.monotonic() + 7200
    while not receipt.exists():
        if time.monotonic() > deadline:
            raise TimeoutError('reference gate receipt did not arrive')
        time.sleep(10)
    assert json.loads(receipt.read_text())['returncode'] == 0
    tasks = [('gate', 'candidate')]
elif kind == 'x3':
    tasks = [('x3', side) for side in ('reference', 'candidate')]
elif kind == 'recordings':
    tasks = [(phase, side) for phase in ('prefix', 'full') for side in ('reference', 'candidate')]
elif kind == 'analytic':
    tasks = [('red', 'reference'), ('analytic', 'reference'), ('analytic', 'candidate'), ('trace', 'candidate')]
elif kind == 'tests':
    tasks = [('tests', 'candidate')]
else:
    raise ValueError(kind)
for phase, side in tasks:
    code = subprocess.run([sys.executable, HERE / 'run_checks.py', phase, '--side', side]).returncode
    print(phase, side, code, flush=True)
    if code:
        (WORK / f'{kind}-queue-complete.json').write_text(json.dumps({'returncode': code, 'failed': [phase, side]}))
        sys.exit(code)
(WORK / f'{kind}-queue-complete.json').write_text(json.dumps({'returncode': 0, 'tasks': tasks}))
