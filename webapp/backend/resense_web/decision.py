"""Shared base policy on a FrameResult dict (no ROS freshness/watchdog evaluation)."""
from __future__ import annotations

try:
    from resense_ros.decision_policy import DECISIONS, decision as decision_of
except ModuleNotFoundError as exc:
    if exc.name != "resense_ros":
        raise
    from ros2_ws.src.resense_ros.resense_ros.decision_policy import DECISIONS, decision as decision_of

__all__ = ["DECISIONS", "LETTER", "FROM_LETTER", "decision_of", "letter_of"]

LETTER = {"GO": "G", "CAUTION": "C", "STOP": "S", "FAULT": "F"}
FROM_LETTER = {v: k for k, v in LETTER.items()}


def letter_of(decision: str) -> str:
    return LETTER.get(decision, "F")
