"""Run the entire installed-image test suite; retain counts and data-only deselection receipts."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import time


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--out', type=Path, required=True)
    args = cli.parse_args()
    assert Path.cwd() == Path('/'), Path.cwd()
    assert os.environ['RESENSE_REQUIRE_SYNTHETIC'] == '1'
    assert os.environ['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] == '1'

    import resense
    from resense import _native
    import open3d
    import pytest

    installed = Path(resense.__file__).resolve()
    assert not installed.is_relative_to('/opt/resense'), installed
    assert _native.AVAILABLE and _native.enabled(), _native.status()
    source_paths = [
        'ros2_ws/src/resense_ros/resense_ros/detector_node.py',
        'ros2_ws/src/resense_ros/resense_ros/decision_policy.py',
        'ros2_ws/src/resense_ros/launch/detector.launch.py',
        'scripts/startup_acceptance.py', 'scripts/decision_policy_import.py',
        'webapp/backend/resense_web/decision.py',
    ]
    identity = {
        'cwd': str(Path.cwd()), 'python': platform.python_version(),
        'resense': str(installed), 'version': resense.__version__, 'native': _native.status(),
        'ros_node': importlib.util.find_spec('resense_ros.detector_node').origin, 'open3d': open3d.__version__,
        'packages': {name: importlib.metadata.version(name) for name in (
            'numpy', 'scipy', 'scikit-learn', 'pytest', 'rosbags', 'zstandard')},
        'env': {key: os.environ.get(key) for key in (
            'RESENSE_REQUIRE_SYNTHETIC', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD',
            'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')},
        'source_sha256': {name: hashlib.sha256((Path('/opt/resense') / name).read_bytes()).hexdigest()
                          for name in source_paths},
    }
    write(args.out / 'runtime_identity.json', identity)
    print(json.dumps(identity, indent=2), flush=True)
    # Preserve installed resense; add the source root only for tests' scripts.* consumers.
    sys.path.insert(0, '/opt/resense')

    class Receipt:
        def __init__(self):
            self.deselected = []
            self.skipped = []
            self.failed = []

        def pytest_deselected(self, items):
            for item in items:
                marker = item.get_closest_marker('realdata')
                path = str(marker.args[0]) if marker and marker.args else None
                self.deselected.append({'nodeid': item.nodeid, 'realdata_path': path,
                                        'allowed_missing_realdata': path is not None and not Path(path).is_dir()})

        def pytest_runtest_logreport(self, report):
            if report.skipped:
                self.skipped.append(report.nodeid)
            if report.failed:
                self.failed.append({'nodeid': report.nodeid, 'phase': report.when})

    receipt = Receipt()
    start = time.monotonic()
    code = int(pytest.main(['-q', '-rs', '--junitxml=' + str(args.out / 'junit.xml'),
                           '/opt/resense/tests'], plugins=[receipt]))
    allowed = all(item['allowed_missing_realdata'] for item in receipt.deselected)
    write(args.out / 'suite_receipt.json', {
        'pytest_exit': code, 'pytest_seconds': round(time.monotonic() - start, 3),
        'deselected': receipt.deselected, 'only_missing_realdata_deselected': allowed,
        'skipped': receipt.skipped, 'failed': receipt.failed,
    })
    sys.exit(code or (1 if receipt.skipped or not allowed else 0))


if __name__ == '__main__':
    main()
