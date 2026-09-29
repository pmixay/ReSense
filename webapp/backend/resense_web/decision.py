"""The ROS node's per-frame decision rule (``DetectorNode.decision``) on a FrameResult dict."""
from __future__ import annotations

DECISIONS = ("GO", "CAUTION", "STOP", "FAULT")
LETTER = {"GO": "G", "CAUTION": "C", "STOP": "S", "FAULT": "F"}
FROM_LETTER = {v: k for k, v in LETTER.items()}


def decision_of(result: dict) -> str:
    """STOP if ``obstacle``; else FAULT if ``health.level == "error"``; else CAUTION if ``warning``
    or ``health.decision_level`` (fallback ``health.level``) is ``"warn"``; else GO."""
    health = result.get("health") or {}
    level = health.get("level", "ok")
    if result.get("obstacle"):
        return "STOP"
    if level == "error":
        return "FAULT"
    if result.get("warning") or health.get("decision_level", level) == "warn":
        return "CAUTION"
    return "GO"


def letter_of(decision: str) -> str:
    return LETTER.get(decision, "F")
