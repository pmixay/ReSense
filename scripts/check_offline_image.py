#!/usr/bin/env python3
"""Check the installed detector/native library and the rebuilt ROS overlay, from outside source.

Run through the image entrypoint with `docker run --rm --network none -w / IMAGE
python3 /opt/resense/scripts/check_offline_image.py`. No tools-image dependencies needed.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    import resense
    import resense.detector
    from resense import _native as native
    import resense_ros.detector_node
    from ament_index_python.packages import get_package_share_directory

    root = Path('/opt/resense')
    source = root / 'resense'
    installed = Path(resense.__file__).resolve().parent
    assert not Path.cwd().is_relative_to(root), Path.cwd()
    assert not installed.is_relative_to(root), installed
    assert resense.__version__ == importlib.metadata.version('resense')
    # An old wheel or a source-tree import must not make a changed-source rebuild look green.
    expected = {p.relative_to(source): digest(p) for p in source.rglob('*.py')}
    actual = {p.relative_to(installed): digest(p) for p in installed.rglob('*.py')}
    assert actual == expected, 'installed Python files differ from the copied source'
    assert native.AVAILABLE and native.enabled(), native.status()
    library = Path(native.LIBRARY).resolve()
    assert library.parent == installed, library

    workspace = root / 'ros2_ws'
    ros_source = workspace / 'src/resense_ros'
    share = Path(get_package_share_directory('resense_ros'))
    assert share.is_relative_to(workspace / 'install'), share
    node = Path(resense_ros.detector_node.__file__).resolve()
    assert node == ros_source / 'resense_ros/detector_node.py', node
    launch = share / 'launch/detector.launch.py'
    config = share / 'config/detector.yaml'
    assert launch.read_bytes() == (ros_source / 'launch/detector.launch.py').read_bytes()
    assert config.read_bytes() == (root / 'configs/default.yaml').read_bytes()
    broken = [str(p) for p in (workspace / 'install').rglob('*') if p.is_symlink() and not p.exists()]
    assert not broken, broken
    print(json.dumps({
        'version': resense.__version__, 'package': str(installed),
        'native': native.status(), 'native_library': str(library),
        'native_sha256': digest(library),
        'native_source_sha256': digest(root / 'native/resense_native.cpp'),
        'ros_node': str(node), 'share': str(share),
        'launch_sha256': digest(launch), 'config_sha256': digest(config),
        'sys_path': sys.path,
    }, indent=2))


if __name__ == '__main__':
    main()
