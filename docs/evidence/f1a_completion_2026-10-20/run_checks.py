"""Immutable source-bound F1a checks; detector edits happen outside these runs."""
import argparse
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/f1a-completion-work')
REFERENCE = Path('/tmp/opencode/f1a-completion-reference')
DATA = Path('/tmp/opencode/resense-b4-data')
spec = importlib.util.spec_from_file_location('receipts', ROOT / 'docs/evidence/h1_core_2026-10-19/run_checks.py')
receipts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(receipts)
receipts.HERE, receipts.WORK = HERE, WORK


def main():
    p = argparse.ArgumentParser()
    p.add_argument('phase', choices=['gate', 'x3', 'falcon', 'physical', 'ride', 'affected', 'tests'])
    p.add_argument('--side', choices=['reference', 'candidate'], default='candidate')
    p.add_argument('--revision', default='b')
    a = p.parse_args()
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
            command += ['--reference', '/tmp/opencode/r3-completion-work/x3-a-candidate.json']
    elif a.phase == 'falcon':
        command += [repo / 'docs/evidence/judgement_2026-10-13/scripts/probe.py',
                    '/tmp/opencode/l16-s3/falcon-decoded', out]
    elif a.phase == 'physical':
        command += [ROOT / 'docs/evidence/f1a_b1_2026-10-20/physical.py', '--out', WORK / f'{name}.json']
    elif a.phase == 'ride':
        command += [repo / 'docs/evidence/f1_false_alarms_2026-10-19/scripts/replay.py',
                    '--cache', DATA / 'cache', '--bag', 'new_data', '--out', out, '--full']
    else:
        command += ['-m', 'pytest', '-q', '--junitxml', WORK / f'{name}.xml']
        if a.phase == 'affected':
            command += ['tests/' + f'test_{module}.py' for module in (
                'f1a_continuation', 'f1a_b1', 'f1_false_alarms', 'low_height_keep', 'lowobj_near',
                'low_local_support', 'rail_start', 'modules', 'core', 'algorithm', 'native',
                'cable_current_support', 'cable_confirmation', 'ego_veto', 'explained_run')]
    return receipts.run(name, repo, command)


if __name__ == '__main__':
    sys.exit(main())
