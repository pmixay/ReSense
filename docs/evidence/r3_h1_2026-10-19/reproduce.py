"""Reproduce with the unchanged judge and X1 observer; keep source and input receipts."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
DATA = Path('/tmp/opencode/resense-b4-data')
WORK = Path('/tmp/opencode/r3-h1')
A = 'roundT_squareT_pressureGate_squareT'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def call(args, log):
    with log.open('w') as f:
        p = subprocess.run([sys.executable, *map(str, args)], cwd=ROOT,
                           stdout=f, stderr=subprocess.STDOUT)
    if p.returncode:
        raise RuntimeError(f'{p.returncode}: {log}')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--tag', default='baseline')
    a = p.parse_args()
    assert np.__version__ == '1.26.4'
    assert os.environ['RESENSE_REPO'] == str(ROOT)
    out = WORK / a.tag
    out.mkdir(parents=True, exist_ok=False)
    cache = out / 'cache'
    cache.mkdir()
    (cache / A).symlink_to(DATA / 'decoded' / A, target_is_directory=True)
    archive = ROOT / 'docs/evidence/p4_eval_1.1.0_2026-10-16/raw/p4_raw_2026-10-16.tar.xz'
    with tarfile.open(archive) as t:
        for name in [f'x1/icp/icp_{A}.json', 'x1/1.1.0/E6_cable_low_c.off.json']:
            (out / Path(name).name).write_bytes(t.extractfile(name).read())
    identity = {'base': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                'numpy': np.__version__, 'environment': {k: os.environ.get(k) for k in
                ['RESENSE_REPO', 'PYTHONPATH', 'OPENBLAS_CORETYPE', 'OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS']},
                'sources': {str(f.relative_to(ROOT)): sha(f) for d in ['resense', 'native', 'configs']
                            for f in sorted((ROOT / d).rglob('*')) if f.is_file()
                            and '__pycache__' not in str(f) and f.suffix in ['.py', '.cpp', '.yaml', '.so']},
                'inputs': {str(DATA / 'decoded' / b / 'meta.json'): sha(DATA / 'decoded' / b / 'meta.json')
                           for b in [A, 'cloud_with_fake_obj']}}
    (out / 'identity.json').write_text(json.dumps(identity, indent=2))
    # Build object-free placement once; both observer modes consume these same bytes.
    call(['-c', f"import sys; sys.path.insert(0, '{ROOT}/docs/evidence/judgement_2026-10-13/scripts'); "
          f"import range_test; range_test.baseline('{cache/A}', '{cache}/{A}_baseline.json')"], out / 'placement.log')

    def one(case):
        if case == 'E6':
            tool = ['range', cache / A, out / f'icp_{A}.json', 'OUT', '--obj', '0.05,0.05,2.6',
                    '--start', '150', '--d0', '230', '--end', '340', '--base', '0.2']
            extra, index, ext = [], 3, '.json'
        else:
            tool = ['probe', DATA / 'decoded/cloud_with_fake_obj', 'OUT', '--end', '791']
            extra = ['--labels', ROOT / 'labels/cloud_with_fake_obj.json',
                     '--window', 'thin_hanging:760:790', '--window', 'small_center:300:340']
            index, ext = 2, '.jsonl'
        for mode in ['off', 'on']:
            args = tool.copy()
            args[index] = out / f'{case}.{mode}'
            hook = ['--hooks-off'] if mode == 'off' else extra + ['--keep-frames']
            call([ROOT / 'scripts/range_attrib.py', 'run', '--repo', ROOT, '--out', out / case,
                  *hook, *args], out / f'{case}.{mode}.log')
        call([ROOT / 'scripts/range_attrib.py', 'verify', out / case,
              out / f'{case}.on{ext}', out / f'{case}.off{ext}'], out / f'{case}.verify.log')

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(one, ['E6', 'setO']))
    print(out)


if __name__ == '__main__':
    main()
