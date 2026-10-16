"""Reinstall frozen source on retained tools dependencies; prove exact production fixture COPY.

Only OWNED packaging files are overlaid on git archive --source-ref. The existing offline
Dockerfile rebuilds the installed detector/native and ROS packages with no network. This is
focused fixture evidence, not final integrated runtime/tools or full-suite acceptance.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile
import textwrap
import time

ROOT = Path(__file__).resolve().parents[3]
OWNED = ('.dockerignore', 'docker/Dockerfile', 'tests/test_docker_fixtures.py',
         'docs/evidence/offline_rebuild_2026-10-15/context_check.py')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--source-ref', required=True)
    cli.add_argument('--base-image', default='resense:p1-combined-tools-7d3d5a05c258')
    cli.add_argument('--image', required=True, help='fresh fixture-test image tag')
    cli.add_argument('--out', type=Path, required=True)
    args = cli.parse_args()
    args.out = args.out.resolve()
    if args.out.exists():
        cli.error('evidence output already exists; choose a fresh --out')
    args.out.mkdir(parents=True)
    commands = []

    def run(name, command, cwd=ROOT):
        start = time.monotonic()
        result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding='utf-8', errors='replace', timeout=300)
        text = '\n'.join(line.rstrip() for line in result.stdout.splitlines()) + '\n'
        (args.out / f'{name}.log').write_text(text, encoding='utf-8')
        commands.append({'name': name, 'command': command, 'exit': result.returncode,
                         'seconds': round(time.monotonic() - start, 3)})
        print(f'{name}: exit {result.returncode}', flush=True)
        if result.returncode:
            print(text, flush=True)
        result.check_returncode()
        return result.stdout

    if subprocess.run(['docker', 'image', 'inspect', args.image], capture_output=True).returncode == 0:
        cli.error('fixture-test image already exists; choose a fresh --image')
    commit = subprocess.check_output(['git', 'rev-parse', f'{args.source_ref}^{{commit}}'],
                                     cwd=ROOT, text=True).strip()
    base = run('base', ['docker', 'image', 'inspect', '--format', '{{.Id}}', args.base_image]).strip()
    archive = subprocess.check_output(['git', 'archive', commit], cwd=ROOT)
    source_files = {}
    with tempfile.TemporaryDirectory(prefix='e2-context-', dir=args.out.resolve()) as tmp:
        context = Path(tmp)
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            source.extractall(context, filter='data')
        # The snapshot ignores concurrent edits to the shared node/launch sources. Record every
        # core/config/native/ROS input; the installed package is checked against these hashes.
        for name in ('resense', 'native', 'configs', 'ros2_ws/src'):
            for path in sorted((context / name).rglob('*')):
                if path.is_file():
                    source_files[path.relative_to(context).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        for name in ('pyproject.toml', 'setup.py', 'README.md'):
            source_files[name] = hashlib.sha256((context / name).read_bytes()).hexdigest()
        owned_hashes = {}
        for name in OWNED:
            content = (ROOT / name).read_bytes()
            target = context / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            owned_hashes[name] = hashlib.sha256(content).hexdigest()
        dockerfile = (context / 'docker/Dockerfile').read_text(encoding='utf-8')
        fixtures = dockerfile.split('# BEGIN pure test fixtures', 1)[1].split('# END pure test fixtures', 1)[0]
        copies = '\n'.join(line for line in fixtures.splitlines() if line.startswith('COPY '))
        fixture_files = [{'path': name, 'bytes': (context / name).stat().st_size,
                          'sha256': hashlib.sha256((context / name).read_bytes()).hexdigest()}
                         for line in copies.splitlines() for name in line.split()[1:-1]]
        manifest = {'source_commit': commit, 'source_files': source_files, 'fixtures': fixture_files}
        (context / 'fixture-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        # Real excluded directories, even when absent from git archive, exercise the ignore rules.
        for name in ('out', 'data', 'docs/evidence/judgement_2026-10-13/out'):
            sentinel = context / name / 'must-not-copy.txt'
            sentinel.parent.mkdir(parents=True, exist_ok=True)
            sentinel.write_text('excluded context sentinel\n', encoding='utf-8')
        # Reuse the production offline clean uninstall/recompile/colcon recipe. Retain only the
        # tools dependencies from the old image, never its detector or fixture/source trees.
        offline = (context / 'docker/Dockerfile.offline').read_text(encoding='utf-8')
        rebuild = offline.split('COPY scripts/check_offline_image.py', 1)[0]
        proof = rebuild + f'''
RUN rm -rf scripts tests docs webapp labels /e2-context
COPY . /e2-context
COPY scripts ./scripts
COPY tests ./tests
{copies}
RUN find scripts -type f -name '*.sh' -exec sed -i 's/\\r$//' {{}} +
'''
        (args.out / 'Dockerfile.context-check').write_text(proof, encoding='utf-8')
        (args.out / 'fixture-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
        (context / 'docker/Dockerfile.context-check').write_text(proof, encoding='utf-8')
        run('build', ['docker', 'build', '--network', 'none', '--pull=false', '--no-cache', '--progress=plain',
                      '--build-arg', f'RELEASE_IMAGE={args.base_image}',
                      '-f', 'docker/Dockerfile.context-check', '-t', args.image, '.'], cwd=context)
        exclusion = textwrap.dedent('''
            import hashlib, json, runpy
            from pathlib import Path
            p, root = Path('/e2-context'), Path('/opt/resense')
            manifest = json.loads((p / 'fixture-manifest.json').read_text())
            fixtures = {f['path']: f['sha256'] for f in manifest['fixtures']}
            assert set(runpy.run_path(str(root / 'tests/test_docker_fixtures.py'))['FIXTURES']) == set(fixtures)
            for relative, expected in fixtures.items():
                for parent in (p, root):
                    assert hashlib.sha256((parent / relative).read_bytes()).hexdigest() == expected, relative
            for prefix in ('docs', 'webapp', 'labels'):
                actual = {f.relative_to(p).as_posix() for f in (p / prefix).rglob('*') if f.is_file()}
                assert actual == {n for n in fixtures if n.startswith(prefix + '/')}, (prefix, actual)
            for name in ('.git', 'out', 'data', 'archive', 'archives', 'web', 'gitbook', 'webapp/frontend',
                         'docs/evidence/judgement_2026-10-13/out',
                         'docs/evidence/node_startup_2026-10-15/out'):
                assert not (p / name).exists(), name
            print(json.dumps({'result': 'PASS', 'exact_context_and_copy_files': len(fixtures),
                              'fixture_bytes': sum(f['bytes'] for f in manifest['fixtures']),
                              'no_recorded_data_or_archives': True}))
        ''')
        run('exclusions', ['docker', 'run', '--rm', '--network', 'none', '-w', '/', args.image,
                           'python3', '-c', exclusion])
        installed = textwrap.dedent('''
            import hashlib, json
            from pathlib import Path
            import open3d, resense, resense.detector
            from resense import _native
            root = Path('/opt/resense')
            package = Path(resense.__file__).parent
            assert not package.is_relative_to(root), package
            assert Path.cwd() == Path('/')
            assert _native.AVAILABLE and _native.enabled(), _native.status()
            manifest = json.loads(Path('/e2-context/fixture-manifest.json').read_text())
            for relative, expected in manifest['source_files'].items():
                path = root / relative
                if relative == 'ros2_ws/src/resense_ros/config/detector.yaml':
                    expected = manifest['source_files']['configs/default.yaml']
                assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, relative
                if relative.startswith('resense/'):
                    installed = package / relative.removeprefix('resense/')
                    assert hashlib.sha256(installed.read_bytes()).hexdigest() == expected, str(installed)
            native = Path(_native.LIBRARY)
            print(json.dumps({'source_commit': manifest['source_commit'], 'import': resense.__file__,
                              'native': _native.status(), 'native_sha256': hashlib.sha256(native.read_bytes()).hexdigest(),
                              'open3d': open3d.__version__, 'verified_source_files': len(manifest['source_files'])}))
        ''')
        runtime = json.loads(run('installed-source', ['docker', 'run', '--rm', '--network', 'none',
                                                     '-w', '/', args.image, 'python3', '-c', installed]).splitlines()[-1])
        groups = {
            'robustness-units': ('test_robustness_battery.py',),
            'fixture-packaging-units': ('test_docker_fixtures.py', 'test_metrics.py',
                                        'test_decision_policy.py', 'test_startup_acceptance.py'),
            'native-synthetic-units': ('test_native.py', 'test_fastcloud.py', 'test_core.py'),
        }
        unit_counts = {}
        for name, files in groups.items():
            tests = [f'/opt/resense/tests/{f}' for f in files]
            # Import the installed package before making scripts.* available to this subset.
            pytest = ('import resense, sys, pytest; from resense import _native; '
                      'assert not resense.__file__.startswith("/opt/resense/"); assert _native.enabled(); '
                      'sys.path.insert(0, "/opt/resense"); '
                      f'sys.exit(pytest.main({["-q", "-rs", *tests]!r}))')
            output = run(name, ['docker', 'run', '--rm', '--network', 'none', '-w', '/',
                               '-e', 'RESENSE_REQUIRE_SYNTHETIC=1', '-e', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1',
                               args.image, 'python3', '-c', pytest])
            counts = {key: int(count) for count, key in re.findall(r'(\d+) (passed|skipped|deselected)', output)}
            assert counts.get('passed', 0) > 0 and counts.get('skipped', 0) == 0, counts
            unit_counts[name] = dict(passed=counts['passed'], skipped=counts.get('skipped', 0),
                                     deselected=counts.get('deselected', 0))
    retained = run('base-after', ['docker', 'image', 'inspect', '--format', '{{.Id}}', args.base_image]).strip()
    assert retained == base
    image = run('image', ['docker', 'image', 'inspect', '--format', '{{.Id}}', args.image]).strip()
    report = {'result': 'PASS', 'source_commit': commit, 'owned_overlay_sha256': owned_hashes,
              'git_archive_sha256': hashlib.sha256(archive).hexdigest(),
              'base_image': args.base_image, 'base_id': base, 'image': args.image, 'image_id': image,
              'fixture_files': fixture_files, 'fixture_bytes': sum(p['bytes'] for p in fixture_files),
              'linux_unit_counts': unit_counts, 'installed_source': runtime,
              'commands': commands, 'scope': 'frozen source rebuilt on retained tools dependencies; focused units only'}
    (args.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
