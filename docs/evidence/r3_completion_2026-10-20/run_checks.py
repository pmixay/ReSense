"""Immutable, source-bound R3 completion checks."""
import argparse
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/r3-completion-work')
REFERENCE = Path('/tmp/opencode/r3-completion-reference')
DATA = Path('/tmp/opencode/resense-b4-data')
spec = importlib.util.spec_from_file_location('receipts', ROOT / 'docs/evidence/h1_core_2026-10-19/run_checks.py')
receipts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(receipts)
receipts.HERE, receipts.WORK = HERE, WORK


def main():
    p = argparse.ArgumentParser()
    p.add_argument('phase', choices=['gate', 'x3', 'falcon', 'analytic', 'affected', 'tests', 'range', 'diagnose'])
    p.add_argument('--side', choices=['reference', 'candidate'], default='candidate')
    p.add_argument('--revision', default='a')
    a = p.parse_args()
    WORK.mkdir(exist_ok=True)
    repo = REFERENCE if a.side == 'reference' else ROOT
    name = f'{a.phase}-{a.revision}-{a.side}'
    out = WORK / name
    command = [sys.executable]
    if a.phase == 'gate':
        command += [repo / 'scripts/regression_gate.py', '--cache', DATA / 'cache', '--jobs', '2',
                    '--baseline', repo / 'docs/evidence/results/regression_baseline_2026-09-29_shell_off.json',
                    '--out', HERE / f'{name}.json', '--work', out]
    elif a.phase == 'x3':
        command += [ROOT / 'scripts/robustness_battery.py', '--repo', repo, '--cache', DATA / 'decoded',
                    '--out', WORK / f'{name}.json', '-j', '2']
        if a.side == 'candidate':
            # Authenticated previous main run permits both fresh sides in parallel.
            # The independent audit also compares every row to the fresh base run.
            command += ['--reference', '/tmp/opencode/l16-open-air-work/x3-merged-candidate.json']
    elif a.phase == 'falcon':
        command += [repo / 'docs/evidence/judgement_2026-10-13/scripts/probe.py',
                    '/tmp/opencode/l16-s3/falcon-decoded', out]
    elif a.phase == 'analytic':
        command += [HERE / 'analytic.py', '--out', WORK / f'{name}.json']
    elif a.phase == 'range':
        command += [repo / 'docs/evidence/judgement_2026-10-13/scripts/range_test.py',
                    '/tmp/opencode/r3-h1/baseline/cache/roundT_squareT_pressureGate_squareT',
                    '/tmp/opencode/r3-h1/baseline/icp_roundT_squareT_pressureGate_squareT.json', out,
                    '--obj', '0.05,0.05,2.6', '--start', '150', '--d0', '230', '--end', '340', '--base', '0.2']
    else:
        command += ['-m', 'pytest', '-q', '--junitxml', WORK / f'{name}.xml']
        if a.phase == 'affected':
            command += ['tests/' + f'test_{module}.py' for module in (
                'cable_current_support', 'cable_confirmation', 'ego_veto', 'explained_run',
                'thin_hanging', 'fresh_stop_evidence', 'far_thin', 'near_escalation',
                'column_collision_core', 'column_axis_anchor', 'column_free_top', 'h4_spare_rearm',
                'modules', 'core', 'algorithm', 'native', 'low_height_keep', 'f1a_b1')]
        elif a.phase == 'diagnose':
            command += ['tests/test_algorithm.py::test_timing_with_accumulation',
                        'tests/test_lidar_proxy_hook.py::test_child_process_inherits_hook_and_bad_source_fails_closed',
                        'tests/test_node.py::test_obstacle_is_stop_and_published_in_the_sensor_frame']
    return receipts.run(name, repo, command)


if __name__ == '__main__':
    sys.exit(main())
