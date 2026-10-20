"""Fresh paired Set F runs with fixed original RNG order and immutable receipts."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = Path('/tmp/opencode/r3-sustained')
CACHE = Path('/tmp/opencode/resense-b4-data/cache/new_data')
sys.path.insert(0, str(ROOT))
from scripts.cache_io import cache_files  # noqa: E402
from scripts.far_range_eval import consecutive_files  # noqa: E402


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources():
    paths = [p for folder in ['resense', 'native', 'configs', 'ros2_ws/src/resense_ros/config']
             for p in (ROOT / folder).rglob('*')
             if p.is_file() and p.suffix in ('.py', '.so', '.cpp', '.yaml') and '__pycache__' not in p.parts]
    paths += [ROOT / p for p in ['scripts/far_range_eval.py', 'scripts/cache_io.py',
                                'docs/extended_dataset_intake.json']]
    return {str(p.relative_to(ROOT)): sha(p) for p in sorted(paths)}


def main():
    WORK.mkdir(exist_ok=False)
    all_files = cache_files(CACHE)
    selected = set()
    for number in [46, 68, 98, 140, 168, 172]:
        start = next(i for i, p in enumerate(all_files) if Path(p).name.startswith(f'new_data_{number}_'))
        selected.update(map(Path, consecutive_files(all_files, start, 110)))
    selected.update(CACHE.glob('*_stamps.json'))
    inputs = {str(p.relative_to(CACHE)): sha(p) for p in sorted(selected)}
    with (HERE / 'input-manifest.json').open('x') as out:
        json.dump(inputs, out, indent=2)
    before = sources()
    config = yaml.safe_load((ROOT / 'configs/default.yaml').read_text())
    config['resense']['tracking']['cable_confirm_time_s'] = 0.0
    off = WORK / 'r3-off.yaml'
    off.write_text(yaml.safe_dump(config, sort_keys=False))
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()

    def run(side):
        config_path = off if side == 'off' else ROOT / 'configs/default.yaml'
        command = [sys.executable, str(ROOT / 'scripts/far_range_eval.py'),
            '--cache', str(CACHE), '--files', '46,68,98,140,168,172',
            '--kinds', 'person,box1.0,box0.5,trolley,cable', '--start', '220', '--frames', '110',
            '--lateral=-0.6:0.6', '--seed', '0', '--placement-mode', 'legacy', '--place', 'bed',
            '--speeds', str(ROOT / 'docs/extended_dataset_intake.json'), '--jobs', '4',
            '--config', str(config_path), '--out', str(WORK / f'{side}.json')]
        env = dict(os.environ, RESENSE_REPO=str(ROOT), PYTHONPATH=str(ROOT),
            OPENBLAS_CORETYPE='Haswell', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
            MKL_NUM_THREADS='1', LD_LIBRARY_PATH='/tmp/opencode/resense-b4-libs/usr/lib/x86_64-linux-gnu')
        receipt = dict(side=side, commit=commit, command=command, source_sha256=before,
            config_sha256=sha(config_path), started=datetime.now(timezone.utc).isoformat())
        log = WORK / f'{side}.log'
        with log.open('x') as out:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=out, stderr=subprocess.STDOUT)
        receipt.update(returncode=result.returncode, finished=datetime.now(timezone.utc).isoformat(),
            source_unchanged=sources() == before, log_sha256=sha(log))
        if result.returncode == 0:
            receipt['raw_sha256'] = sha(WORK / f'{side}.json')
        with (HERE / f'{side}-execution.json').open('x') as out:
            json.dump(receipt, out, indent=2)
        print(side, result.returncode, receipt['source_unchanged'], flush=True)
        return result.returncode

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, ['off', 'on']))
    assert sources() == before
    assert all(sha(CACHE / p) == digest for p, digest in inputs.items())
    return int(any(results))


if __name__ == '__main__':
    sys.exit(main())
