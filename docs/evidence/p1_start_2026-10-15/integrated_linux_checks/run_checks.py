"""Build an immutable combined HEAD tools image and run all tests, retaining every attempt.

No test selection, Docker pruning or unrelated cleanup. A labeled guard container remains up
from build start through suite cleanup so the separate S1 timing agent can wait for completion.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--source-ref', default='HEAD')
    cli.add_argument('--attempt', required=True)
    cli.add_argument('--image', help='default: resense:p1-combined-tools-<commit12>')
    cli.add_argument('--scratch-parent', type=Path, default=Path(tempfile.gettempdir()) / 'opencode')
    args = cli.parse_args()
    out = HERE / args.attempt
    if out.exists():
        cli.error('attempt already exists; use a new name to retain the original failure')
    if not args.scratch_parent.is_dir():
        cli.error('scratch parent must already exist')
    out.mkdir()
    started = time.monotonic()
    deadline = started + 900
    commands = []
    report = {'result': 'NOT RUN', 'attempt': args.attempt, 'commands': commands}

    def save():
        report['total_seconds'] = round(time.monotonic() - started, 3)
        (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    def run(name, command, *, cwd=ROOT, check=True, timeout=None):
        print(f'{name}: started', flush=True)
        start = time.monotonic()
        limit = timeout or max(1, deadline - start)
        try:
            result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, encoding='utf-8', errors='replace', timeout=limit)
        except subprocess.TimeoutExpired as exc:
            output = exc.stdout or b''
            if isinstance(output, bytes):
                output = output.decode('utf-8', errors='replace')
            (out / f'{name}.log').write_text(output, encoding='utf-8')
            commands.append({'name': name, 'command': command, 'timeout': True,
                             'seconds': round(time.monotonic() - start, 3)})
            raise
        text = '\n'.join(line.rstrip() for line in result.stdout.splitlines()) + '\n'
        (out / f'{name}.log').write_text(text, encoding='utf-8')
        commands.append({'name': name, 'command': command, 'exit': result.returncode,
                         'seconds': round(time.monotonic() - start, 3)})
        print(f'{name}: exit {result.returncode}, {commands[-1]["seconds"]}s', flush=True)
        save()
        if check:
            result.check_returncode()
        return result

    commit = subprocess.check_output(['git', 'rev-parse', args.source_ref], cwd=ROOT, text=True).strip()
    tree = subprocess.check_output(['git', 'rev-parse', commit + '^{tree}'], cwd=ROOT, text=True).strip()
    image = args.image or f'resense:p1-combined-tools-{commit[:12]}'
    suffix = commit[:12] + '-' + uuid.uuid4().hex[:8]
    guard = 'resense-p1-final-suite-guard-' + suffix
    suite = 'resense-p1-final-suite-' + suffix
    guard_created = False
    suite_started = False
    report.update({'source_commit': commit, 'source_tree': tree, 'image': image,
                   'guard_container': guard, 'suite_container': suite,
                   'runner_sha256': {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest()
                                     for name in ('run_checks.py', 'suite.py')}})
    save()
    try:
        if subprocess.run(['docker', 'image', 'inspect', image], capture_output=True).returncode == 0:
            raise RuntimeError(f'image already exists: {image}; choose a fresh tag')
        run('docker-version', ['docker', 'version'], timeout=30)
        run('guard-start', ['docker', 'run', '-d', '--rm', '--network', 'none', '--name', guard,
                            '--label', 'resense.p1.checks=final', '--entrypoint', '/bin/sleep',
                            'resense:p1-e2-check', '1800'], timeout=30)
        guard_created = True
        archive = subprocess.check_output(['git', 'archive', '--format=tar', commit], cwd=ROOT)
        report['source_archive_sha256'] = hashlib.sha256(archive).hexdigest()
        with tempfile.TemporaryDirectory(prefix='resense-final-suite-', dir=args.scratch_parent) as tmp:
            context = Path(tmp)
            with tarfile.open(fileobj=io.BytesIO(archive)) as source:
                source.extractall(context, filter='data')
            run('build', ['docker', 'build', '--progress=plain', '--build-arg', 'WITH_TOOLS=1',
                          '--label', f'org.opencontainers.image.revision={commit}',
                          '--label', 'resense.p1.checks=final', '-f', 'docker/Dockerfile',
                          '-t', image, '.'], cwd=context)
        metadata = json.loads(run('image', ['docker', 'image', 'inspect', image], timeout=30).stdout)[0]
        assert metadata['Config']['Labels']['org.opencontainers.image.revision'] == commit
        report['image_id'] = metadata['Id']
        report['image_config'] = {key: metadata['Config'][key] for key in ('Labels', 'Entrypoint', 'Cmd')}
        report['image_layers'] = metadata['RootFS']['Layers']
        save()
        suite_started = True
        result = run('suite', ['docker', 'run', '--rm', '--network', 'none', '--name', suite,
                               '--label', 'resense.p1.checks=final', '-w', '/',
                               '-e', 'RESENSE_REQUIRE_SYNTHETIC=1', '-e', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1',
                               '--mount', f'type=bind,source={HERE},target=/checks', image,
                               'python3', '/checks/suite.py', '--out', '/checks/' + args.attempt], check=False)
        if (out / 'junit.xml').exists():
            xml = ET.parse(out / 'junit.xml').getroot()
            suites = [xml] if xml.tag == 'testsuite' else list(xml)
            counts = {name: sum(int(s.get(name, 0)) for s in suites)
                      for name in ('tests', 'failures', 'errors', 'skipped')}
            report['junit'] = counts
            receipt = json.loads((out / 'suite_receipt.json').read_text(encoding='utf-8'))
            report['deselected'] = receipt['deselected']
            report['pytest_seconds'] = receipt['pytest_seconds']
            report['passed'] = counts['tests'] - counts['failures'] - counts['errors'] - counts['skipped']
            report['result'] = ('PASS' if result.returncode == 0 and counts['tests'] > 0
                                and not any(counts[key] for key in ('failures', 'errors', 'skipped'))
                                and receipt['only_missing_realdata_deselected'] else 'FAIL')
        else:
            report['result'] = 'BLOCKED'
            report['blocker'] = 'suite exited without a JUnit result; see suite.log'
    except Exception as exc:
        report['result'] = 'BLOCKED'
        report['blocker'] = f'{type(exc).__name__}: {exc}'
        print(report['blocker'], flush=True)
    finally:
        # Unique names created by this invocation only. Never remove other final-check containers.
        if suite_started:
            run('suite-cleanup', ['docker', 'rm', '-f', suite], check=False, timeout=30)
        if guard_created:
            run('guard-cleanup', ['docker', 'rm', '-f', guard], check=False, timeout=30)
        save()
    print(json.dumps(report, indent=2), flush=True)
    raise SystemExit(0 if report['result'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
