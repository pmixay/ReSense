"""Run unchanged author gates on the current H1 source with fresh receipts."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/h1-reference')
spec = importlib.util.spec_from_file_location('h1_d_driver', ROOT / 'docs/evidence/h1_axis_range_2026-10-19/run_checks.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)
driver.HERE, driver.WORK = HERE, WORK
driver.archived.HERE, driver.archived.WORK = HERE, WORK
archived = driver.archived


def main():
    if '--background' in sys.argv:
        args = [arg for arg in sys.argv[1:] if arg != '--background']
        phase = args[0]
        revision = args[args.index('--revision') + 1]
        name = f'{phase}-{revision}-candidate'
        command = [sys.executable, __file__, *args]
        with (WORK / f'{name}-driver.log').open('x') as stream:
            process = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        with (HERE / f'{name}-job.json').open('x') as stream:
            json.dump(dict(pid=process.pid, command=command), stream, indent=2)
        print('STARTED', name, process.pid, flush=True)
        return 0
    return driver.main()


if __name__ == '__main__':
    sys.exit(main())
