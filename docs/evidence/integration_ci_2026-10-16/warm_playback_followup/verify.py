"""P1 bounded warm-setup validation only; no detector/node execution or playback."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

VOLUME = 'rs-s1-original-bags-20261016-72a601b'
IMAGE = 'resense:h4-fixture-fixed-1cfe8de-20261016'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def linux_units():
    import os

    root = Path('/work')
    subprocess.run(['python3', 'tests/test_warm_cache.py', '-v'], cwd=root, check=True)
    cache = load(root / 'scripts/check_warm_cache.py', 'mapped_cache')
    # Controlled red/green: evict ONLY a disposable owned small fixture, fault it
    # via the new read-only mapping, close it, and demand all pages remain resident.
    with tempfile.TemporaryDirectory(prefix='mapped-warm-contract-') as tmp:
        path = Path(tmp) / 'fixture.db3'
        content = bytes(range(256)) * (16 * 1024)
        path.write_bytes(content)
        with path.open('rb') as file:
            os.fsync(file.fileno())
            os.posix_fadvise(file.fileno(), 0, 0, os.POSIX_FADV_DONTNEED)
            before = cache.resident_pages(file)
        if before['missing'] == 0:
            raise RuntimeError('controlled cold witness not established; cannot claim faulting proof')
        row = {'name': path.name, 'identity': cache.identity(path.stat())}
        setup = {'sweeps': [], 'mappings_released_before_final_check': False}
        cache.mapped_setup([path], [row], time.monotonic() + 60, setup)
        with path.open('rb') as file:
            after = cache.resident_pages(file)
        assert after['fully_resident'] and setup['mappings_released_before_final_check']
        assert digest(path) == hashlib.sha256(content).hexdigest()
        print(json.dumps({'controlled_faulting': 'PASS', 'before': before, 'after': after, 'setup': setup}))
    # Execute the real warm guard with tiny fixtures and a stub player: fail closed.
    previous = load(root / 'docs/evidence/integration_ci_2026-10-16/warm_playback/preflight.py', 'prior_shell_contract')
    print(json.dumps({'shell_gate': previous.shell_checks(root)}))


def linux_bag():
    cache = load(Path('/work/scripts/check_warm_cache.py'), 'mapped_cache')
    bag = Path('/data/doubleT_obstacle')
    db = bag / 'doubleT_obstacle_0.db3'
    out = Path('/out')
    expected = '05f1d7f7d1bbbc5e9453877416cc9f7367c19e31d35a5291271d863fc89c5ad9'
    # This read-only identity check necessarily affects initial cache state. Both
    # its duration and the method's subsequent before-state are retained.
    start = time.monotonic()
    actual = digest(db)
    assert actual == expected
    (out / 'input.json').write_text(json.dumps({'bag_sha256': actual, 'bytes': db.stat().st_size,
        'hash_read_wall_s': time.monotonic() - start, 'scope': 'original read-only bag; no playback'}, indent=2) + '\n')
    report = cache.inspect_bag(bag)
    (out / 'setup.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'setup_status': report['status'], 'errors': report['errors'],
                      'before': report['files'][0].get('before'), 'after': report['files'][0].get('after'),
                      'wall_s': report['wall_s']}), flush=True)
    # Observe once after the player's existing 3-second delay, without repairing,
    # pinning, reading file data, or running playback even if setup is green.
    time.sleep(3)
    boundary = cache.inspect_bag(bag, observe_only=True)
    (out / 'boundary-after-3s.json').write_text(json.dumps(boundary, indent=2) + '\n')
    boundary_good = not boundary['errors'] and all(r['after']['fully_resident'] for r in boundary['files'])
    passed = report['status'] == 'WARM_VERIFIED' and boundary_good
    result = {'result': 'PASS' if passed else 'BLOCKED', 'setup_status': report['status'],
              'all_pages_resident_after_3s': boundary_good, 'setup_attempts': 1, 'playback_attempts': 0,
              'scope': 'one local warm-setup case; not Actions or runtime acceptance'}
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)
    return 0 if passed else 1


def main():
    if sys.argv[1:] == ['--linux-units']:
        linux_units()
        return 0
    if sys.argv[1:] == ['--linux-bag']:
        return linux_bag()
    root = Path(__file__).resolve().parents[4]
    here = Path(__file__).resolve().parent
    out = here / 'results'
    out.mkdir(exist_ok=False)
    failed = subprocess.check_output(['gh', 'run', 'view', '38928306547', '--job', '117065713597', '--log-failed'], cwd=root)
    (out / 'original-ci-failure.txt').write_bytes(failed)
    receipt = next(json.loads(m[1]) for line in failed.decode('utf-8-sig').splitlines()
                   if (m := re.search(r'(\{"schema": "resense-warm-cache-v1".*)$', line)))
    (out / 'original-ci-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8', newline='\n')
    provenance = {'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
                  'helper_sha256': digest(root / 'scripts/check_warm_cache.py'),
                  'tests_sha256': digest(root / 'tests/test_warm_cache.py'), 'image': IMAGE, 'volume': VOLUME,
                  'method_budget_s': 60, 'max_mapped_sweeps': 2, 'commands': []}
    for name, command in (
        ('image.json', ['docker', 'image', 'inspect', IMAGE]),
        ('volume.json', ['docker', 'volume', 'inspect', VOLUME]),
    ):
        (out / name).write_bytes(subprocess.check_output(command))
    base = ['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'python3',
            '-e', 'PYTHONDONTWRITEBYTECODE=1', '-v', f'{root}:/work:ro', '-w', '/work']
    driver = '/work/docs/evidence/integration_ci_2026-10-16/warm_playback_followup/verify.py'
    units = base + [IMAGE, driver, '--linux-units']
    result = subprocess.run(units, capture_output=True, text=True, timeout=120)
    (out / 'linux-contracts.txt').write_text(result.stdout + result.stderr, encoding='utf-8', newline='\n')
    provenance['commands'].append({'command': units, 'exit': result.returncode})
    result.check_returncode()
    bag_out = out / 'bag-once'
    bag_out.mkdir()
    command = base + ['--mount', f'type=volume,src={VOLUME},dst=/data,readonly,volume-nocopy',
                      '-v', f'{bag_out.resolve()}:/out', IMAGE, driver, '--linux-bag']
    result = subprocess.run(command, capture_output=True, text=True, timeout=240)
    (bag_out / 'console.txt').write_text(result.stdout + result.stderr, encoding='utf-8', newline='\n')
    provenance['commands'].append({'command': command, 'exit': result.returncode})
    (out / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(result.stdout + result.stderr)
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
