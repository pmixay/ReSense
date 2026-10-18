"""Detached Set F baseline queue: do not start before verified full ride intake."""
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
OUT = ROOT / 'docs/evidence/n3_dust_2026-10-18/set_f_baseline'
RECEIPT = DATA / 'gate_cache/ride_receipt.json'
STATUS = DATA / 'dust/set_f_queue_status.json'
PYTHON = '/home/resense/.venv/bin/python'
lock = (DATA / 'dust/set_f_queue.lock').open('w')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
os.nice(5)

def status(state, **extra):
    payload = {'state': state, 'pid': os.getpid(), 'utc_epoch': time.time(), **extra}
    temp = STATUS.with_suffix('.tmp')
    temp.write_text(json.dumps(payload, indent=2) + '\n')
    temp.replace(STATUS)
    print(json.dumps(payload), flush=True)

status('waiting_for_verified_full_ride_receipt')
while not RECEIPT.exists():
    time.sleep(30)
receipt = json.loads(RECEIPT.read_text())
assert receipt['verified'] is True and receipt['mode'] == 'ride'
assert receipt['sha256'] == '8124b627a8a70516a4023db522849f1cadae711e7b152b0f701535a69dab99ec'
assert receipt['bytes'] == 17078961996
assert receipt['total_frames'] == 221 * 51
assert receipt['frame_counts'] == {f'new_data_{i}': 51 for i in range(221)}
assert receipt['validation']['splits'] == 221 and receipt['validation']['frames'] == 221 * 51
sys.path.insert(0, str(ROOT))
from scripts.cache_io import validate_extended_ride_cache  # noqa: E402
validation = validate_extended_ride_cache(str(DATA / 'gate_cache/new_data'), load_arrays=False)
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'verified_ride_receipt.json').write_text(json.dumps({'receipt': receipt, 'receipt_sha256': hashlib.sha256(RECEIPT.read_bytes()).hexdigest(), 'independent_cache_validation': validation}, indent=2) + '\n')
command = [PYTHON, str(ROOT / 'scripts/dust_set_f.py'), '--cache', str(DATA / 'gate_cache/new_data'),
           '--bank', str(DATA / 'dust/set_f_bank'), '--out', str(OUT),
           '--placement-root', str(DATA / 'n2/baseline_9b92df5'),
           '--detector-root', str(DATA / 'n2/baseline_9b92df5')]
env = {**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'OPENBLAS_CORETYPE': 'Haswell'}
status('running_full_clean_low_medium_high_baseline', command=command)
result = subprocess.run(command, cwd=ROOT, env=env)
status('complete' if result.returncode == 0 else 'failed', returncode=result.returncode, output=str(OUT))
sys.exit(result.returncode)
