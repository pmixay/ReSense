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
import re
import subprocess
import sys
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
    cli.add_argument('--incremental-base', help='reuse a verified WITH_TOOLS=1 image; rebuild via Dockerfile.offline')
    cli.add_argument('--expected-base-id', help='required immutable image ID with --incremental-base')
    cli.add_argument('--scratch-parent', type=Path, default=Path(tempfile.gettempdir()) / 'opencode')
    args = cli.parse_args()
    if bool(args.incremental_base) != bool(args.expected_base_id):
        cli.error('--incremental-base and --expected-base-id must be supplied together')
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
        base = None
        if args.incremental_base:
            base = json.loads(run('base-image', ['docker', 'image', 'inspect', args.incremental_base], timeout=30).stdout)[0]
            assert base['Id'] == args.expected_base_id, 'incremental base ID differs'
            base_revision = base['Config']['Labels']['org.opencontainers.image.revision']
            dependency_inputs = ['pyproject.toml', 'setup.py', 'ros2_ws/src/resense_ros/setup.py',
                                 'ros2_ws/src/resense_ros/package.xml']
            run('dependency-inputs', ['git', 'diff', '--exit-code', base_revision, commit, '--', *dependency_inputs], timeout=30)
            report.update({'construction': 'incremental offline rebuild; not a fresh runtime Dockerfile build',
                           'base_image': args.incremental_base, 'base_id': base['Id'],
                           'base_source_revision': base_revision, 'unchanged_dependency_inputs': dependency_inputs})
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
            build_args = ['--build-arg', 'WITH_TOOLS=1', '-f', 'docker/Dockerfile']
            if base is not None:
                runtime = (context / 'docker/Dockerfile').read_text(encoding='utf-8')
                copies = [line for line in runtime.splitlines()
                          if line.startswith(('COPY docs/', 'COPY webapp/', 'COPY labels/'))]
                offline = (context / 'docker/Dockerfile.offline').read_text(encoding='utf-8')
                refresh = (
                    '\n# Latest suite/scripts and exact runtime fixtures; discard inherited files first.\n'
                    'RUN rm -rf /opt/resense/tests /opt/resense/scripts /opt/resense/webapp /opt/resense/docs /opt/resense/labels\n'
                    'COPY tests ./tests\nCOPY scripts ./scripts\n' + '\n'.join(copies) + '\n'
                    "RUN find scripts -type f -name '*.sh' -exec sed -i 's/\\r$//' {} +\n")
                generated = offline + refresh
                (out / 'Dockerfile.incremental').write_text(generated, encoding='utf-8')
                (context / 'docker/Dockerfile.incremental').write_text(generated, encoding='utf-8')
                paths = set()
                for name in ('resense', 'native', 'configs', 'ros2_ws/src', 'scripts', 'tests'):
                    paths.update(p.relative_to(context).as_posix() for p in (context / name).rglob('*') if p.is_file())
                paths.update(('pyproject.toml', 'setup.py', 'README.md'))
                for line in copies:
                    paths.update(line.split()[1:-1])
                hashes, transforms = {}, {}
                for name in sorted(paths):
                    raw = (context / name).read_bytes()
                    data = re.sub(rb'\r(?=\n|$)', b'', raw) if name.startswith('scripts/') and name.endswith('.sh') else raw
                    hashes[name] = hashlib.sha256(data).hexdigest()
                    if data != raw:
                        transforms[name] = {'operation': 'declared Dockerfile sed removes line-final CR',
                                            'source_sha256': hashlib.sha256(raw).hexdigest(),
                                            'image_sha256': hashes[name]}
                manifest = {'source_commit': commit, 'files': hashes, 'transforms': transforms}
                (out / 'source_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
                report['incremental_dockerfile_sha256'] = hashlib.sha256(generated.encode('utf-8')).hexdigest()
                report['source_manifest_files'] = len(paths)
                report['declared_shell_normalizations'] = len(transforms)
                changed = subprocess.check_output(['git', 'diff', '--name-only', base_revision, commit], cwd=ROOT, text=True)
                python_paths = [name for name in changed.splitlines() if name.endswith('.py') and (context / name).is_file()]
                lint = run('ruff-focused', ['ruff', 'check', *python_paths], cwd=context, check=False, timeout=30)
                report['ruff_focused_exit'] = lint.returncode
                report['static_checks_passed'] = lint.returncode == 0
                if lint.returncode:
                    report['remaining_concerns'] = ['Focused Ruff failed; preserve ruff-focused.log separately from the full-suite result']
                run('yaml-parse', [sys.executable, '-c',
                                  "from pathlib import Path; import yaml; paths=sorted(Path('.github/workflows').glob('*.yml')); "
                                  "[yaml.safe_load(p.read_text(encoding='utf-8')) for p in paths]; "
                                  "print('PASS: parsed', len(paths), 'workflow YAML files')"], cwd=context, timeout=30)
                build_args = ['--network', 'none', '--pull=false', '--no-cache', '--build-arg',
                              f'RELEASE_IMAGE={args.incremental_base}', '--label', f'resense.p1.base-image-id={base["Id"]}',
                              '-f', 'docker/Dockerfile.incremental']
            run('build', ['docker', 'build', '--progress=plain', *build_args,
                          '--label', f'org.opencontainers.image.revision={commit}',
                          '--label', 'resense.p1.checks=final', '-t', image, '.'], cwd=context)
        metadata = json.loads(run('image', ['docker', 'image', 'inspect', image], timeout=30).stdout)[0]
        assert metadata['Config']['Labels']['org.opencontainers.image.revision'] == commit
        report['image_id'] = metadata['Id']
        report['image_config'] = {key: metadata['Config'][key] for key in ('Labels', 'Entrypoint', 'Cmd')}
        report['image_layers'] = metadata['RootFS']['Layers']
        save()
        suite_started = True
        extra = ['--expected-source', '/checks/' + args.attempt + '/source_manifest.json'] if base is not None else []
        result = run('suite', ['docker', 'run', '--rm', '--network', 'none', '--name', suite,
                               '--label', 'resense.p1.checks=final', '-w', '/',
                               '-e', 'RESENSE_REQUIRE_SYNTHETIC=1', '-e', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1',
                               '--mount', f'type=bind,source={HERE},target=/checks', image,
                               'python3', '/checks/suite.py', '--out', '/checks/' + args.attempt, *extra], check=False)
        if base is not None:
            after = json.loads(run('base-image-after', ['docker', 'image', 'inspect', args.incremental_base], timeout=30).stdout)[0]
            assert after['Id'] == args.expected_base_id, 'incremental base tag changed'
        if (out / 'junit.xml').exists():
            xml = ET.parse(out / 'junit.xml').getroot()
            suites = [xml] if xml.tag == 'testsuite' else list(xml)
            counts = {name: sum(int(s.get(name, 0)) for s in suites)
                      for name in ('tests', 'failures', 'errors', 'skipped')}
            report['junit'] = counts
            receipt = json.loads((out / 'suite_receipt.json').read_text(encoding='utf-8'))
            report['deselected'] = receipt['deselected']
            report['pytest_seconds'] = receipt['pytest_seconds']
            report['passed_by_file'] = receipt['passed_by_file']
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
