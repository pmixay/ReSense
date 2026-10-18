"""Serial merged-source checks; keep all prior evidence and record exact commands."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--stage', choices=('tests', 'gate', 'gate-reference', 'x3', 'x3-reference', 'b4'), required=True)
    args = parser.parse_args()
    source = args.source.resolve()
    out = Path(__file__).resolve().parent
    data = Path('/home/resense/data')
    work = data / 'b4_merge_reseal'
    baseline = work / 'reference'
    sys.path.insert(0, str(source / 'scripts'))
    from detector_freeze import source_hashes, source_digest

    def git(*words):
        return subprocess.check_output(['git', *words], cwd=source, text=True).strip()

    files = source_hashes(source)
    native = {p.name: sha(p) for p in (source / 'resense').glob('*.so')}
    assert len(native) == 1
    assert not git('status', '--porcelain')
    identity = {'commit': git('rev-parse', 'HEAD'), 'files': files,
                'source_sha256': source_digest(files), 'native': native}
    receipt_path = out / f'{args.stage}_execution.json'
    assert not receipt_path.exists(), 'refuse to overwrite evidence'
    env = dict(os.environ, OPENBLAS_CORETYPE='Haswell', OPENBLAS_NUM_THREADS='1',
               OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1',
               PYTHONPATH=str(source), PYTHONDONTWRITEBYTECODE='1')
    for key in list(env):
        if key.startswith('RESENSE_N2_'):
            del env[key]
    receipt = {'source': identity, 'runner_sha256': sha(Path(__file__)),
               'environment': {k: env[k] for k in ('OPENBLAS_CORETYPE', 'OPENBLAS_NUM_THREADS',
                               'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')},
               'reference': {'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=baseline, text=True).strip(),
                             'files': source_hashes(baseline),
                             'native': {p.name: sha(p) for p in (baseline / 'resense').glob('*.so')}},
               'runs': [], 'status': 'running'}

    def save():
        receipt_path.write_text(json.dumps(receipt, indent=2) + '\n')

    def run(name, command, repo=source):
        command = [str(c) for c in command]
        log = out / f'{name}.log'
        start = time.monotonic()
        entry = {'name': name, 'command': command, 'cwd': str(repo),
                 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        receipt['runs'].append(entry)
        save()
        print('START', name, flush=True)
        with log.open('x') as stream:
            result = subprocess.run(command, cwd=repo,
                                    env=dict(env, PYTHONPATH=str(repo), RESENSE_REPO=str(repo)),
                                    stdout=stream, stderr=subprocess.STDOUT)
        entry.update(exit=result.returncode, wall_s=round(time.monotonic() - start, 3),
                     log_sha256=sha(log), finished_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))
        save()
        print('END', name, result.returncode, entry['wall_s'], flush=True)
        assert result.returncode == 0, f'{name} failed; see {log}'
        assert files == source_hashes(source)
        assert git('rev-parse', 'HEAD') == identity['commit']
        assert native == {p.name: sha(p) for p in (source / 'resense').glob('*.so')}

    save()
    if args.stage == 'tests':
        tests = ['mount_ring_axis', 'orientation_health', 'orientation_replay', 'calibration',
                 'reseed_safety', 'native', 'detector_timing', 'decision_policy', 'wall_drift',
                 'algorithm', 'core', 'modules', 'lowobj_near', 'cpu_savings', 'history_robustness',
                 'envelope', 'fastcloud', 'regression_gate', 'robustness_battery',
                 'health_gate_parity', 'health_histogram', 'cache_extended_ride', 'release',
                 'detector_freeze']
        run('affected_tests', [sys.executable, '-m', 'pytest', '-q',
                              *[f'tests/test_{t}.py' for t in tests], f'--junitxml={out / "affected_tests.xml"}'])
        run('params', ['bash', 'scripts/sync_params.sh', '--check'])
        run('directed', [sys.executable, source / 'docs/evidence/b4_release_2026-10-18/p4/directed_checks.py',
                         '--repo', source, '--cache', data / 'decoded/roundT_squareT_pressureGate_squareT',
                         '--assert-no-loss', '--out', out / 'directed.json'])
    elif args.stage in ('gate', 'gate-reference'):
        selected = baseline if args.stage == 'gate-reference' else source
        run(args.stage, [sys.executable, selected / 'scripts/regression_gate.py', '--cache', data / 'gate_cache',
                     '--jobs', '1', '--baseline', source / 'docs/evidence/results/regression_baseline_2026-09-29_shell_off.json',
                     '--out', out / f'{args.stage}.json', '--work', work / args.stage], selected)
    elif args.stage in ('x3', 'x3-reference'):
        selected = baseline if args.stage == 'x3-reference' else source
        reference = data / 'x3_reference/reference.json' if args.stage == 'x3-reference' else work / 'x3-reference.json'
        run(args.stage, [sys.executable, source / 'scripts/robustness_battery.py', '--repo', selected,
                   '--cache', data / 'x3_reference/cache', '--reference', reference,
                   '--out', work / f'{args.stage}.json', '-j', '1'], selected)
    elif args.stage == 'b4':
        runner = source / 'docs/evidence/b4_orientation_fix_2026-10-18/run_b4.py'
        raw = work / 'b4'
        raw.mkdir()
        for side, repo in (('baseline', baseline), ('candidate', source)):
            assert {sha(p) for p in (repo / 'resense').glob('*.so')} == set(native.values())
            for case, bag in (('empty', 'roundT_squareT_pressureGate_squareT'), ('positive', 'doubleT_obstacle')):
                run(f'b4-{side}-{case}', [sys.executable, runner, '--repo', repo,
                                         '--cache', data / 'decoded' / bag, '--jobs', '1',
                                         '--out', raw / f'b4-{side}-{case}.json'], repo)
        run('b4-summary', [sys.executable, runner.with_name('summarize_b4.py'), '--runs', raw,
                           '--labels', source / 'labels/doubleT_obstacle.json', '--out', out / 'b4_summary.json'])
    receipt['status'] = 'complete'
    save()


if __name__ == '__main__':
    main()
