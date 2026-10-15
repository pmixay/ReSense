"""Reproduce the local E2 Docker evidence. Keeps this run's two plain tags and mutation tag.

Run from this worktree with Python. No Docker prune, tag replacement of release images, or
user-resource cleanup. The archive is temporary; logs and result.json stay next to this file.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
BASE = 'resense:p1-e2-check'
OFFLINE = 'resense:p1-e2-offline-check'
MUTATION = 'resense:p1-e2-mutation-check'
COMMANDS = []


def run(name: str, args: list[str], *, timeout: int = 900) -> str:
    start = time.monotonic()
    result = subprocess.run(args, cwd=ROOT, text=True, encoding='utf-8', errors='replace',
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    seconds = round(time.monotonic() - start, 3)
    (OUT / f'{name}.log').write_text(result.stdout, encoding='utf-8')
    COMMANDS.append({'name': name, 'command': args, 'seconds': seconds, 'exit': result.returncode})
    print(f'{name}: exit {result.returncode}, {seconds}s', flush=True)
    if result.returncode:
        print(result.stdout, flush=True)
    result.check_returncode()
    return result.stdout


def inspect(image: str) -> dict:
    return json.loads(subprocess.check_output(['docker', 'image', 'inspect', image], text=True))[0]


def main() -> None:
    run('docker-version', ['docker', 'version'])
    run('runtime-build', ['docker', 'build', '--progress=plain', '-t', BASE, '-f', 'docker/Dockerfile', '.'])
    before = inspect(BASE)
    with tempfile.TemporaryDirectory(prefix='resense-e2-archive-', dir=OUT.parents[3]) as tmp:
        archive = str(Path(tmp) / 'runtime.tar')
        run('archive-save', ['docker', 'save', '-o', archive, BASE])
        run('archive-load', ['docker', 'load', '-i', archive])
    loaded = inspect(BASE)
    assert before['Id'] == loaded['Id'] and before['RootFS'] == loaded['RootFS']
    cache_probe = (
        'import json, os, sys; from pathlib import Path; import resense; '
        'root=Path("/opt/resense"); '
        'files=list((root/"build").rglob("*.so"))+list((root/"build").rglob("*.o")); '
        'print(json.dumps({"package":resense.__file__, "PYTHONPATH":os.getenv("PYTHONPATH"), '
        '"sys_path":sys.path, "inherited_build_artifacts":'
        '[{"path":str(p), "mtime":p.stat().st_mtime} for p in files]}, indent=2))'
    )
    run('inherited-caches', ['docker', 'run', '--rm', '--network', 'none', '-w', '/', BASE,
                             'python3', '-c', cache_probe])
    run('offline-build', ['docker', 'build', '--network', 'none', '--pull=false', '--no-cache',
                          '--progress=plain', '--build-arg', f'RELEASE_IMAGE={BASE}',
                          '-f', 'docker/Dockerfile.offline', '-t', OFFLINE, '.'])
    for name, image in (('runtime', BASE), ('offline', OFFLINE)):
        run(f'{name}-installed', ['docker', 'run', '--rm', '--network', 'none', '-w', '/', image,
                                 'python3', '/opt/resense/scripts/check_offline_image.py'])
        run(f'{name}-nonroot', ['docker', 'run', '--rm', '--network', 'none', '--user', '1000:1000',
                               '-w', '/', image, 'python3', '/opt/resense/scripts/check_nonroot_player.py'])
    rebuilt = inspect(OFFLINE)
    for key in ('Entrypoint', 'Cmd'):
        assert rebuilt['Config'][key] == loaded['Config'][key], key
    assert rebuilt['Config']['Env'] == loaded['Config']['Env']
    assert inspect(BASE)['Id'] == loaded['Id']
    run('mutation', [sys.executable, 'scripts/offline_rebuild_test.py',
                     '--base-image', BASE, '--image', MUTATION, '--out', str(OUT / 'mutation')])
    summary = {'result': 'PASS', 'base_commit': 'd0d17bb5dcc2b5b23f9ddd96744a8fd0424e0b5d',
               'images': {BASE: loaded['Id'], OFFLINE: rebuilt['Id'], MUTATION: inspect(MUTATION)['Id']},
               'archive_layers_unchanged': True, 'entrypoint_cmd_env_unchanged': True,
               'commands': COMMANDS}
    (OUT / 'result.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2), flush=True)


def supplemental() -> None:
    run('lint', ['ruff', 'check', 'scripts/check_offline_image.py', 'scripts/check_nonroot_player.py',
                 'scripts/offline_rebuild_test.py', str(OUT / 'verify.py')])
    import ast
    import yaml
    for name in ('scripts/check_offline_image.py', 'scripts/check_nonroot_player.py',
                 'scripts/offline_rebuild_test.py'):
        ast.parse((ROOT / name).read_text(encoding='utf-8'))
    workflow = yaml.safe_load((ROOT / '.github/workflows/release.yml').read_text(encoding='utf-8'))
    offline_step = next(step for step in workflow['jobs']['release']['steps'] if step.get('id') == 'offline')
    run('workflow-bash-syntax', ['docker', 'run', '--rm', '--network', 'none', BASE,
                                 'bash', '-n', '-c', offline_step['run']])
    for name, image in (('runtime', BASE), ('offline', OFFLINE)):
        run(f'{name}-nonroot-hostnet', ['docker', 'run', '--rm', '--net=host', '--user', '1000:1000',
                                       '-w', '/', image, 'python3', '/opt/resense/scripts/check_nonroot_player.py'])
    # pytest is installed only in these --rm containers, not in the runtime images. This
    # supplementary unit run uses the internet to install pytest; E2's builds/player runs above
    # independently prove the offline path with --network none.
    run('release-unit-linux', ['docker', 'run', '--rm', '-w', '/', BASE, 'bash', '-c',
                               'pip3 install pytest==8.4.2 && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 '
                               'python3 -m pytest -q -rs /opt/resense/tests/test_release.py'])
    run('native-unit-linux', ['docker', 'run', '--rm', '-w', '/', OFFLINE, 'bash', '-c',
                              'pip3 install pytest==8.4.2 && PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 '
                              'python3 -m pytest -q -rs /opt/resense/tests/test_native.py '
                              '-k "not track_stage_functions_identical and not detector_output_identical"'])
    (OUT / 'supplemental.json').write_text(json.dumps({'result': 'PASS', 'commands': COMMANDS}, indent=2)
                                         + '\n', encoding='utf-8')


if __name__ == '__main__':
    if '--supplemental' in sys.argv:
        supplemental()
    else:
        main()
