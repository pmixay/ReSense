"""Build the production fixture COPY block on a loaded image and run focused Linux units.

Freeze application/tests at --source-ref; overlay only the named E2 packaging changes. This
checks Docker's actual ignore rules/COPY behavior without apt, PyPI or mutable node sources.
The resulting image is a fixture-test image, not a final combined runtime/tools acceptance.
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
import time

ROOT = Path(__file__).resolve().parents[3]
OWNED = ('.dockerignore', 'docker/Dockerfile', 'tests/test_docker_fixtures.py',
         'docs/evidence/offline_rebuild_2026-10-15/verify.py')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--source-ref', required=True)
    cli.add_argument('--base-image', default='resense:p1-e2-check')
    cli.add_argument('--image', required=True, help='fresh fixture-test image tag')
    cli.add_argument('--out', type=Path, required=True)
    args = cli.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    commands = []

    def run(name, command, cwd=ROOT):
        start = time.monotonic()
        result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding='utf-8', errors='replace', timeout=300)
        text = '\n'.join(line.rstrip() for line in result.stdout.splitlines()) + '\n'
        (args.out / f'{name}.log').write_text(text, encoding='utf-8')
        commands.append({'command': command, 'exit': result.returncode,
                         'seconds': round(time.monotonic() - start, 3)})
        print(f'{name}: exit {result.returncode}', flush=True)
        if result.returncode:
            print(text, flush=True)
        result.check_returncode()
        return result.stdout

    if subprocess.run(['docker', 'image', 'inspect', args.image], capture_output=True).returncode == 0:
        cli.error('fixture-test image already exists; choose a fresh --image')
    commit = subprocess.check_output(['git', 'rev-parse', args.source_ref], cwd=ROOT, text=True).strip()
    base = json.loads(run('base', ['docker', 'image', 'inspect', args.base_image]))[0]['Id']
    archive = subprocess.check_output(['git', 'archive', commit], cwd=ROOT)
    with tempfile.TemporaryDirectory(prefix='e2-context-', dir=args.out.resolve()) as tmp:
        context = Path(tmp)
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            source.extractall(context, filter='data')
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
        fixture_files = [{'path': name, 'bytes': (context / name).stat().st_size}
                         for line in copies.splitlines() for name in line.split()[1:-1]]
        # COPY . exposes Docker's filtered context for an explicit exclusion check. The image
        # also executes the production COPY block verbatim at its real destinations.
        proof = f'''ARG RELEASE_IMAGE=resense:p1-e2-check
FROM ${{RELEASE_IMAGE}}
WORKDIR /opt/resense
COPY . /e2-context
COPY scripts ./scripts
COPY tests ./tests
{copies}
RUN rm -rf ros2_ws
COPY ros2_ws/src ./ros2_ws/src
COPY configs/default.yaml ./ros2_ws/src/resense_ros/config/detector.yaml
RUN . /opt/ros/humble/setup.sh && cd ros2_ws && colcon build --symlink-install
RUN find scripts -type f -name '*.sh' -exec sed -i 's/\\r$//' {{}} +
'''
        (context / 'docker/Dockerfile.context-check').write_text(proof, encoding='utf-8')
        run('build', ['docker', 'build', '--network', 'none', '--pull=false', '--no-cache', '--progress=plain',
                      '--build-arg', f'RELEASE_IMAGE={args.base_image}',
                      '-f', 'docker/Dockerfile.context-check', '-t', args.image, '.'], cwd=context)
        # These sentinels already exist in the frozen source tree and must stay excluded.
        exclusion = (
            'from pathlib import Path; p=Path("/e2-context"); '
            'assert sorted(x.name for x in (p/"webapp/backend/resense_web").iterdir()) '
            '== ["__init__.py", "decision.py"]; '
            'assert not (p/"webapp/frontend").exists(); '
            'assert not (p/"docs/evidence/judgement_2026-10-13/out").exists(); '
            'assert not (p/"docs/evidence/node_startup_2026-10-15/out").exists(); '
            'print("PASS: exact pure backend files; frontend and recorded evidence excluded")'
        )
        run('exclusions', ['docker', 'run', '--rm', '--network', 'none', '-w', '/', args.image,
                           'python3', '-c', exclusion])
        tests = [f'/opt/resense/tests/{name}' for name in (
            'test_docker_fixtures.py', 'test_decision_policy.py', 'test_node.py', 'test_startup_acceptance.py')]
        # The normal full suite adds scripts' source root while collecting its other modules.
        # Do that explicitly for this subset, after importing the installed detector first.
        pytest = ('import resense, sys, pytest; assert not resense.__file__.startswith("/opt/resense/"); '
                  f'sys.path.insert(0, "/opt/resense"); sys.exit(pytest.main({["-q", "-rs", *tests]!r}))')
        output = run('linux-units', ['docker', 'run', '--rm', '--network', 'none', '-w', '/',
                                     '-e', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1', args.image, 'python3', '-c', pytest])
        unit_counts = {name: int(count) for count, name in re.findall(r'(\d+) (passed|skipped|deselected)', output)}
        packaging_tests = [path for path in tests if not path.endswith('/test_node.py')]
        pytest = ('import resense, sys, pytest; sys.path.insert(0, "/opt/resense"); '
                  f'sys.exit(pytest.main({["-q", "-rs", *packaging_tests]!r}))')
        run('packaging-units', ['docker', 'run', '--rm', '--network', 'none', '-w', '/',
                                '-e', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1', args.image, 'python3', '-c', pytest])
    retained = json.loads(run('base-after', ['docker', 'image', 'inspect', args.base_image]))[0]['Id']
    assert retained == base
    image = json.loads(run('image', ['docker', 'image', 'inspect', args.image]))[0]['Id']
    report = {'result': 'PASS', 'source_commit': commit, 'owned_overlay_sha256': owned_hashes,
              'base_image': args.base_image, 'base_id': base, 'image': args.image, 'image_id': image,
              'fixture_files': fixture_files, 'fixture_bytes': sum(p['bytes'] for p in fixture_files),
              'linux_unit_counts': unit_counts,
              'commands': commands, 'scope': 'frozen source plus E2 packaging; not final integrated suite'}
    (args.out / 'result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
