"""Fresh H1 follow-up runs; reuse the archived source/receipt implementation."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/h1-axis-range')
REF = Path('/tmp/opencode/h1-axis-range-reference')
DATA = Path('/tmp/opencode/resense-b4-data')
spec = importlib.util.spec_from_file_location('h1_archived_checks',
    ROOT / 'docs/evidence/h1_core_2026-10-19/run_checks.py')
archived = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archived)
archived.HERE, archived.WORK = HERE, WORK


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=['gate', 'probes', 'x3', 'trace', 'tests'])
    parser.add_argument('--revision', required=True)
    parser.add_argument('--side', choices=['candidate', 'reference'], default='candidate')
    parser.add_argument('--background', action='store_true')
    parser.add_argument('--reference', type=Path)
    args = parser.parse_args()
    WORK.mkdir(exist_ok=True)
    if not (REF / 'resense/_resense_native.so').exists():
        shutil.copy2(ROOT / 'resense/_resense_native.so', REF / 'resense/_resense_native.so')
    assert archived.sha(ROOT / 'resense/_resense_native.so') == archived.sha(REF / 'resense/_resense_native.so')
    repo = ROOT if args.side == 'candidate' else REF
    name = f'{args.phase}-{args.revision}-{args.side}'
    if args.background:
        with (WORK / f'{name}-driver.log').open('x') as log:
            command = [sys.executable, __file__, args.phase, '--revision', args.revision, '--side', args.side]
            if args.reference:
                command += ['--reference', str(args.reference)]
            child = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                     start_new_session=True)
        with (HERE / f'{name}-job.json').open('x') as stream:
            json.dump(dict(pid=child.pid, command=child.args, log=str(WORK / f'{name}-driver.log')), stream, indent=2)
        print('STARTED', name, child.pid, flush=True)
        return 0
    if args.phase == 'gate':
        return archived.run(name, repo, [sys.executable, repo / 'scripts/regression_gate.py', '--cache', DATA / 'cache',
            '--jobs', '4', '--baseline', repo / 'docs/evidence/results/regression_baseline_2026-09-29_shell_off.json',
            '--out', HERE / f'{name}.json', '--work', WORK / f'{name}-work'])
    if args.phase == 'x3':
        command = [sys.executable, repo / 'scripts/robustness_battery.py', '--repo', repo, '--cache', DATA / 'decoded',
                   '--out', WORK / f'{name}.json', '-j', '2']
        if args.side == 'candidate':
            command += ['--reference', args.reference or WORK / f'x3-{args.revision}-reference.json']
        code = archived.run(name, repo, command)
        shutil.copy2(WORK / f'{name}.json', HERE / f'{name}.json')
        return code
    if args.phase == 'trace':
        return archived.run(name, repo, [sys.executable, HERE / 'trace_ranges.py', args.revision])
    if args.phase == 'tests':
        return archived.run(name, repo, [sys.executable, HERE / 'verify_tests.py'])
    out = WORK / name
    out.mkdir(exist_ok=False)
    j = ROOT / 'docs/evidence/judgement_2026-10-13/scripts'
    r3 = Path('/tmp/opencode/r3-h1')
    a, c = 'roundT_squareT_pressureGate_squareT', 'roundT_pressureGate_roundT'
    jobs = [
        ('A-axis', [j / 'range_test.py', r3 / 'baseline/cache' / a, r3 / 'baseline' / f'icp_{a}.json',
                    out / 'A-axis', '--obj', '0.3,0.3,2.8', '--start', '150', '--d0', '230', '--end', '340']),
        ('C-person', [j / 'range_test.py', r3 / 'supplement-range/decoded' / c,
                      r3 / 'supplement-range' / f'icp_{c}.json', out / 'C-person',
                      '--obj', '0.5,0.5,1.75', '--start', '0', '--d0', '230']),
        ('E6', [j / 'range_test.py', r3 / 'baseline/cache' / a, r3 / 'baseline' / f'icp_{a}.json',
                out / 'E6', '--obj', '0.05,0.05,2.6', '--start', '150', '--d0', '230', '--end', '340', '--base', '0.2']),
        ('Falcon', [j / 'probe.py', '/tmp/opencode/l16-s3/falcon-decoded', out / 'Falcon']),
    ]
    results = {}
    for label, command in jobs:
        results[label] = archived.run(f'{name}-{label}', repo, [sys.executable, *command])
    with (HERE / f'{name}.json').open('x') as stream:
        json.dump(results, stream, indent=2)
    return int(any(results.values()))


if __name__ == '__main__':
    sys.exit(main())
