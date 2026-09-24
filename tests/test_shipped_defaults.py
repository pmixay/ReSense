"""Freeze the shipped CV switches and the ROS copy of the canonical parameters."""

from pathlib import Path

import yaml

from resense.config import DetectorConfig


ROOT = Path(__file__).resolve().parents[1]


def test_shipped_yaml_semantics_and_opt_in_defaults():
    canonical = ROOT / "configs/default.yaml"
    ros = ROOT / "ros2_ws/src/resense_ros/config/detector.yaml"
    with canonical.open(encoding="utf-8") as src, ros.open(encoding="utf-8") as dst:
        assert yaml.safe_load(src) == yaml.safe_load(dst)

    for cfg in (DetectorConfig(), DetectorConfig.from_yaml(str(canonical)),
                DetectorConfig.from_yaml(str(ros))):
        assert cfg.track.rails_far_check_enabled is False
        assert cfg.lowobj.near_enabled is False
        assert cfg.accumulation.estimate_speed is False
