"""One detached corrected Set F preparation/evaluation, with verified full ride input."""
from pathlib import Path
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT = Path('/home/resense/ReSense')
DATA = Path('/home/resense/data')
HARNESS = DATA / 'dust/harness_b9ad5f4'
SOURCE = DATA / 'n2/baseline_9b92df5'
OUT = ROOT / 'docs/evidence/n3_dust_2026-10-18/set_f_baseline_pose_fixed'
BANK = DATA / 'dust/set_f_bank_pose_fixed'
RECEIPT = DATA / 'gate_cache/ride_receipt.json'
STATUS = DATA / 'dust/set_f_corrected_status.json'
lock = (DATA / 'dust/set_f_corrected.lock').open('w')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
os.nice(5)


def status(state, **extra):
    record = {'state': state, 'pid': os.getpid(), 'pgid': os.getpgrp(),
              'utc_epoch': time.time(), 'harness_commit': 'b9ad5f4',
              'detector_source': '9b92df5', **extra}
    temporary = STATUS.with_suffix('.tmp')
    temporary.write_text(json.dumps(record, indent=2) + '\n')
    temporary.replace(STATUS)
    print(json.dumps(record), flush=True)


receipt = json.loads(RECEIPT.read_text())
if (receipt['verified'] is not True or receipt['mode'] != 'ride'
        or receipt['sha256'] != '8124b627a8a70516a4023db522849f1cadae711e7b152b0f701535a69dab99ec'
        or receipt['bytes'] != 17078961996 or receipt['total_frames'] != 11271
        or receipt['frame_counts'] != {f'new_data_{i}': 51 for i in range(221)}):
    raise ValueError('complete verified canonical ride input required')
sys.path.insert(0, str(HARNESS))
from scripts.cache_io import validate_extended_ride_cache  # noqa: E402
validation = validate_extended_ride_cache(str(DATA / 'gate_cache/new_data'), load_arrays=False)
OUT.mkdir(parents=True, exist_ok=True)
if any(OUT.iterdir()) or BANK.exists():
    raise ValueError('fresh corrected bank/output required; preserve earlier captures')
(OUT / 'verified_ride_receipt.json').write_text(json.dumps({
    'receipt': receipt, 'receipt_sha256': hashlib.sha256(RECEIPT.read_bytes()).hexdigest(),
    'independent_cache_validation': validation}, indent=2) + '\n')
command = [sys.executable, str(HARNESS / 'scripts/dust_set_f.py'),
           '--cache', str(DATA / 'gate_cache/new_data'), '--bank', str(BANK), '--out', str(OUT),
           '--placement-root', str(SOURCE), '--detector-root', str(SOURCE)]
env = {**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
       'MKL_NUM_THREADS': '1', 'OPENBLAS_CORETYPE': 'Haswell'}
status('running', command=command, output=str(OUT), bank=str(BANK))
result = subprocess.run(command, cwd=HARNESS, env=env)
status('complete' if result.returncode == 0 else 'failed', returncode=result.returncode,
       output=str(OUT), bank=str(BANK))
sys.exit(result.returncode)
