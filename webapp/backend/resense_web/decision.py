"""Shared base policy on a FrameResult dict (no ROS freshness/watchdog evaluation)."""
from __future__ import annotations

try:
    from resense_ros.decision_policy import DECISIONS, decision as decision_of
except ModuleNotFoundError as exc:
    if exc.name not in ("resense_ros", "resense_ros.decision_policy"):
        raise
    # Source checkout with no ROS install, or an older overlay lacking this module.
    # An installed wheel gets resense-ros through its declared dependency instead.
    import importlib.util
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    helper = root / "scripts/decision_policy_import.py"
    if not helper.is_file():
        raise
    spec = importlib.util.spec_from_file_location("_resense_web_policy_import", helper)
    loader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loader)
    policy = loader.load_policy(root)
    DECISIONS, decision_of = policy.DECISIONS, policy.decision

__all__ = ["DECISIONS", "LETTER", "FROM_LETTER", "decision_of", "letter_of"]

LETTER = {"GO": "G", "CAUTION": "C", "STOP": "S", "FAULT": "F"}
FROM_LETTER = {v: k for k, v in LETTER.items()}


def letter_of(decision: str) -> str:
    return LETTER.get(decision, "F")
