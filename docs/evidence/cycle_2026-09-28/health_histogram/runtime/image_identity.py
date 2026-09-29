"""Record installed and build-tree identities before matched ROS measurements."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

import resense
from resense import _native
from resense.config import DetectorConfig
import resense_ros.detector_node

sys.path.insert(0, '/opt/resense/scripts')
from detector_freeze import source_hashes, source_digest

root = Path('/opt/resense')
installed = Path(resense.__file__).resolve().parent
files = source_hashes(root)
actual = {}
for relative in files:
    if relative.startswith('resense/'):
        path = installed / relative.removeprefix('resense/')
        actual[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
assert all(files[name] == checksum for name, checksum in actual.items())
assert _native.enabled(), _native.status()
native = Path(_native.LIBRARY).resolve()
assert native.parent == installed
node = Path(resense_ros.detector_node.__file__).resolve()
assert node.read_bytes() == (root / 'ros2_ws/src/resense_ros/resense_ros/detector_node.py').read_bytes()
config = DetectorConfig.from_yaml(str(root / 'configs/default.yaml')).to_dict()
report = {
    'schema': 'resense-health-runtime-image-identity-v1',
    'source_sha256': source_digest(files), 'files': files,
    'installed_package': str(installed), 'installed_files': actual,
    'native_path': str(native), 'native_sha256': hashlib.sha256(native.read_bytes()).hexdigest(),
    'node_path': str(node), 'node_sha256': hashlib.sha256(node.read_bytes()).hexdigest(),
    'effective_config': config,
    'effective_config_sha256': hashlib.sha256(json.dumps(config, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
    'packages': {name: importlib.metadata.version(name) for name in ('numpy', 'scipy', 'scikit-learn', 'pyyaml', 'rosbags', 'open3d')},
    'observer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
}
Path(sys.argv[1]).write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: report[key] for key in ('source_sha256', 'native_sha256', 'effective_config_sha256')}))
