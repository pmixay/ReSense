#!/usr/bin/env python3
"""E2 integration regression: actually recompile changed source with no build/run network.

Requires a locally loaded runtime image. Mutates only a temporary COPY of build inputs; never
changes the checkout, package version, release tags or the base image. Keeps the new image for
inspection and writes command output plus a JSON result under --out.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
TOKEN = 20261015


def run(args: list[str], log: Path, *, cwd: Path = ROOT) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, encoding='utf-8', errors='replace',
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900)
    log.write_text(result.stdout, encoding='utf-8')
    print(result.stdout, end='', flush=True)
    result.check_returncode()
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-image', required=True, help='exact locally loaded release image tag')
    parser.add_argument('--image', required=True, help='new, disposable mutation-test image tag')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    base = run(['docker', 'image', 'inspect', args.base_image], args.out / 'base.json')
    identity = json.loads(base)[0]['Id']
    # Refuse to overwrite an existing image (especially the archive's tag or an unrelated image).
    exists = subprocess.run(['docker', 'image', 'inspect', args.image], capture_output=True).returncode == 0
    if exists:
        parser.error(f'test image already exists: {args.image}; choose a new tag')
    with tempfile.TemporaryDirectory(prefix='resense-e2-', dir=args.out.resolve()) as tmp:
        context = Path(tmp)
        ignore = shutil.ignore_patterns('__pycache__', '*.pyc', '*.so', '*.pyd', '*.egg-info',
                                       'build', 'install', 'log')
        for name in ('resense', 'native', 'configs', 'ros2_ws/src'):
            shutil.copytree(ROOT / name, context / name, ignore=ignore)
        for name in ('pyproject.toml', 'setup.py', 'README.md', 'docker/Dockerfile.offline',
                     'scripts/check_offline_image.py'):
            target = context / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        for name in ('resense/e2_rebuild_probe.py', 'ros2_ws/src/resense_ros/resense_ros/e2_rebuild_probe.py'):
            (context / name).write_text(f'TOKEN = {TOKEN}\n', encoding='utf-8')
        cpp = context / 'native/resense_native.cpp'
        with cpp.open('a', encoding='utf-8') as stream:
            stream.write(f'\nextern "C" int rs_e2_rebuild_probe() {{ return {TOKEN}; }}\n')
        # Deliberately older than the inherited build/*.o: incremental setuptools would skip it.
        os.utime(cpp, (1, 1))
        for name in ('configs/default.yaml', 'ros2_ws/src/resense_ros/launch/detector.launch.py'):
            with (context / name).open('a', encoding='utf-8') as stream:
                stream.write(f'\n# e2-rebuild-probe-{TOKEN}\n')
        start = time.monotonic()
        run(['docker', 'build', '--network', 'none', '--pull=false', '--no-cache', '--progress=plain',
             '--build-arg', f'RELEASE_IMAGE={args.base_image}', '-f', 'docker/Dockerfile.offline',
             '-t', args.image, '.'], args.out / 'build.log', cwd=context)
        elapsed = time.monotonic() - start
    run(['docker', 'run', '--rm', '--network', 'none', '-w', '/', args.image,
         'python3', '/opt/resense/scripts/check_offline_image.py'], args.out / 'installed.log')
    probe = (
        'from pathlib import Path; '
        'from resense import _native as n; '
        'import resense.e2_rebuild_probe as p; import resense_ros.e2_rebuild_probe as r; '
        'from ament_index_python.packages import get_package_share_directory as share; '
        f'assert p.TOKEN == r.TOKEN == n._lib.rs_e2_rebuild_probe() == {TOKEN}; '
        's = Path(share("resense_ros")); '
        f'assert "e2-rebuild-probe-{TOKEN}" in (s / "launch/detector.launch.py").read_text(); '
        f'assert "e2-rebuild-probe-{TOKEN}" in (s / "config/detector.yaml").read_text(); '
        'print("PASS: changed Python, native symbol, ROS module, launch and shared config")'
    )
    run(['docker', 'run', '--rm', '--network', 'none', '-w', '/', args.image,
         'python3', '-c', probe], args.out / 'probe.log')
    after = run(['docker', 'image', 'inspect', args.base_image], args.out / 'base_after.json')
    assert json.loads(after)[0]['Id'] == identity, 'loaded release image changed'
    summary = {'result': 'PASS', 'base_image': args.base_image, 'base_id': identity,
               'test_image': args.image, 'build_seconds': round(elapsed, 3),
               'network': 'none', 'pull': False, 'no_cache': True, 'probe_token': TOKEN}
    (args.out / 'result.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
