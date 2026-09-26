"""Execute exactly one preregistered cold replay with bounded, read-only disk contention."""
import datetime
import hashlib
import json
import mmap
import multiprocessing
import os
from pathlib import Path
import subprocess
import time

ROOT = Path('/home/resense/ReSense')
VALID = Path('/home/resense/validation')
PROTOCOL = VALID / 'cold_load_final_protocol.json'


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def reader(path, destination, stop, ready):
    started = time.monotonic()
    record = {'file': path, 'started_utc': utc(), 'bytes': 0, 'reads': 0, 'passes': 0,
              'direct_io': True, 'error': None, 'samples': []}
    fd = None
    buffer = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_DIRECT)
        buffer = mmap.mmap(-1, 1 << 20)
        next_sample = 1.0
        while not stop.is_set() and time.monotonic() - started < 120:
            block_start = time.monotonic()
            count = os.readv(fd, [buffer])
            if not count:
                os.lseek(fd, 0, os.SEEK_SET)
                record['passes'] += 1
                continue
            record['bytes'] += count
            record['reads'] += 1
            ready.set()
            elapsed = time.monotonic() - started
            if elapsed >= next_sample:
                record['samples'].append({'elapsed_s': round(elapsed, 4), 'bytes': record['bytes']})
                next_sample = elapsed + 1.0
            # Limit each reader to at most 64 MiB/s, without accumulating catch-up credit.
            stop.wait(max(0.0, count / (64 << 20) - (time.monotonic() - block_start)))
    except Exception as error:
        record['error'] = repr(error)
    finally:
        record['elapsed_s'] = time.monotonic() - started
        record['finished_utc'] = utc()
        record['mib_per_s'] = record['bytes'] / (1 << 20) / record['elapsed_s']
        if buffer is not None:
            buffer.close()
        if fd is not None:
            os.close(fd)
        Path(destination).write_text(json.dumps(record, indent=2) + '\n')


def main():
    protocol = json.loads(PROTOCOL.read_text())
    marker = VALID / 'cold_load_final_started.json'
    with marker.open('x') as output:  # no retry or accidental replacement of this trial
        json.dump({'started_utc': utc(), 'protocol_sha256': hashlib.sha256(PROTOCOL.read_bytes()).hexdigest()}, output)
        output.write('\n')
    result = {'started_utc': utc(), 'protocol': str(PROTOCOL), 'dry_run_exit_code': None,
              'impractical_reason': None, 'load_covered_capture': False}
    stop = multiprocessing.Event()
    workers = []
    try:
        for index, path in enumerate(protocol['workload']['files']):
            ready = multiprocessing.Event()
            worker = multiprocessing.Process(target=reader,
                args=(path, str(VALID / f'cold_load_final_reader{index}.json'), stop, ready))
            worker.start()
            workers.append((worker, ready))
        if not all(ready.wait(10) for _, ready in workers):
            result['impractical_reason'] = 'A reader could not establish direct I/O; no replay attempted.'
            return
        time.sleep(3)
        with (VALID / 'cold_load_final_cache_before.json').open('w') as output:
            cold = subprocess.run(['python3', '/tmp/resense_cold_bag.py'], stdout=output,
                                  stderr=subprocess.STDOUT, timeout=10)
        if cold.returncode:
            result['impractical_reason'] = 'File-local cold-cache proof failed; no replay attempted.'
            return
        result['replay_started_utc'] = utc()
        env = os.environ.copy()
        env.update({'SKIP_BUILD': '1', 'OFFLINE': '1', 'OUT': str(VALID / 'dry_cold_load_final')})
        command = [str(ROOT / 'scripts/dry_run.sh'), protocol['bag'], '--expect-obstacle',
                   '--distance', '50:62', '--max-p95-latency', '100', '--max-dropped', '0']
        with (VALID / 'dry_cold_load_final.log').open('w') as output:
            try:
                replay = subprocess.run(command, cwd=ROOT, env=env, stdout=output,
                                        stderr=subprocess.STDOUT, timeout=110)
                result['dry_run_exit_code'] = replay.returncode
            except subprocess.TimeoutExpired:
                result['dry_run_exit_code'] = 'timeout'
        result['replay_finished_utc'] = utc()
        result['load_covered_capture'] = all(worker.is_alive() for worker, _ in workers)
    finally:
        stop.set()
        for worker, _ in workers:
            worker.join(10)
            if worker.is_alive():
                worker.terminate()
                worker.join()
        result['finished_utc'] = utc()
        for index in range(len(workers)):
            path = VALID / f'cold_load_final_reader{index}.json'
            record = json.loads(path.read_text()) if path.exists() else {'error': 'reader report missing'}
            result.setdefault('readers', []).append(record)
        result['trial_valid'] = (result['impractical_reason'] is None and result['load_covered_capture']
                                 and all(not r['error'] for r in result.get('readers', [])))
        (VALID / 'cold_load_final_result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({k: v for k, v in result.items() if k != 'readers'}, indent=2))


if __name__ == '__main__':
    main()
