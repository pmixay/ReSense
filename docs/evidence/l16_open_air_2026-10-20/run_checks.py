"""Source-bound L16 A1 acceptance runs; outputs are exclusive, never overwritten."""
import argparse
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/l16-open-air-work')
REFERENCE = Path('/tmp/opencode/l16-open-air-reference')
DATA = Path('/tmp/opencode/resense-b4-data')
spec = importlib.util.spec_from_file_location(
    'l16_receipts', ROOT / 'docs/evidence/h1_core_2026-10-19/run_checks.py')
receipts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(receipts)
receipts.HERE, receipts.WORK = HERE, WORK


def main():
    p = argparse.ArgumentParser()
    p.add_argument('phase', choices=['gate', 'x3', 'prefix', 'full', 'analytic', 'trace', 't1', 'tests', 'red', 'diagnose', 'nodes', 'affected', 'falcon'])
    p.add_argument('--side', choices=['reference', 'candidate'], default='candidate')
    p.add_argument('--revision', default='a')
    p.add_argument('--jobs', default='2')
    p.add_argument('--repo', type=Path)
    p.add_argument('--reference', type=Path)
    a = p.parse_args()
    WORK.mkdir(exist_ok=True)
    repo = a.repo or (REFERENCE if a.side == 'reference' else ROOT)
    name = f'{a.phase}-{a.revision}-{a.side}'
    out = WORK / name
    command = [sys.executable]
    if a.phase == 'gate':
        command += [repo / 'scripts/regression_gate.py', '--cache', DATA / 'cache', '--jobs', a.jobs,
            '--baseline', repo / 'docs/evidence/results/regression_baseline_2026-09-29_shell_off.json',
            '--out', HERE / f'{name}.json', '--work', out]
    elif a.phase == 'x3':
        command += [ROOT / 'scripts/robustness_battery.py', '--repo', repo, '--cache', DATA / 'decoded',
                    '--out', WORK / f'{name}.json', '-j', a.jobs]
        if a.side == 'candidate':
            command += ['--reference', a.reference or WORK / f'x3-{a.revision}-reference.json']
    elif a.phase == 'falcon':
        command += [repo / 'docs/evidence/judgement_2026-10-13/scripts/probe.py',
                    '/tmp/opencode/l16-s3/falcon-decoded', out]
    elif a.phase in ('prefix', 'full'):
        return recordings(a, repo)
    elif a.phase in ('analytic', 'trace'):
        command += [HERE / 'analytic.py', '--out', WORK / f'{name}.json']
        if a.phase == 'trace':
            command += ['--trace']
    elif a.phase == 't1':
        command += [HERE / 'real_starts.py', '--out', WORK / f'{name}.json']
    else:
        command += ['-m', 'pytest', '-q', '--junitxml', WORK / f'{name}.xml']
        if a.phase == 'red':
            command += [ROOT / 'tests/test_open_air_orientation.py', '-k', 'ground_half_space', '--maxfail=1']
        elif a.phase == 'diagnose':
            command += ['tests/test_algorithm.py::test_timing_with_accumulation',
                        'tests/test_lidar_proxy_hook.py::test_child_process_inherits_hook_and_bad_source_fails_closed',
                        'tests/test_node.py::test_status_marker_says_the_decision_and_publishing_errors_are_contained']
        elif a.phase == 'nodes':
            # Import the post-failure reporter without changing detector imports.
            entry = ('import sys, runpy; sys.path.insert(0, ' + repr(str(HERE))
                     + '); sys.argv = ["pytest", *sys.argv[1:]]; runpy.run_module("pytest", run_name="__main__")')
            command = [sys.executable, '-c', entry, *command[3:], 'tests/test_node.py', '-p', 'pytest_diagnostics']
        elif a.phase == 'affected':
            command += ['tests/' + name for name in (
                'test_open_air_orientation.py', 'test_directional_orientation.py', 'test_directional_history.py',
                'test_orientation_budget.py', 'test_orientation_health.py', 'test_mount_ring_axis.py',
                'test_orientation_numeric.py', 'test_calibration.py', 'test_orientation_replay.py',
                'test_f1a_b1.py', 'test_f1_false_alarms.py', 'test_low_height_keep.py', 'test_lowobj_near.py',
                'test_low_local_support.py', 'test_rail_start.py', 'test_late_candidates.py', 'test_k1_k2_axis.py',
                'test_native.py')]
    code = receipts.run(name, repo, command)
    return int(code != 1) if a.phase == 'red' else code


def recordings(a, repo):
    groups = [
        ('falcon', Path('/tmp/opencode/l16-s3/falcon-decoded'), False),
        ('empty-ringfree', DATA / 'decoded/roundT_squareT_pressureGate_squareT', False),
        ('positive-ringfree', DATA / 'decoded/doubleT_obstacle', False),
        ('empty-ring', DATA / 'decoded/roundT_squareT_pressureGate_squareT', True),
        ('positive-ring', DATA / 'decoded/doubleT_obstacle', True)]
    for group, cache, ring in groups:
        name = f'{a.phase}-{group}-{a.revision}-{a.side}'
        command = [sys.executable, ROOT / 'docs/evidence/l16_s3_2026-10-19/replay.py',
                   '--repo', repo, '--cache', cache, '--out', WORK / name, '--jobs', a.jobs,
                   '--cases', ','.join(map(str, range(24))) if a.phase == 'prefix' else '0,4,5,12']
        if a.phase == 'prefix':
            command += ['--end', '32']
        if ring:
            command += ['--keep-ring']
        code = receipts.run(name, repo, command)
        if code:
            return code
    return 0


if __name__ == '__main__':
    sys.exit(main())
