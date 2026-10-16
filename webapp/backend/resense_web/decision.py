"""Shared base policy on a FrameResult dict (no ROS freshness/watchdog evaluation)."""
from __future__ import annotations

try:
    from resense_ros.decision_policy import DECISIONS, decision as decision_of, evaluate_decision
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
    evaluate_decision = policy.evaluate_decision

__all__ = ["DECISIONS", "LETTER", "FROM_LETTER", "decision_of", "evaluate_decision", "letter_of", "import_decision"]

LETTER = {"GO": "G", "CAUTION": "C", "STOP": "S", "FAULT": "F"}
FROM_LETTER = {v: k for k, v in LETTER.items()}


def import_decision(d: dict) -> None:
    """Preserve published historical decisions and reasons; derive only absent decisions.

    Invalid additive fields fail the import rather than quietly dropping an explanation.
    A legacy published decision without reasons stays explicitly unexplained.
    """
    if "caution_reason" in d and (not isinstance(d["caution_reason"], list)
                                  or not all(isinstance(v, str) for v in d["caution_reason"])):
        raise ValueError("caution_reason must be an array of strings")
    if "decision_policy" in d and not isinstance(d["decision_policy"], str):
        raise ValueError("decision_policy must be a string")
    if "decision" in d:
        if not isinstance(d["decision"], str) or d["decision"] not in DECISIONS:
            raise ValueError("Invalid published decision")
    else:
        d.update(evaluate_decision(d).to_dict())


def letter_of(decision: str) -> str:
    return LETTER.get(decision, "F")
