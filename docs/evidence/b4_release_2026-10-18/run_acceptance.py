#!/usr/bin/env python3
"""Prospective, serial acceptance on a committed B4 candidate; fail on any error."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import time


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--stage', choices=('tests', 'gates', 'b4', 'x3', 'all'), default='all')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    out = Path(__file__).resolve().parent
    ref, data, work = args.reference.resolve(), args.data.resolve(), args.work.resolve()
    work.mkdir(exist_ok=True)
    scope = ['resense', 'native', 'configs', 'setup.py', 'pyproject.toml',
             'scripts/build_native.sh', 'ros2_ws/src/resense_ros/config']

    def git(repo, *words):
        return subprocess.check_output(['git', *words], cwd=repo, text=True).strip()

    identities = {}
    for side, repo in (('baseline', ref), ('candidate', root)):
        assert not git(repo, 'diff', 'HEAD', '--', *scope), f'dirty {side} source'
        identities[side] = {'commit': git(repo, 'rev-parse', 'HEAD'),
                            'files': {str(p.relative_to(repo)): digest(p) for p in
                                      sorted((repo / 'resense').glob('*.py'))},
                            'config_sha256': digest(repo / 'configs/default.yaml'),
                            'native_sha256': {p.name: digest(p) for p in (repo / 'resense').glob('*resense_native*.so')}}
    receipt_path = out / 'run_receipts.json'
    receipt = json.loads(receipt_path.read_text()) if receipt_path.exists() else {'identities': identities, 'runs': []}
    assert receipt['identities'] == identities, 'candidate/reference changed across stages'
    env = dict(os.environ, OPENBLAS_CORETYPE='Haswell', OPENBLAS_NUM_THREADS='1',
               OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1',
               RESENSE_REQUIRE_SYNTHETIC='1')

    def save():
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')

    def run(name, command, repo=root):
        log = out / f'{name}.log'
        assert not log.exists(), f'refuse to replace {log}'
        command = [str(c) for c in command]
        selected_env = dict(env, PYTHONPATH=str(repo), RESENSE_REPO=str(repo))
        t0 = time.monotonic()
        print('START', name, flush=True)
        with log.open('x') as output:
            result = subprocess.run(command, cwd=repo, env=selected_env, stdout=output, stderr=subprocess.STDOUT)
        receipt['runs'].append({'name': name, 'command': command, 'cwd': str(repo),
                                'exit': result.returncode, 'wall_s': round(time.monotonic() - t0, 2),
                                'log_sha256': digest(log)})
        save()
        print('END', name, result.returncode, receipt['runs'][-1]['wall_s'], flush=True)
        assert result.returncode == 0, f'{name} failed: {log}'
        for side, checkout in (('baseline', ref), ('candidate', root)):
            assert not git(checkout, 'diff', 'HEAD', '--', *scope), f'{side} changed during measurement'
            assert git(checkout, 'rev-parse', 'HEAD') == identities[side]['commit']

    def archive(folder, name):
        destination = out / name
        assert not destination.exists()
        with tarfile.open(destination, 'w:xz') as target:
            for path in sorted(folder.rglob('*')):
                if path.is_file():
                    target.add(path, arcname=str(path.relative_to(folder)))

    save()
    if args.stage in ('tests', 'all'):
        tests = ['mount_ring_axis', 'calibration', 'reseed_safety', 'native', 'detector_timing',
                 'decision_policy', 'wall_drift', 'algorithm', 'core', 'modules', 'lowobj_near',
                 'cpu_savings', 'history_robustness', 'envelope', 'fastcloud', 'regression_gate',
                 'robustness_battery', 'health_gate_parity', 'health_histogram', 'cache_extended_ride']
        run('pytest', [sys.executable, '-m', 'pytest', '-q',
                       *[f'tests/test_{t}.py' for t in tests], f'--junitxml={out / "pytest.xml"}'])
        run('lint', [sys.executable, 'scripts/check_archived_lint.py', '--lint', '--ruff',
                     Path(sys.executable).with_name('ruff')])
        run('params', ['bash', 'scripts/sync_params.sh', '--check'])
        run('directed', [sys.executable, out / 'p4/directed_checks.py', '--assert-no-loss',
                         '--out', out / 'directed.json'])
    if args.stage in ('gates', 'all'):
        for side, repo in (('baseline', ref), ('candidate', root)):
            raw = work / f'gate-{side}'
            run(f'gate-{side}', [sys.executable, repo / 'scripts/regression_gate.py',
                                '--cache', data / 'cache', '--jobs', '4',
                                '--baseline', root / 'docs/evidence/results/regression_baseline_2026-09-29_shell_off.json',
                                '--out', out / f'gate-{side}.json', '--work', raw], repo)
            gate = json.loads((out / f'gate-{side}.json').read_text())
            assert gate['code']['commit'] == identities[side]['commit']
            assert gate['code']['uncommitted_detector_changes'] == []
            assert gate['gate']['passed'] and gate['gate']['same'] == 208
            archive(raw, f'gate-{side}-raw.tar.xz')
    if args.stage in ('b4', 'all'):
        raw = work / 'b4'
        raw.mkdir()
        runner = root / 'docs/evidence/b4_orientation_fix_2026-10-18/run_b4.py'
        for side, repo in (('baseline', ref), ('candidate', root)):
            for case, bag in (('empty', 'roundT_squareT_pressureGate_squareT'), ('positive', 'doubleT_obstacle')):
                run(f'b4-{side}-{case}', [sys.executable, runner, '--repo', repo, '--cache', data / 'decoded' / bag,
                                         '--out', raw / f'b4-{side}-{case}.json', '--jobs', '4'], repo)
        run('b4-summary', [sys.executable, runner.with_name('summarize_b4.py'), '--runs', raw,
                           '--labels', root / 'labels/doubleT_obstacle.json', '--out', out / 'b4-summary.json'])
        archive(raw, 'b4-raw.tar.xz')
    if args.stage in ('x3', 'all'):
        for side, repo in (('baseline', ref), ('candidate', root)):
            report = work / f'x3-{side}.json'
            command = [sys.executable, root / 'scripts/robustness_battery.py', '--repo', repo,
                       '--cache', data / 'decoded', '--out', report, '-j', '2']
            if side == 'candidate':
                command += ['--reference', work / 'x3-baseline.json']
            run(f'x3-{side}', command, repo)
            shutil.copy2(report, out / report.name)
            archive(report.with_suffix('.raw'), f'x3-{side}-raw.tar.xz')
    print('ACCEPTANCE STAGE COMPLETE', args.stage, flush=True)


if __name__ == '__main__':
    main()
