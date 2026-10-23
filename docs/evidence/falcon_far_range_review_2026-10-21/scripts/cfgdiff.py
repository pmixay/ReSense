"""Effective config per profile in a checkout (RESENSE_REPO), as the node builds it (YAML, calibration on, profile)."""
import json, os, sys
from dataclasses import asdict
repo = os.environ["RESENSE_REPO"]
sys.path.insert(0, repo); sys.path.insert(0, repo + "/ros2_ws/src/resense_ros")
import resense
assert resense.__file__.startswith(repo), resense.__file__
from resense.config import DetectorConfig
from resense_ros.sensor_profiles import apply_sensor_profile
out = {}
for yaml_path in ("configs/default.yaml", "ros2_ws/src/resense_ros/config/detector.yaml"):
    for prof in ("manual", "pandar128", "falcon_ros", "falcon_native"):
        cfg = DetectorConfig.from_yaml(os.path.join(repo, yaml_path))
        cfg.calibration.enabled = True
        try:
            cfg, _ = apply_sensor_profile(cfg, prof)
        except Exception as e:
            out[f"{yaml_path}|{prof}"] = repr(e); continue
        out[f"{yaml_path}|{prof}"] = asdict(cfg)
cls = asdict(DetectorConfig())
out["class_default"] = cls
json.dump(out, open(sys.argv[1], "w"), default=str, indent=0, sort_keys=True)
