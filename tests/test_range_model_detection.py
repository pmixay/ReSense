"""``sensor_profiles.detect_range_model``: the range-density model the node's ``clear_range_policy:=auto`` (default
since 1.3, user decision 22.10) reads from a cloud's own point fields."""
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ros2_ws/src/resense_ros"))

from resense_ros.sensor_profiles import detect_range_model  # noqa: E402


def test_range_model_detection_reads_only_the_documented_point_layouts():
    """``detect_range_model`` on the field layouts recorded at intake (docs/evidence/extended_data_2026-10-17):
    Falcon Prime by its own fields, Pandar128 by 128 ``ring`` channels; everything else stays unknown."""
    falcon = ["x", "y", "z", "timestamp", "intensity", "flags", "elongation", "scan_id", "scan_idx", "is_2nd_return"]
    pandar = ["x", "y", "z", "intensity", "ring", "timestamp"]
    rings = np.arange(10000) % 128
    assert detect_range_model(falcon) == "falcon_prime"
    assert detect_range_model(pandar, rings) == "pandar128"
    assert detect_range_model(pandar, rings[rings < 100]) == "pandar128"          # 100 channels in view
    assert detect_range_model(["x", "y", "z", "intensity"]) is None                 # Set O: no ring
    assert detect_range_model(pandar, np.zeros(10000, np.uint16)) is None           # a constant ring
    assert detect_range_model(pandar, rings[rings < 32]) is None                    # too few channels
    assert detect_range_model(pandar, np.arange(10000) % 200) is None               # more than 128 channels
    assert detect_range_model(pandar) is None                                       # ring declared, not read
    assert detect_range_model(falcon + ["ring"], rings) == "pandar128"              # a ring field is Pandar's rule
