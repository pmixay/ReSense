#!/usr/bin/env python3
"""Explain every captured H3 frame difference without changing gate acceptance."""
import argparse
from collections import Counter, defaultdict
import itertools
import json
import math
from pathlib import Path
import re
import statistics
import sys

from frame_diff import MISSING, changes, normalize, field_group

RANGE_FIELDS = {f"{representation}.{field}" for representation in ("raw", "serialized")
                for field in ("clear_distance", "health.clear_distance", "health.monitored_range")}
WALL_FIELD = re.compile(r"^(raw|serialized)\.(track|health)\.wall_drift$")
CLUSTER_METADATA = re.compile(r"^raw\.candidates\[\d+\]\.(cut|spared)$")
GROUPS = ("obstacle_warning", "nearest_clear", "detections_warnings", "candidates", "track", "health", "ego_motion", "mount", "other_result_fields")


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.write_bytes((json.dumps(data, indent=2, sort_keys=True) + "\n").encode())


def category(path, before, after):
    if path in RANGE_FIELDS:
        return "monitored_clear_range"
    if WALL_FIELD.fullmatch(path) and before is MISSING:
        return "added_wall_drift_metadata"
    if CLUSTER_METADATA.fullmatch(path) and before is MISSING:
        return "added_cluster_metadata"
    if before is MISSING or after is MISSING:
        return "other_schema_change"
    return "other_preexisting_field_change"


def numeric_pairs(a, b, path="raw"):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(a.keys() & b.keys()):
            yield from numeric_pairs(a[k], b[k], path + "." + k)
    elif isinstance(a, list) and isinstance(b, list):
        for i, (x, y) in enumerate(zip(a, b)):
            yield from numeric_pairs(x, y, path + f"[{i}]")
    elif type(a) in (int, float) and type(b) in (int, float):
        yield path, a, b


def analyze(base, candidate, diff, out):
    out.mkdir(exist_ok=False)
    generic = load(diff / "summary.json")
    if generic["controls"]["candidate_commit"] != "f8c088dc4f3243fbd15a3aae9be0459e8a0aa941":
        raise ValueError("this H3 interpretation is registered for f8c088dc only")
    group_stats = {g: dict(frames=0, changes=0) for g in GROUPS}
    categories = defaultdict(lambda: dict(frames=0, changes=0, examples=[]))
    fields = defaultdict(lambda: dict(frames=0, changes=0, examples=[]))
    datasets = defaultdict(Counter)
    checks = Counter()
    numeric = Counter()
    flags = {k: Counter() for k in ("cut", "spared")}
    flags_true_examples = {k: [] for k in flags}
    cap_examples = defaultdict(list)
    reductions = defaultdict(list)
    unexpected = []
    explicit = Counter({k: 0 for k in ("obstacle", "warning", "nearest_distance", "detections", "warnings", "n_candidates", "n_points", "n_corridor",
        "preexisting_track_fields", "non_range_non_latency_health", "ego_motion", "mount", "preexisting_raw_candidates", "raw_corridor_membership")})
    for path in sorted((base / "frames").glob("*.jsonl")):
        with path.open(encoding="utf-8") as left, (candidate / "frames" / path.name).open(encoding="utf-8") as right:
            for i, (x, y) in enumerate(itertools.zip_longest(left, right)):
                if x is None or y is None:
                    raise ValueError("unaligned frame count")
                a, b = json.loads(x), json.loads(y)
                if a["key"] != b["key"]:
                    raise ValueError("unaligned frame identity")
                dataset = "SetF" if path.name.startswith("setF_") else a["key"]["recording"]
                ident = dict(sequence_file=path.name, row=i, **a["key"])
                da, db = {}, {}
                for representation in ("raw", "serialized"):
                    da[representation], _ = normalize(a[representation])
                    db[representation], _ = normalize(b[representation])
                delta = list(changes(da, db))
                frame_categories, frame_groups, frame_fields = set(), set(), set()
                for field, old, new in delta:
                    cat, group = category(field, old, new), field_group(field)
                    name = re.sub(r"\[\d+\]", "[]", field)
                    example = dict(frame=ident, field=field, baseline=old, candidate=new)
                    categories[cat]["changes"] += 1
                    fields[name]["changes"] += 1
                    group_stats[group]["changes"] += 1
                    for entry in (categories[cat], fields[name]):
                        if len(entry["examples"]) < 3:
                            entry["examples"].append(example)
                    frame_categories.add(cat)
                    frame_groups.add(group)
                    frame_fields.add(name)
                    if cat.startswith("other_"):
                        unexpected.append(example)
                for key in frame_categories:
                    categories[key]["frames"] += 1
                    datasets[dataset][key + "_frames"] += 1
                for key in frame_groups:
                    group_stats[key]["frames"] += 1
                for key in frame_fields:
                    fields[key]["frames"] += 1
                datasets[dataset]["frames"] += 1
                checks["frames"] += 1
                sa, sb = da["serialized"], db["serialized"]
                ra, rb = da["raw"], db["raw"]
                for key in ("obstacle", "warning", "nearest_distance", "detections", "warnings", "n_candidates", "n_points", "n_corridor"):
                    explicit[key] += sa[key] != sb[key]
                old_track = sa["track"]
                new_track = {k: v for k, v in sb["track"].items() if k != "wall_drift"}
                explicit["preexisting_track_fields"] += old_track != new_track
                old_health = {k: v for k, v in sa["health"].items() if k not in ("monitored_range", "clear_distance", "wall_drift")}
                new_health = {k: v for k, v in sb["health"].items() if k not in ("monitored_range", "clear_distance", "wall_drift")}
                explicit["non_range_non_latency_health"] += old_health != new_health
                for key in ("mount",):
                    explicit[key] += sa[key] != sb[key]
                motion_keys = [k for k in sa if k.startswith("ego_") or k == "n_accumulated"]
                explicit["ego_motion"] += any(sa[k] != sb[k] for k in motion_keys)
                old_candidates = ra["candidates"]
                new_candidates = [{k: v for k, v in c.items() if k not in ("cut", "spared")} for c in rb["candidates"]]
                explicit["preexisting_raw_candidates"] += old_candidates != new_candidates
                explicit["raw_corridor_membership"] += ra["corridor_idx"] != rb["corridor_idx"]
                for flag in flags:
                    values = [c[flag] for c in rb["candidates"]]
                    flags[flag].update(str(v).lower() for v in values)
                    if any(values):
                        checks["frames_with_" + flag] += 1
                        if len(flags_true_examples[flag]) < 5:
                            flags_true_examples[flag].append(ident)
                for field, old, new in numeric_pairs(ra, rb):
                    numeric["common_numeric_values_compared"] += 1
                    if old != new:
                        numeric["common_numeric_values_changed"] += 1
                        numeric["range_values_changed" if field in RANGE_FIELDS else "other_values_changed"] += 1
                wall = rb["track"]["wall_drift"]
                if not math.isfinite(wall):
                    raise ValueError("non-finite wall drift")
                checks["finite_wall_drift_frames"] += wall < 1e9
                for section, key in (("health", "monitored_range"), ("health", "clear_distance"), ("result", "clear_distance")):
                    old = sa["health"][key] if section == "health" else sa[key]
                    new = sb["health"][key] if section == "health" else sb[key]
                    expected = round(max(0.0, min(old, wall)), 1)
                    checks[section + "." + key + "_formula_checked"] += 1
                    if new != expected:
                        checks[section + "." + key + "_formula_mismatch"] += 1
                        unexpected.append(dict(frame=ident, formula=section + "." + key, baseline=old, candidate=new, expected=expected, wall_drift=wall))
                    if old != new:
                        datasets[dataset][section + "." + key + "_changed_frames"] += 1
                        reductions[section + "." + key].append(old - new)
                        checks[section + "." + key + "_increased_frames"] += new > old
                for section in ("track", "health"):
                    found = sb[section].get("wall_drift", None)
                    expected = round(wall, 1) if wall < 1e9 else None
                    if found != expected:
                        checks[section + "_wall_metadata_mismatch"] += 1
                if sa["clear_distance"] != sb["clear_distance"] or sa["health"]["monitored_range"] != sb["health"]["monitored_range"]:
                    if len(cap_examples[dataset]) < 3:
                        cap_examples[dataset].append(dict(frame=ident, wall_drift=wall,
                            monitored=[sa["health"]["monitored_range"], sb["health"]["monitored_range"]],
                            clear=[sa["clear_distance"], sb["clear_distance"]], obstacle=[sa["obstacle"], sb["obstacle"]],
                            warning=[sa["warning"], sb["warning"]], nearest=[sa["nearest_distance"], sb["nearest_distance"]],
                            candidates=[sa["n_candidates"], sb["n_candidates"]],
                            corridor_membership_unchanged=ra["corridor_idx"] == rb["corridor_idx"],
                            track_geometry_unchanged=old_track == new_track,
                            detections_unchanged=sa["detections"] == sb["detections"], warnings_unchanged=sa["warnings"] == sb["warnings"]))
    if checks["frames"] != 18329 or datasets["SetF"]["frames"] != 3060:
        raise ValueError("incomplete H3 comparison")
    if checks["frames"] != generic["counts"]["frames"]:
        raise ValueError("generic and explanatory comparator coverage differ")
    for key in GROUPS:
        if group_stats[key]["frames"] != generic["groups"].get(key, {}).get("frames", 0) or group_stats[key]["changes"] != generic["groups"].get(key, {}).get("field_changes", 0):
            raise ValueError("generic and explanatory field counts differ: " + key)
    sf = load(diff / "setF_report_changes.json")
    sf_fields = Counter()
    for change in sf["changes"]:
        sf_fields[re.sub(r"\[\d+\]", "[]", change["field"])] += 1
    report = dict(schema="resense-h3-explained-frame-diff-v1", controls=generic["controls"],
        groups=group_stats, categories=dict(categories), fields=dict(fields),
        datasets={k: dict(v) for k, v in datasets.items()}, exact_checks=dict(checks),
        changed_frames_by_explicit_result_group=dict(explicit),
        common_captured_raw_numeric_values={k: numeric[k] for k in ("common_numeric_values_compared", "common_numeric_values_changed", "range_values_changed", "other_values_changed")},
        added_cluster_flags={k: dict(v) for k, v in flags.items()}, added_cluster_flag_true_examples=flags_true_examples,
        range_reductions={k: dict(frames=len(v), minimum=min(v), maximum=max(v), median=statistics.median(v)) for k, v in reductions.items()},
        cap_examples=dict(cap_examples), other_or_unexplained_changes=unexpected,
        setF_scoring_report_changed_fields=dict(sf_fields),
        arithmetic_scope="Exact comparison covers the captured preexisting raw numeric result fields, including candidate descriptors and point indices. Health/mount may already be rounded inside the detector. This is not a claim that every internal intermediate, cloud array, or arithmetic operation is bit-identical.",
        causal_scope="The wall-drift min-cap equation is checked independently on every frame for monitored range and both health/result clear distance. All other changed fields remain listed; new cut/spared flags are measured metadata and are not assumed false.")
    write(out / "explained_frames.json", report)
    lines = ["# H3 full-frame explanation", "", f"Measured candidate: `{generic['controls']['candidate_commit']}`", f"Same-runtime sealed control: `{generic['controls']['baseline_commit']}`", "",
             "Compared 18,329 frames, including every one of the 3,060 Set F frames. No numeric tolerance was used.", "", "| Result field group | Changed frames | Changed leaf/schema entries |", "|---|---:|---:|"]
    lines += [f"| {k} | {v['frames']} | {v['changes']} |" for k, v in group_stats.items()]
    lines += ["", "## Preexisting output checks", "", *[f"- `{k}`: **{v} changed frames**." for k, v in explicit.items()], "", "## Interpretation", "",
        "- `explained_frames.json` retains every changed field's counts/examples, per-dataset range counts and cap traces. Additive raw `wall_drift`, `cut` and `spared` metadata is counted separately from preexisting output changes.",
        f"- Independent min-cap equation checks: {checks['frames']} frames per range field. Mismatches/unclassified changes: **{len(unexpected)}**.",
        f"- Set F scoring/placement field changes: `{json.dumps(dict(sf_fields), sort_keys=True)}`.",
        "- " + report["arithmetic_scope"], "- " + report["causal_scope"], "", "Complete raw and serialized changes remain in the external generic `changes.jsonl`, including raw corridor membership hashes. Only the explicitly registered timing telemetry is excluded; its complete audit is retained separately."]
    (out / "EXPLANATION.md").write_bytes(("\n".join(lines) + "\n").encode())
    print(json.dumps(dict(groups=group_stats, explicit=dict(explicit), checks=dict(checks), numeric=dict(numeric), flags={k: dict(v) for k, v in flags.items()}, other_changes=len(unexpected), setF_fields=dict(sf_fields)), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "candidate", "diff", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    analyze(args.baseline, args.candidate, args.diff, args.out)
