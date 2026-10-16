"""One baseline and one instrumented playback of existing read-only Linux-volume bags.

No image build, bag copy, cache eviction, affinity pinning or pass-selected rerun.
Core/node source is frozen at the failed CI commit; only harness files are overlaid.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

COMMIT = 'b0c9c17cde65a59ddf93fb2799bc94a8a6a31bd1'
VOLUME = 'rs-s1-original-bags-20261016-72a601b'
IMAGE = 'resense:h4-fixture-fixed-1cfe8de-20261016'


def container(mode):
    """Runs only inside the disposable diagnostic container."""
    import os
    import shutil
    import time

    source, work, out = Path('/source'), Path('/tmp/repro'), Path('/out')
    work.mkdir()
    for path in source.iterdir():
        if path.is_dir():
            shutil.copytree(path, work / path.name)
        else:
            shutil.copy2(path, work / path.name)
    commands = []

    def run(name, argv, cwd=work):
        start = time.monotonic()
        result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
        (out / f'{name}.txt').write_text(result.stdout + result.stderr)
        commands.append({'name': name, 'argv': argv, 'exit': result.returncode,
                         'wall_s': time.monotonic() - start})
        return result

    run('uninstall', ['python3', '-m', 'pip', 'uninstall', '-y', 'resense'], cwd='/').check_returncode()
    os.environ['PIP_NO_INDEX'] = '1'
    run('install', ['python3', '-m', 'pip', 'install', '--no-deps', '--no-build-isolation', '.']).check_returncode()
    run('ros-build', ['bash', '-c', 'source /opt/ros/humble/setup.bash && '
                      'cd /tmp/repro/ros2_ws && colcon build --symlink-install']).check_returncode()
    run('installed', ['python3', '-c', '''
import hashlib, json
from pathlib import Path
import resense
from resense import _native
assert _native.enabled(), _native.status()
assert not resense.__file__.startswith(('/opt/resense/', '/tmp/repro/'))
root = Path('/tmp/repro/resense')
installed = Path(resense.__file__).parent
for path in root.rglob('*.py'):
    assert path.read_bytes() == (installed / path.relative_to(root)).read_bytes(), path
print(json.dumps({'version': resense.__version__, 'import': resense.__file__, 'native': _native.status(),
                  'native_sha256': hashlib.sha256(Path(_native.LIBRARY).read_bytes()).hexdigest()}))
'''], cwd='/').check_returncode()

    # Verify existing bag hashes read-only. This creates no copy and preserves the pinned inputs.
    pins = {'doubleT_obstacle/doubleT_obstacle_0.db3':
            '05f1d7f7d1bbbc5e9453877416cc9f7367c19e31d35a5291271d863fc89c5ad9',
            'roundT_doubleT/roundT_doubleT_0.db3':
            '6b5d3780bb8e373fae9c1a72080c34084f5a743efca5899526eb15c148a2b90d'}
    hashes = {}
    for name, expected in pins.items():
        path = Path('/data') / name
        digest = hashlib.sha256()
        with path.open('rb') as file:
            for block in iter(lambda: file.read(4 * 1024 * 1024), b''):
                digest.update(block)
        assert digest.hexdigest() == expected, name
        hashes[name] = {'bytes': path.stat().st_size, 'sha256': digest.hexdigest()}
    (out / 'bag-hashes.json').write_text(json.dumps(hashes, indent=2) + '\n')
    os.environ.update(BAG_NAME='doubleT_obstacle', RATE='1.0', BAG_READ_AHEAD_QUEUE_SIZE='10', WARM_CACHE='1')
    dry = (work / ('dry_run_original.sh' if mode == 'baseline' else 'scripts/dry_run.sh')).read_text()
    inner = dry.split("<<'INNER'\n", 1)[1].split('\nINNER', 1)[0]
    setup = ('source /opt/ros/humble/setup.bash\nsource /tmp/repro/ros2_ws/install/setup.bash\n'
             'source /opt/resense/dds_transport.sh\nresense_dds_transport\n')
    if mode == 'baseline':
        # Preserve the previous read-before-container-start policy as a read before node startup.
        # Record residency without reading pages both before that read and at the player boundary.
        setup += ('python3 scripts/check_warm_cache.py /data/doubleT_obstacle --observe-only '
                  '--out /out/cache_before_cat.json\n'
                  'for warm_db in /data/doubleT_obstacle/*.db3; do cat "$warm_db" > /dev/null; done\n')
        anchor = 'ros2 bag play "/data/$BAG_NAME"'
        inner = inner.replace(anchor, 'python3 scripts/check_warm_cache.py /data/doubleT_obstacle '
                              '--observe-only --out /out/cache_at_play.json\n' + anchor, 1)
    script = setup + inner
    (out / 'executed-inner.sh').write_text(script)
    result = run('playback', ['bash', '-c', script])
    check = run('acceptance', ['python3', 'scripts/check_dry_run.py', '/out/status.jsonl', '--require-freshness',
                '--expect-obstacle', '--distance', '50:62', '--min-frames', '201', '--max-p95-latency', '100',
                '--max-dropped', '0', '--min-playback-rate', '0.9', '--bag', '/data/doubleT_obstacle'])
    report = {'mode': mode, 'source_commit': COMMIT, 'playback_exit': result.returncode,
              'acceptance_exit': check.returncode, 'commands': commands,
              'scope': 'one local diagnostic, not CI reproduction or full acceptance'}
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return 0 if result.returncode == check.returncode == 0 else 1


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--container', choices=['baseline', 'guarded'])
    args = cli.parse_args()
    if args.container:
        return container(args.container)
    root = Path(__file__).resolve().parents[4]
    out = Path(__file__).resolve().parent / 'local-once'
    out.mkdir(exist_ok=False)
    # Explicitly inspect the volume first: Docker must never create a missing data volume.
    volume = subprocess.check_output(['docker', 'volume', 'inspect', VOLUME])
    (out / 'volume.json').write_bytes(volume)
    image = subprocess.check_output(['docker', 'image', 'inspect', IMAGE])
    (out / 'image.json').write_bytes(image)
    archive = subprocess.check_output(['git', '-c', 'core.autocrlf=false', 'archive', COMMIT, '--',
        'resense', 'native', 'configs', 'ros2_ws/src', 'pyproject.toml', 'setup.py', 'README.md', 'scripts'], cwd=root)
    scratch = Path('C:/Users/alikh/AppData/Local/Temp/opencode')
    with tempfile.TemporaryDirectory(dir=scratch, prefix='warm-ci-source-') as tmp:
        source = Path(tmp)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            tar.extractall(source, filter='data')
        original = (source / 'scripts/dry_run.sh').read_text()
        (source / 'dry_run_original.sh').write_text(original, encoding='utf-8', newline='\n')
        for name in ('scripts/check_warm_cache.py', 'scripts/dry_run.sh'):
            (source / name).write_text((root / name).read_text(), encoding='utf-8', newline='\n')
        results = []
        # Predeclared order and one attempt each. Keep both outcomes even if one is red.
        for mode in ('baseline', 'guarded'):
            folder = out / mode
            folder.mkdir()
            command = ['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'python3',
                '--mount', f'type=volume,src={VOLUME},dst=/data,readonly,volume-nocopy',
                '-v', f'{source}:/source:ro', '-v', f'{folder.resolve()}:/out',
                '-v', f'{Path(__file__).resolve()}:/driver.py:ro', IMAGE, '/driver.py', '--container', mode]
            result = subprocess.run(command, capture_output=True, text=True, timeout=600)
            (folder / 'driver.txt').write_text(result.stdout + result.stderr, encoding='utf-8')
            results.append({'mode': mode, 'command': command, 'exit': result.returncode})
            print(mode, 'exit', result.returncode, flush=True)
        (out / 'runs.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
