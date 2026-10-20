"""Final merged-tree H1 physical/X3 publication checks with exact source receipts."""
import argparse
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/h1-publication')
spec = importlib.util.spec_from_file_location('h1_receipts', ROOT / 'docs/evidence/h1_core_2026-10-19/run_checks.py')
receipts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(receipts)
receipts.HERE, receipts.WORK = HERE, WORK


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['physical', 'x3'])
    args = parser.parse_args()
    WORK.mkdir(exist_ok=True)
    if args.phase == 'x3':
        command = [sys.executable, ROOT / 'scripts/robustness_battery.py', '--repo', ROOT,
            '--cache', '/tmp/opencode/resense-b4-data/decoded', '--out', WORK / 'x3.json', '-j', '2',
            '--reference', ROOT / 'docs/evidence/h1_reference_2026-10-19/x3-e-candidate.json']
    else:
        command = [sys.executable, ROOT / 'docs/evidence/h1_reference_2026-10-19/physical_e.py',
            '--baseline', '/tmp/opencode/h1-axis-range/physical-audit-d.json', '--out', WORK / 'physical.json']
    return receipts.run(args.phase, ROOT, command)


if __name__ == '__main__':
    sys.exit(main())
