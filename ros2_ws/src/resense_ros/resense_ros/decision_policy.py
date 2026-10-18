"""Versioned, stateless base decision on a FrameResult or its serialized mapping.

Decision APIs have no ROS or detector imports. The optional C2 range screen loads
the existing sensor-density prior on demand. Freshness evaluation, watchdogs and
the STOP latch belong to the caller. v1 is the compatibility default; v2 is a
proposal to measure on final 1.1.0, not an accepted deployment default.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache
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


def caution_advisory_distance(res, policy: DecisionPolicy | str = "v1") -> float | None:
    """Nearest advisory responsible for CAUTION, for the unaccepted C2 range screen.

    This shares the decision predicate, including v2's deliberate suppressions; it
    does not change decisions or the published runtime. ``None`` means CAUTION
    has no active object advisory (or the frame is not CAUTION). An aggregate or
    malformed active advisory whose distance is unknown returns 0, never an
    invented clear range. Health-only CAUTION supplies no geometric cap.
    """
    if isinstance(policy, str):
        policy = DecisionPolicy(version=policy)
    if evaluate_decision(res, policy).decision != "CAUTION":
        return None
    if not _flag(_get(res, "warning", False)):
        return None
    warnings = _get(res, "warnings")
    if not isinstance(warnings, (list, tuple)) or not warnings:
        return 0.0
    distances = []
    for item in warnings:
        if policy.version == "v2" and _warning_reason(item, policy) is None:
            continue
        value = _get(item, "distance")
        if not _positive_finite(value):
            return 0.0
        distances.append(float(value))
    return min(distances) if distances else None


def _nonnegative(value, name):
    if (not isinstance(value, Real) or isinstance(value, bool)
            or not math.isfinite(value) or value < 0):
        raise ValueError(f"{name} must be finite and nonnegative")
    return float(value)


@lru_cache(maxsize=64, typed=True)
def small_target_limit(sensor_model: str, min_points_far: int = 3,
                       max_range: float = 250.0) -> float | None:
    """Largest distance satisfying the existing 0.3 x 0.3 m expected-return prior.

    Scan the piecewise angular-resolution model before refining its last crossing;
    the elevation-density jump means a single global bisection is not valid.
    """
    if sensor_model not in ("pandar128", "unknown", "falcon_prime"):
        raise ValueError(f"unsupported sensor model: {sensor_model}")
    if (not isinstance(min_points_far, int) or isinstance(min_points_far, bool)
            or min_points_far < 1):
        raise ValueError("min_points_far must be a positive integer")
    max_range = _nonnegative(max_range, "max_range")
    if sensor_model != "pandar128":
        return None
    if max_range == 0:
        return 0.0
    import numpy as np
    from resense.sensor import expected_points
    grid = np.linspace(0.0, max_range, 4097)
    eligible = np.flatnonzero(expected_points(grid, 0.3, 0.3) >= min_points_far)
    if not eligible.size:
        return 0.0
    last = int(eligible[-1])
    if last == len(grid) - 1:
        return max_range
    lo, hi = float(grid[last]), float(grid[last + 1])
    for _ in range(48):
        mid = (lo + hi) / 2.0
        if expected_points(mid, 0.3, 0.3) >= min_points_far:
            lo = mid
        else:
            hi = mid
    return lo


def candidate_ranges(row: dict, policy="v1", *, sensor_model="unknown",
                     min_points_far=3, max_range=250.0, cap_small_target=False,
                     profile="candidate") -> dict:
    """Return a copy with the C2 candidate fields; decisions/detections are intact.

    ``cap_small_target`` explicitly requests a size-qualified range, changing the
    meaning of clear distance. The conservative_2026_10_17 profile records the
    user's approved coverage tradeoff; the original C2 profile still fails.
    Without a validated sensor prior that requested range is unavailable (0).
    The advisory cap is rounded down to decimetres so serialization cannot extend
    it beyond the object. An invalid freshness record invalidates both ranges.
    """
    if profile not in ("candidate", "conservative_2026_10_17"):
        raise ValueError(f"unknown range reporting profile: {profile}")
    if profile != "candidate" and not cap_small_target:
        raise ValueError("the conservative profile requires the small-target cap")
    if profile != "candidate" and min_points_far != 3:
        raise ValueError("the accepted conservative profile requires measured min_points_far=3")
    out = deepcopy(row)
    health = out.get("health")
    if not isinstance(health, dict):
        raise ValueError("candidate ranges require a health mapping")
    clear = _nonnegative(out.get("clear_distance"), "clear_distance")
    out.setdefault("detector_clear_distance", clear)
    monitored = _nonnegative(health.get("monitored_range"), "monitored_range")
    cap = caution_advisory_distance(out, policy)
    if cap is not None:
        clear = min(clear, math.floor(cap * 10.0) / 10.0)
    freshness = out.get("freshness")
    invalid = (isinstance(freshness, dict) and freshness.get("valid") is False)
    if (invalid or health.get("freshness_valid") is False
            or evaluate_decision(out, policy).decision == "FAULT"
            or evaluate_decision({"health": health}, policy).decision == "FAULT"):
        clear, monitored = 0.0, 0.0
        health["monitored_range"] = 0.0
    limit = small_target_limit(sensor_model, min_points_far, max_range)
    small = None if limit is None else math.floor(min(monitored, limit) * 10.0) / 10.0
    if cap_small_target:
        clear = min(clear, small) if small is not None else 0.0
    out["clear_distance"] = health["clear_distance"] = clear
    if "clear" in out:  # preserve consistency for expanded judge_runner aliases
        out["clear"] = clear
    if "monitored" in out:
        out["monitored"] = health["monitored_range"]
    out["advisory_clear_cap"] = cap
    out["monitored_small"] = health["monitored_small"] = small
    out["monitored_small_model"] = {
        "sensor": sensor_model, "available": limit is not None,
        "target_width_m": 0.3, "target_height_m": 0.3,
        "min_points_far": min_points_far,
        "density_limit_m": limit,
        "meaning": "expected return density only; not measured detection or clear-track guarantee",
    }
    out["range_policy"] = ("c2_conservative_2026_10_17" if profile != "candidate" else
                           "c2_small_candidate_not_accepted" if cap_small_target else
                           "c2_advisory_candidate_not_accepted")
    return out
