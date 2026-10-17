"""Validate CI policy on clean committed bytes plus only the owned lint repair overlay."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
PREFIX = HERE.relative_to(ROOT).as_posix()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--ruff', required=True)
    cli.add_argument('--scratch', type=Path, required=True)
    cli.add_argument('--out', type=Path, required=True)
    cli.add_argument('--linux-image', help='also run pinned lint/contracts in this retained Linux image')
    args = cli.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    commands = []

    def run(name, command, cwd, expected=0):
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        (args.out / f'{name}.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
        commands.append({'name': name, 'command': list(map(str, command)), 'exit': result.returncode})
        if result.returncode != expected:
            raise RuntimeError(f'{name}: expected {expected}, got {result.returncode}: {result.stdout}{result.stderr}')
        print(name, 'PASS', flush=True)
        return result.stdout

    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    archive = subprocess.check_output(['git', '-c', 'core.autocrlf=false', 'archive', commit], cwd=ROOT)
    with tempfile.TemporaryDirectory(dir=args.scratch, prefix='ci-lint-clean-') as tmp:
        clean = Path(tmp)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(clean, filter='data')
        owned = ['.github/workflows/ci.yml', 'scripts/check_archived_lint.py', 'tests/test_archived_lint.py']
        owned += [p.relative_to(ROOT).as_posix() for p in HERE.iterdir() if p.is_file()]
        for name in owned:
            target = clean / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name).read_bytes())
        # Every historical locked byte in this clean checkout must still equal its original Git blob.
        lock = json.loads((HERE / 'snapshot_lock.json').read_text())
        for entry in lock['files']:
            path = entry['path']
            original = subprocess.check_output(['git', 'show', f'492e407:{path}'], cwd=ROOT)
            assert (clean / path).read_bytes() == original, path
        python = 'python'
        run('integrity', [python, 'scripts/check_archived_lint.py'], clean)
        run('contract-tests', [python, 'tests/test_archived_lint.py', '-v'], clean)
        lint = [python, 'scripts/check_archived_lint.py', '--lint', '--ruff', args.ruff]
        run('full-pinned-lint', lint, clean)
        if args.linux_image:
            code = '''
import subprocess
subprocess.run(['python3', '-m', 'pip', 'install', '--no-deps', '--target', '/tmp/lint-tools',
                'ruff==0.15.8'], check=True)
subprocess.run(['python3', 'scripts/check_archived_lint.py', '--lint',
                '--ruff', '/tmp/lint-tools/bin/ruff'], check=True)
subprocess.run(['python3', 'tests/test_archived_lint.py', '-v'], check=True)
'''
            run('linux-pinned-lint-and-contracts', ['docker', 'run', '--rm', '--entrypoint', 'python3',
                '-e', 'PYTHONDONTWRITEBYTECODE=1', '-v', f'{clean}:/work:ro', '-w', '/work',
                args.linux_image, '-c', code], clean)
        # Ruff's own resolved file list is the coverage inventory, including maintained docs helpers.
        exclusions = ','.join(str((clean / e['path']).resolve()) for e in lock['exclusions'])
        files = run('lint-files', [args.ruff, 'check', '--no-cache', '--show-files',
                                  '--extend-exclude', exclusions, '.'], clean).splitlines()
        files = [Path(p).relative_to(clean).as_posix() for p in files]
        assert not set(files) & {e['path'] for e in lock['exclusions']}
        assert 'scripts/check_archived_lint.py' in files and 'tests/test_archived_lint.py' in files
        (args.out / 'lint-coverage.json').write_text(json.dumps(files, indent=2) + '\n', encoding='utf-8')
        # A broken new maintained file outside the frozen package must still fail actual Ruff.
        new = clean / 'scripts/new_live_lint_probe.py'
        new.write_text('import definitely_unused\n', encoding='utf-8')
        run('negative-live-file', lint, clean, expected=1)
        new.unlink()
        # New Python next to frozen evidence fails even if its code would pass Ruff.
        new = clean / lock['python_roots'][0] / 'unlisted_probe.py'
        new.write_text('pass\n', encoding='utf-8')
        run('negative-unlisted-snapshot', lint, clean, expected=1)
        new.unlink()
        path = clean / lock['exclusions'][0]['path']
        original = path.read_bytes()
        path.write_bytes(original + b'\n# mutation\n')
        run('negative-mutated-snapshot', lint, clean, expected=1)
        path.write_bytes(original)
        path.unlink()
        run('negative-missing-snapshot', lint, clean, expected=1)
        path.write_bytes(original)
        # Exact file scope: identical basename in a different folder must not be exempt.
        new = clean / 'scripts' / path.name
        assert not new.exists()
        new.write_text('import definitely_unused\n', encoding='utf-8')
        run('negative-same-basename', lint, clean, expected=1)
        new.unlink()
        report = {'result': 'PASS', 'source_commit': commit, 'original_snapshot_commit': '492e407',
                  'ruff': subprocess.check_output([args.ruff, '--version'], text=True).strip(),
                  'immutable_files_unchanged': len(lock['files']), 'exact_exclusions': len(lock['exclusions']),
                  'maintained_files_linted': len(files), 'snapshot_lock_sha256': hashlib.sha256(
                      (HERE / 'snapshot_lock.json').read_bytes()).hexdigest(), 'commands': commands,
                  'scope': 'CI lint/integrity only; no archived helpers executed, no detector evaluation or reseal'}
        (args.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({k: v for k, v in report.items() if k != 'commands'}, indent=2))


if __name__ == '__main__':
    main()
