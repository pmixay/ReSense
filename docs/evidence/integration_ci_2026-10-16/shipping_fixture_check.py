"""Collect the image suite and execute changed shipping/fixture regressions on frozen installed source."""
import argparse
import json
from pathlib import Path
import re
import subprocess


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--image', default='resense:h4-fixture-fixed-1cfe8de-20261016')
    cli.add_argument('--out', type=Path, default=Path(__file__).resolve().parent / 'h4-fixture-fixed')
    args = cli.parse_args()
    assert args.out.is_dir()
    commands = []

    def run(name, code):
        log = args.out / f'{name}.log'
        assert not log.exists(), log
        command = ['docker', 'run', '--rm', '--network', 'none', '-w', '/',
                   '-e', 'RESENSE_REQUIRE_SYNTHETIC=1', '-e', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1',
                   args.image, 'python3', '-c', code]
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        text = '\n'.join(line.rstrip() for line in (result.stdout + result.stderr).splitlines()) + '\n'
        log.write_text(text, encoding='utf-8')
        commands.append({'name': name, 'command': command, 'exit': result.returncode})
        result.check_returncode()
        print(f'{name}: PASS', flush=True)
        return result.stdout

    prefix = ('import resense, sys, pytest; from resense import _native; '
              'assert not resense.__file__.startswith("/opt/resense/"); assert _native.enabled(); '
              'sys.path.insert(0, "/opt/resense"); ')
    collected = run('full-suite-collection', prefix +
                    'sys.exit(pytest.main(["--collect-only", "-q", "-rs", "/opt/resense/tests"]))')
    tests = [f'/opt/resense/tests/{name}' for name in (
        'test_h4_spare_rearm.py', 'test_column_shipping.py', 'test_column_free_top.py',
        'test_late_candidates.py', 'test_structure_cut.py')]
    tested = run('changed-shipping-units', prefix + f'sys.exit(pytest.main({["-q", "-rs", *tests]!r}))')
    counts = {name: int(n) for n, name in re.findall(r'(\d+) (passed|skipped|deselected)', tested)}
    assert counts.get('passed', 0) > 0 and counts.get('skipped', 0) == 0, counts
    configuration = run('shipping-fixture-paths', '''
import hashlib, json
from pathlib import Path
import resense
from resense import _native
from resense.config import DetectorConfig
root = Path('/opt/resense')
assert not Path(resense.__file__).is_relative_to(root)
assert _native.enabled(), _native.status()
relative = 'docs/evidence/integration_2026-10-16/h4_safety/results/rearm_witness.json'
manifest = json.loads(Path('/e2-context/fixture-manifest.json').read_text())
expected = next(f for f in manifest['fixtures'] if f['path'] == relative)
assert hashlib.sha256((root / relative).read_bytes()).hexdigest() == expected['sha256']
canonical = root / 'configs/default.yaml'
mirror = root / 'ros2_ws/src/resense_ros/config/detector.yaml'
assert canonical.read_bytes() == mirror.read_bytes()
for path in (canonical, mirror):
    assert DetectorConfig.from_yaml(str(path)).cluster.column_free_max_top == 0.0
assert DetectorConfig().cluster.column_free_max_top == 0.0
print(json.dumps({'source_commit': manifest['source_commit'], 'import': resense.__file__,
                  'native': _native.status(), 'h4_witness': expected,
                  'shipping_yaml_and_ros_mirror_identical': True, 'shipping_h1_disabled': True}))
''')
    report = {'result': 'PASS', 'image': args.image, 'changed_shipping_counts': counts,
              'full_suite_collection_summary': collected.strip().splitlines()[-1],
              'fixture_paths': json.loads(configuration.strip().splitlines()[-1]), 'commands': commands,
              'scope': 'full-suite collection/imports and focused changed tests; not the full test run or 1.1.0 release'}
    (args.out / 'shipping-result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in report.items() if k != 'commands'}, indent=2))


if __name__ == '__main__':
    main()
