"""Every config field: code default, both YAML copies, effective value per shipped profile.

    python inventory.py <repo> > fields.tsv
Profiles: pandar = configs/default.yaml as loaded (the CLI and the node's manual / pandar128 path);
falcon_ros / falcon_native = default.yaml through resense_ros.sensor_profiles.apply_sensor_profile.
"""
import dataclasses, sys, os, yaml
repo = sys.argv[1]
sys.path[:0] = [repo, os.path.join(repo, "ros2_ws/src/resense_ros")]
from resense.config import DetectorConfig
from resense_ros.sensor_profiles import apply_sensor_profile

code = DetectorConfig()
dy = yaml.safe_load(open(os.path.join(repo, "configs/default.yaml")))["resense"]
ry = yaml.safe_load(open(os.path.join(repo, "ros2_ws/src/resense_ros/config/detector.yaml")))["resense"]
base = DetectorConfig.from_yaml(os.path.join(repo, "configs/default.yaml"))
prof = {"pandar": apply_sensor_profile(base, "pandar128")[0],
        "falcon_ros": apply_sensor_profile(base, "falcon_ros")[0],
        "falcon_native": apply_sensor_profile(base, "falcon_native")[0]}
MISSING = "<absent>"
print("\t".join(["key", "code", "default.yaml", "ros.yaml", "pandar", "falcon_ros", "falcon_native"]))
for sec in [f.name for f in dataclasses.fields(code) if dataclasses.is_dataclass(getattr(code, f.name))]:
    for f in dataclasses.fields(getattr(code, sec)):
        k = f.name
        vals = [getattr(getattr(code, sec), k),
                dy.get(sec, {}).get(k, MISSING), ry.get(sec, {}).get(k, MISSING)]
        vals += [getattr(getattr(prof[p], sec), k) for p in prof]
        print("\t".join([f"{sec}.{k}"] + [repr(v) for v in vals]))
print("\t".join(["voxel", repr(code.voxel), repr(dy.get("voxel", MISSING)), repr(ry.get("voxel", MISSING))]
                + [repr(prof[p].voxel) for p in prof]))
