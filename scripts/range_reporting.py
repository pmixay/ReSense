"""Load the same C2 range candidate used by the ROS node, without importing ROS."""
from pathlib import Path

from scripts.decision_policy_import import load_policy

POLICY = load_policy(Path(__file__).resolve().parents[1])
small_target_limit = POLICY.small_target_limit
candidate_ranges = POLICY.candidate_ranges
