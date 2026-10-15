#!/usr/bin/env python3
"""Rescore saved full FrameResult JSONL, without a detector run or new data.

Examples (five empty bags + ride pieces, and separately set O):
  python scripts/rescore_decisions.py --policy v2 --empty out/empty.jsonl out/new_data_0.jsonl
  python scripts/rescore_decisions.py --policy v2 --objects out/cloud_with_fake_obj.jsonl

Positional paths auto-classify standard empty/set-O names; other files are
unclassified. Both FrameResult JSONL and judge_runner.record JSONL are supported.
--range takes full result JSONL with a boolean `visible` per frame
(B/C). The judge's distance/decision-only range summaries cannot be rescored.
Metrics are frame-level alerts, not object-matched detection recall. --gt uses
the existing set-O labels; in-gauge means organizer intent, visible and plausible.
The measured-envelope subset (n_in_envelope > 0) is also reported separately.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from decision_policy_import import load_policy  # noqa: E402

POLICY = load_policy(ROOT)
DECISIONS, DecisionPolicy, evaluate_decision = POLICY.DECISIONS, POLICY.DecisionPolicy, POLICY.evaluate_decision

EMPTY_BAGS = {"doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
              "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch"}


def role_of(path):
    if path.stem == "cloud_with_fake_obj":
        return "objects"
    if path.stem in EMPTY_BAGS or path.stem == "new_data" or path.stem.startswith("new_data_"):
        return "empty"
    return "unclassified"


def counts():
    return {word: 0 for word in DECISIONS}


def retention():
    return {"frames": 0, "v1_caution_or_stop": 0, "selected_caution_or_stop": 0,
            "lost_v1_alerts": 0, "gained_alerts": 0}


def add_retention(total, before, after):
    was = before in ("CAUTION", "STOP")
    now = after in ("CAUTION", "STOP")
    total["frames"] += 1
    total["v1_caution_or_stop"] += int(was)
    total["selected_caution_or_stop"] += int(now)
    total["lost_v1_alerts"] += int(was and not now)
    total["gained_alerts"] += int(now and not was)


def finish_retention(total):
    n = total["v1_caution_or_stop"]
    return {**total, "v1_alert_retention": (n - total["lost_v1_alerts"]) / n if n else None}


def normalize_row(row):
    """Expand judge_runner.record's named aliases, never infer health from `decision`."""
    if "health" in row or not any(key in row for key in ("level", "dlevel", "warns", "dets")):
        return row
    health = {"level": row.get("level", "ok")}
    if "dlevel" in row:
        health["decision_level"] = row["dlevel"]
    warnings = row.get("warns")
    if isinstance(warnings, list):
        warnings = [{**item, "distance": item.get("d")} if isinstance(item, dict) else item for item in warnings]
    return {**row, "health": health, "frame": row.get("i"), "warnings": warnings}


def rescore_file(path, role, policy, gt):
    before, after = counts(), counts()
    transitions, reasons = Counter(), Counter()
    intent, measured, object_frames, visible = (retention() for _ in range(4))
    per_label = {}
    loss_examples = []
    digest = hashlib.sha256()
    skipped_snapshots = 0
    with path.open("rb") as source:
        for line_number, line in enumerate(source, 1):
            digest.update(line)
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError("expected a full FrameResult mapping")
                if row.get("snapshot_kind", "frame") != "frame":
                    skipped_snapshots += 1
                    continue
                if "obstacle" not in row or "warning" not in row:
                    raise ValueError("full results need obstacle and warning flags; decision-only rows cannot be rescored")
                row = normalize_row(row)
                old = evaluate_decision(row)
                new = evaluate_decision(row, policy)
                before[old.decision] += 1
                after[new.decision] += 1
                transitions[f"{old.decision}->{new.decision}"] += 1
                reasons.update(new.caution_reason)
                frame = row.get("frame", line_number - 1)
                labels = []
                if role == "objects":
                    if "frame" not in row:
                        raise ValueError("set-O results require frame indices for label alignment")
                    labels = [g for g in gt.get(f"{int(frame):05d}", [])
                              if g.get("in_gauge") and g.get("plausible", True) and g.get("n_points", 1) > 0]
                    if labels:
                        add_retention(object_frames, old.decision, new.decision)
                    for label in labels:
                        add_retention(intent, old.decision, new.decision)
                        add_retention(per_label.setdefault(label["label"], retention()), old.decision, new.decision)
                        if label.get("n_in_envelope", 1) > 0:
                            add_retention(measured, old.decision, new.decision)
                if role == "range":
                    if not isinstance(row.get("visible"), bool):
                        raise ValueError("full range results require an explicit boolean visible field")
                    if row["visible"]:
                        add_retention(visible, old.decision, new.decision)
                target = bool(labels) or (role == "range" and row["visible"])
                if target and old.decision in ("CAUTION", "STOP") and new.decision not in ("CAUTION", "STOP"):
                    if len(loss_examples) < 20:
                        loss_examples.append({"frame": frame, "labels": [g["label"] for g in labels],
                                              "v1": old.decision, "selected": new.decision,
                                              "warnings": row.get("warnings", [])})
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError(f"{path}:{line_number}: {exc}") from exc
    n = sum(after.values())
    result = {"path": str(path), "sha256": digest.hexdigest(), "role": role, "frames": n,
              "skipped_snapshots": skipped_snapshots, "v1": before, "selected": after,
              "selected_caution_fraction": after["CAUTION"] / n if n else None,
              "transitions": dict(sorted(transitions.items())), "caution_reason_frames": dict(sorted(reasons.items()))}
    if role == "objects":
        result.update(in_gauge_object_frames=finish_retention(intent),
                      measured_envelope_object_frames=finish_retention(measured),
                      in_gauge_frames=finish_retention(object_frames),
                      per_label={k: finish_retention(v) for k, v in per_label.items()}, loss_examples=loss_examples)
    if role == "range":
        result.update(visible_frames=finish_retention(visible), loss_examples=loss_examples)
    return result


def summarize(sources, policy):
    groups = {}
    for role in ("empty", "objects", "range", "unclassified"):
        selected = [s for s in sources if s["role"] == role]
        group = {"frames": sum(s["frames"] for s in selected),
                 "v1": {w: sum(s["v1"][w] for s in selected) for w in DECISIONS},
                 "selected": {w: sum(s["selected"][w] for s in selected) for w in DECISIONS}}
        group["selected_caution_fraction"] = group["selected"]["CAUTION"] / group["frames"] if group["frames"] else None
        for metric in ("in_gauge_object_frames", "measured_envelope_object_frames", "in_gauge_frames", "visible_frames"):
            totals = [s[metric] for s in selected if metric in s]
            if totals:
                group[metric] = finish_retention({key: sum(t[key] for t in totals) for key in retention()})
        groups[role] = group
    empty = groups["empty"]["selected_caution_fraction"]

    def retained(role, metric):
        value = groups[role].get(metric)
        if not value or not value["frames"] or not value["v1_caution_or_stop"]:
            return "not_measured"
        return "fail" if value["lost_v1_alerts"] else "pass"

    checks = {"empty_caution_le_25pct": "not_measured" if empty is None else "pass" if empty <= .25 else "fail",
              "in_gauge_object_alert_retention": retained("objects", "in_gauge_object_frames"),
              "range_visible_alert_retention": retained("range", "visible_frames")}
    policy_path = Path(sys.modules[evaluate_decision.__module__].__file__).resolve()
    return {"schema": "resense.decision_rescore.v1", "policy": {"version": policy.version,
             "caution_distance_m": policy.caution_distance_m, "compact_max_size_m": policy.compact_max_size_m},
            "implementation": {"rescorer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                               "policy_path": str(policy_path),
                               "policy_sha256": hashlib.sha256(policy_path.read_bytes()).hexdigest()},
            "scope": "saved base decisions only; no node freshness, watchdog or STOP-latch replay",
            "groups": groups, "checks": checks, "sources": sources,
            "acceptance": "not_accepted: requires complete final-1.1.0 judge-path evidence, node integration and captain review"}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("results", nargs="*", type=Path)
    for role in ("empty", "objects", "range"):
        parser.add_argument(f"--{role}", nargs="+", type=Path, default=[])
    parser.add_argument("--policy", choices=("v1", "v2"), default="v1")
    parser.add_argument("--caution-distance-m", type=float, default=80.0)
    parser.add_argument("--compact-max-size-m", type=float, default=3.0)
    parser.add_argument("--gt", type=Path, default=ROOT / "labels/cloud_with_fake_obj.json")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--require-targets", action="store_true", help="exit 1 if any target fails or is not measured")
    args = parser.parse_args(argv)
    paths = [(path, role_of(path)) for path in args.results]
    paths += [(path, role) for role in ("empty", "objects", "range") for path in getattr(args, role)]
    if not paths:
        parser.error("supply saved full FrameResult JSONL paths (--empty, --objects, --range or positional)")
    if len({path.resolve() for path, _ in paths}) != len(paths):
        parser.error("duplicate input path would double-count frames")
    try:
        policy = DecisionPolicy(args.policy, args.caution_distance_m, args.compact_max_size_m)
        gt = json.loads(args.gt.read_text(encoding="utf-8")) if any(role == "objects" for _, role in paths) else {}
        sources = [rescore_file(path, role, policy, gt) for path, role in paths]
        result = summarize(sources, policy)
        if gt:
            result["labels"] = {"path": str(args.gt), "sha256": hashlib.sha256(args.gt.read_bytes()).hexdigest()}
        text = json.dumps(result, indent=2, allow_nan=False) + "\n"
        if args.out:
            args.out.write_text(text, encoding="utf-8")
        print(text, end="")
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    return int(args.require_targets and any(value != "pass" for value in result["checks"].values()))


if __name__ == "__main__":
    raise SystemExit(main())
