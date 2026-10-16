"""Versioned, stateless base decision on a FrameResult or its serialized mapping.

No ROS or detector imports. Freshness evaluation, watchdogs, range invalidation and
the STOP latch belong to the caller. v1 is the compatibility default; v2 is a
proposal to measure on final 1.1.0, not an accepted deployment default.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import math
from numbers import Real

DECISIONS = ("GO", "CAUTION", "STOP", "FAULT")
_MISSING = object()
_RANGE_REASONS = {"beyond_axis", "beyond_height_ref"}


@dataclass(frozen=True)
class DecisionPolicy:
    """Runtime policy, never part of the sealed detector YAML.

    v2's proposed compactness bar is a positive finite 3-D box with every extent
    <= compact_max_size_m. Only unreasoned (margin) warnings use D_c. Other
    demotion reasons, including unknown future ones and doubt, are retained.
    Selecting v2 presupposes the reviewed 1.1.0 column semantics.
    """

    version: str = "v1"
    caution_distance_m: float = 80.0
    compact_max_size_m: float = 3.0

    def __post_init__(self):
        if self.version not in ("v1", "v2"):
            raise ValueError(f"unknown decision policy: {self.version!r}")
        for name in ("caution_distance_m", "compact_max_size_m"):
            value = getattr(self, name)
            if not _positive_finite(value):
                raise ValueError(f"{name} must be a positive finite number")


@dataclass(frozen=True)
class PolicyDecision:
    decision: str
    decision_policy: str
    caution_reason: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        """Additive status fields; reasons are always a JSON array, empty off CAUTION."""
        return {"decision": self.decision, "decision_policy": self.decision_policy,
                "caution_reason": list(self.caution_reason)}


def _get(source, key, default=None):
    return source.get(key, default) if isinstance(source, Mapping) else getattr(source, key, default)


def _record(source):
    return isinstance(source, Mapping) or hasattr(source, "__dict__")


def _positive_finite(value):
    try:
        return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value) and value > 0
    except OverflowError:
        return False


def _flag(value):
    # numpy.bool_ on an object FrameResult is also legitimate, without importing numpy.
    if isinstance(value, bool) or type(value).__name__ == "bool_":
        return bool(value)
    raise ValueError("decision flags must be booleans")


def _warning_reason(item, policy):
    """None means deliberately suppressed; incomplete evidence keeps CAUTION."""
    if not _record(item):
        return "incomplete_advisory"
    reason = _get(item, "reason", _MISSING)
    if not isinstance(reason, str):
        return "incomplete_advisory"
    if reason == "doubt":
        return "doubt"
    if reason == "column":
        return None
    if reason in _RANGE_REASONS:
        size = _get(item, "size")
        try:
            if len(size) != 3 or not all(_positive_finite(v) for v in size):
                return "incomplete_advisory"
        except TypeError:
            return "incomplete_advisory"
        return "compact_range_object" if max(size) <= policy.compact_max_size_m else None
    if reason == "":
        distance = _get(item, "distance")
        if not _positive_finite(distance):
            return "incomplete_advisory"
        return "margin_object" if distance <= policy.caution_distance_m else None
    return "advisory_object"


def evaluate_decision(res, policy: DecisionPolicy | str = "v1") -> PolicyDecision:
    """STOP > FAULT > CAUTION > GO, without mutating the input.

    Missing legacy flags/health default to false/ok, as in the original rule.
    Malformed flags or health fail closed to FAULT; a valid true obstacle always
    wins, including when the caller has applied its STOP latch. v2 never needs
    advisory geometry to preserve STOP or health warnings. An aggregate warning
    without usable detail stays CAUTION (old outputs cannot prove suppression).
    Stored ``decision`` / ``caution_reason`` fields are deliberately not trusted.
    """
    if isinstance(policy, str):
        policy = DecisionPolicy(version=policy)
    if not isinstance(policy, DecisionPolicy):
        raise TypeError("policy must be a DecisionPolicy or version string")

    def answer(word, reasons=()):
        return PolicyDecision(word, policy.version, tuple(sorted(set(reasons))))

    if not _record(res):
        return answer("FAULT")
    try:
        if _flag(_get(res, "obstacle", False)):
            return answer("STOP")
        warning = _flag(_get(res, "warning", False))
    except ValueError:
        return answer("FAULT")
    health = _get(res, "health")
    if health is None:
        health = {}
    if not isinstance(health, Mapping):
        return answer("FAULT")
    level = health.get("level", "ok")
    decision_level = health.get("decision_level", level)
    if (not isinstance(level, str) or not isinstance(decision_level, str)
            or level not in ("ok", "warn", "error") or decision_level not in ("ok", "warn", "error")):
        return answer("FAULT")
    if level == "error" or decision_level == "error":
        return answer("FAULT")
    reasons = ["health_warning"] if decision_level == "warn" else []
    if policy.version == "v1":
        if warning:
            reasons.append("advisory_object")
    elif warning:
        warnings = _get(res, "warnings")
        if not isinstance(warnings, (list, tuple)) or not warnings:
            reasons.append("incomplete_advisory")
        else:
            reasons.extend(reason for item in warnings
                           if (reason := _warning_reason(item, policy)) is not None)
    return answer("CAUTION", reasons) if reasons else answer("GO")


def decision(res, policy: DecisionPolicy | str = "v1") -> str:
    """Compatibility word-only API; use evaluate_decision for additive status fields."""
    return evaluate_decision(res, policy).decision
