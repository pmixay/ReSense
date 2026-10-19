"""Immutable source receipts for the H1/main integration checks."""
import argparse
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/h1-trajectory')
spec = importlib.util.spec_from_file_location('h1_receipts', ROOT / 'docs/evidence/h1_core_2026-10-19/run_checks.py')
receipts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(receipts)
receipts.HERE, receipts.WORK = HERE, WORK


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['gate', 'tests', 'probes'])
    args = parser.parse_args()
    name = f'merged-{args.phase}'
    if args.phase == 'gate':
        command = [sys.executable, ROOT / 'scripts/regression_gate.py',
            '--cache', '/tmp/opencode/resense-b4-data/cache', '--jobs', '4',
            '--baseline', ROOT / 'docs/evidence/results/regression_baseline_2026-09-29_shell_off.json',
            '--out', HERE / 'merged-gate.json', '--work', WORK / 'merged-gate-work']
    elif args.phase == 'tests':
        command = [sys.executable, '-m', 'pytest', '-q', '--junitxml', WORK / 'merged-tests.xml']
    else:
        spec2 = importlib.util.spec_from_file_location('h1_probe_checks', ROOT / 'docs/evidence/h1_axis_range_2026-10-19/run_checks.py')
        probes = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(probes)
        probes.HERE, probes.WORK = HERE, WORK
        probes.archived.HERE, probes.archived.WORK = HERE, WORK
        sys.argv = [sys.argv[0], 'probes', '--revision', 'merged']
        return probes.main()
    return receipts.run(name, ROOT, command)


if __name__ == '__main__':
    sys.exit(main())
