"""Wait for owned immutable runs, then audit their raw outputs."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/l16-open-air-work')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeout', type=int, default=7200)
    parser.add_argument('--only', nargs='+', choices=['recordings', 'gate', 'x3'])
    args = parser.parse_args()
    pending = {'recordings': 'full-positive-ring-a-candidate',
               'gate': 'gate-a-candidate', 'x3': 'x3-a-candidate'}
    if args.only:
        pending = {key: pending[key] for key in args.only}
    deadline = time.monotonic() + args.timeout
    while pending:
        for phase, name in list(pending.items()):
            receipt = HERE / f'{name}-execution.json'
            if not receipt.exists():
                continue
            assert json.loads(receipt.read_text())['returncode'] == 0, name
            print('AUDIT', phase, flush=True)
            with (WORK / f'audit-{phase}.log').open('x') as log:
                subprocess.run([sys.executable, HERE / 'audit_results.py', phase],
                               stdout=log, stderr=subprocess.STDOUT, check=True)
            print('PASS', phase, flush=True)
            pending.pop(phase)
        if pending:
            for queue in ('recordings', 'gate-followup', 'x3'):
                status = WORK / f'{queue}-queue-complete.json'
                if status.exists():
                    assert json.loads(status.read_text())['returncode'] == 0, queue
            if time.monotonic() >= deadline:
                print('Still running:', ', '.join(pending), flush=True)
                return 3
            time.sleep(20)
    for phase in ('tests', 'sources'):
        subprocess.run([sys.executable, HERE / 'audit_results.py', phase], check=True,
                       stdout=subprocess.DEVNULL)
        print('PASS', phase, flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
