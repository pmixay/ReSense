#!/usr/bin/env python3
"""Exact, complete gate frame comparison against a same-runtime sealed control.

No numeric tolerance, rounding, field selection, or frame sampling is applied.
Both normal serialized outputs and pre-serialization results are compared. Only
explicit timing telemetry is normalized; excluded differences are separately retained.
"""
import argparse
from collections import Counter, defaultdict
import copy
import itertools
import json
import math
from pathlib import Path
import re

TIMING_HEALTH = ("latency_p95_ms", "latency_basis", "latency_sample_age_frames")
LATENCY_MESSAGE = re.compile(r"^latency p95 \d+ ms over the \d+ ms budget$")
MISSING = {"__frame_diff_missing__": True}


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def normalize(result):
    r = copy.deepcopy(result)
    removed = {}
    if "timing_ms" in r:
        removed["timing_ms"] = r.pop("timing_ms")
    h = r.get("health", {})
    for k in TIMING_HEALTH:
        if k in h:
            removed["health." + k] = h.pop(k)
    messages = h.get("messages", [])
    latency = [m for m in messages if LATENCY_MESSAGE.fullmatch(m)]
    if latency:
        removed["health.latency_messages"] = latency
        h["messages"] = [m for m in messages if not LATENCY_MESSAGE.fullmatch(m)]
        # Default config has latency_affects_decision=false. Preserve all scene
        # severity and decision_level; only undo a proven latency-only WARN.
        if h.get("level") == "warn" and h.get("decision_level") == "ok":
            if h["messages"]:
                raise ValueError("cannot normalize latency-only WARN with other scene messages")
            removed["health.latency_only_level"] = h["level"]
            h["level"] = "ok"
    return r, removed


def changes(a, b, path=""):
    if a is MISSING or b is MISSING:
        yield path, a, b
    elif type(a) is not type(b):
        yield path, a, b
    elif isinstance(a, dict):
        for k in sorted(a.keys() | b.keys()):
            p = path + "." + k if path else k
            if k not in a or k not in b:
                yield p, a.get(k, MISSING), b.get(k, MISSING)
            else:
                yield from changes(a[k], b[k], p)
    elif isinstance(a, list):
        if len(a) != len(b):
            yield path + ".length", len(a), len(b)
        for i, (x, y) in enumerate(itertools.zip_longest(a, b, fillvalue=MISSING)):
            yield from changes(x, y, path + f"[{i}]")
    elif a != b:
        yield path, a, b


def field_group(path):
    parts = path.split(".")
    field = parts[1] if parts[0] in ("serialized", "raw") else parts[0]
    field = field.split("[")[0]
    if field in ("obstacle", "warning"):
        return "obstacle_warning"
    if field in ("nearest_distance", "clear_distance"):
        return "nearest_clear"
    if field in ("detections", "warnings"):
        return "detections_warnings"
    if field in ("candidates", "n_candidates"):
        return "candidates"
    if field.startswith("ego_") or field == "n_accumulated":
        return "ego_motion"
    if field in ("track", "health", "mount"):
        return field
    if path.startswith("setF_report"):
        return "setF_report_placement_and_scoring"
    return "other_result_fields"


def validate_pair(base, candidate):
    bg, cg = load(base / "gate.json"), load(candidate / "gate.json")
    bp, cp = load(base / "provenance.json"), load(candidate / "provenance.json")
    bc, cc = load(base / "completion.json"), load(candidate / "completion.json")
    if bc["commit"] != "707ea9cda051369326fb9407c42488c1033dad76" or not bc["seal_verified"]:
        raise ValueError("control is not the verified sealed 707ea9c")
    for p in (base, candidate):
        done = load(p / "completion.json")
        if not done["clean_source"] or done["gate_exit"] not in (0, 1):
            raise ValueError(f"full committed replay did not complete: {p}")
        if p == base and (done["gate_exit"] != 0 or not done["passed"]):
            raise ValueError("sealed control gate did not pass")
        if load(p / "gate.json")["code"]["uncommitted_detector_changes"] != []:
            raise ValueError(f"dirty gate: {p}")
        if load(p / "verification.json")["passed"] is not True:
            raise ValueError(f"incomplete/unverified frame evidence: {p}")
        if load(p / "gate_work/config.yaml.json")["resense"]["health"]["latency_affects_decision"]:
            raise ValueError("latency-affecting config cannot use this normalization")
    if load(base / "cache_identity.json") != load(candidate / "cache_identity.json"):
        raise ValueError("cache byte identities differ")
    bl = load(base.parent / (base.name + ".launch.json"))
    cl = load(candidate.parent / (candidate.name + ".launch.json"))
    if bl["image"] != cl["image"] or bl["image"] != "sha256:5e2659e8f8d3a7e9f64d7c269ae920badd86b8a388e48e9449dda7028b920c19":
        raise ValueError("Docker tools image differs from pinned control")
    for field in ("python", "packages", "platform", "cgroup"):
        if bp[field] != cp[field]:
            raise ValueError("runtime mismatch: " + field)
    if bp["baseline_sha256"] != cp["baseline_sha256"] or bp["baseline_sha256"] != "8d86d6d19ef00f0ece4fd0c924935887ba6f8b39dbfd7074c2f1577099029b30":
        raise ValueError("29 September shell-off baseline bytes differ")
    for field in ("RESENSE_NATIVE", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "PYTHONHASHSEED"):
        if bp["environment"][field] != cp["environment"][field]:
            raise ValueError("environment mismatch: " + field)
    for field in ("jobs", "nominal_stamps"):
        if bg["run"][field] != cg["run"][field]:
            raise ValueError("gate control mismatch: " + field)
    if bg["ride"]["chunks"] != cg["ride"]["chunks"]:
        raise ValueError("ride chunk controls differ")
    bo, co = load(base / "observer.json"), load(candidate / "observer.json")
    if bo["sha256"] != co["sha256"]:
        raise ValueError("external observer differs between runs")
    evaluation_a, evaluation_b = load(base / "evaluation_source.json"), load(candidate / "evaluation_source.json")
    changed_evaluation_files = [p for p in sorted(evaluation_a.keys() | evaluation_b.keys()) if evaluation_a.get(p) != evaluation_b.get(p)]
    return dict(baseline_commit=bc["commit"], candidate_commit=cc["commit"], image=bl["image"],
                candidate_gate_exit=cc["gate_exit"], candidate_gate_passed=cc["passed"],
                packages=bp["packages"], cache=load(base / "cache_identity.json"), observer_sha256=bo["sha256"],
                changed_evaluation_files=changed_evaluation_files)


def compare(base, candidate, out):
    controls = validate_pair(base, candidate)
    out.mkdir(exist_ok=False)
    bf = {p.name: p for p in (base / "frames").glob("*.jsonl")}
    cf = {p.name: p for p in (candidate / "frames").glob("*.jsonl")}
    if bf.keys() != cf.keys():
        raise ValueError("frame sequence inventory differs")
    groups = defaultdict(lambda: dict(field_changes=0, frames=set(), examples=[]))
    fields = defaultdict(lambda: dict(changes=0, frames=set(), max_abs_numeric_delta=0.0, examples=[]))
    counts = Counter()
    datasets = defaultdict(Counter)
    rounding_hidden = Counter()
    excluded_counts = Counter()
    with (out / "changes.jsonl").open("w", encoding="utf-8") as details, (out / "excluded_timing_changes.jsonl").open("w", encoding="utf-8") as telemetry:
        for name in sorted(bf):
            with bf[name].open(encoding="utf-8") as left, cf[name].open(encoding="utf-8") as right:
                for n, (x, y) in enumerate(itertools.zip_longest(left, right)):
                    if x is None or y is None:
                        raise ValueError(f"frame count mismatch: {name}:{n}")
                    a, b = json.loads(x), json.loads(y)
                    if a["key"] != b["key"]:
                        raise ValueError(f"frame identity mismatch: {name}:{n}")
                    ident = name + ":" + str(n)
                    dataset = "SetF" if name.startswith("setF_") else a["key"]["recording"]
                    da, db, ea, eb = {}, {}, {}, {}
                    for representation in ("serialized", "raw"):
                        da[representation], ea[representation] = normalize(a[representation])
                        db[representation], eb[representation] = normalize(b[representation])
                    diff = list(changes(da, db))
                    excluded = list(changes(ea, eb))
                    counts["frames"] += 1
                    datasets[dataset]["frames"] += 1
                    if diff:
                        counts["changed_frames"] += 1
                        datasets[dataset]["changed_frames"] += 1
                        details.write(json.dumps(dict(frame=ident, key=a["key"], changes=[dict(field=p, baseline=v, candidate=w) for p, v, w in diff])) + "\n")
                    if excluded:
                        counts["timing_changed_frames"] += 1
                        telemetry.write(json.dumps(dict(frame=ident, changes=[dict(field=p, baseline=v, candidate=w) for p, v, w in excluded])) + "\n")
                        for p, _, _ in excluded:
                            excluded_counts[re.sub(r"\[\d+\]", "[]", p)] += 1
                    raw_groups, serialized_groups = set(), set()
                    for p, v, w in diff:
                        group = field_group(p)
                        (raw_groups if p.startswith("raw.") else serialized_groups).add(group)
                        key = re.sub(r"\[\d+\]", "[]", p)
                        record = dict(frame=ident, field=p, baseline=v, candidate=w)
                        for entry in (groups[group], fields[key]):
                            entry["field_changes" if "field_changes" in entry else "changes"] += 1
                            entry["frames"].add(ident)
                            if len(entry["examples"]) < 5:
                                entry["examples"].append(record)
                        if type(v) in (int, float) and type(w) in (int, float) and math.isfinite(v) and math.isfinite(w):
                            fields[key]["max_abs_numeric_delta"] = max(fields[key]["max_abs_numeric_delta"], abs(w - v))
                    for group in raw_groups - serialized_groups:
                        rounding_hidden[group] += 1
    for data in (groups, fields):
        for entry in data.values():
            entry["frames"] = len(entry["frames"])
    # Compare every standard Set F scoring/placement row as well as full frame captures.
    sa = load(base / "gate_work/setF_straight.json")["sequences"]
    sb = load(candidate / "gate_work/setF_straight.json")["sequences"]
    sf_changes = []
    sf_rows = 0
    if len(sa) != len(sb):
        raise ValueError("Set F sequence count differs")
    for i, (a, b) in enumerate(zip(sa, sb)):
        if len(a["rows"]) != len(b["rows"]):
            raise ValueError("Set F scoring frame count differs")
        sf_rows += len(a["rows"])
        for p, v, w in changes(a, b, f"sequences[{i}]"):
            sf_changes.append(dict(field=p, baseline=v, candidate=w))
    if sf_rows != 3060:
        raise ValueError("Set F comparison omitted frames")
    write(out / "setF_report_changes.json", dict(rows_compared=sf_rows, changes=sf_changes))
    report = dict(schema="resense-same-runtime-full-frame-diff-v1", controls=controls, counts=dict(counts),
        datasets={k: dict(v) for k, v in datasets.items()}, groups=dict(groups), fields=dict(fields),
        raw_group_changes_not_visible_in_serialized_frame=dict(rounding_hidden),
        setF_scoring_rows_compared=sf_rows, setF_report_field_changes=len(sf_changes),
        exact_comparison=True, numeric_tolerance=None,
        excluded_telemetry_fields=["timing_ms", *["health." + k for k in TIMING_HEALTH],
            "health.messages entries matching " + LATENCY_MESSAGE.pattern,
            "health.level=warn only when latency message exists, decision_level=ok and no scene messages"],
        excluded_field_change_counts=dict(excluded_counts),
        interpretation={
            "range": "Monitored/clear range and track.axis_valid changes are retained. The integration plan intends an axis-supported range cap; review counted examples before attributing any individual change to it.",
            "placement": "Legacy Set F placement depends on detector track fits. GT, injected point counts and scoring row changes are reported separately; changed input placement is not automatically a candidate gain.",
            "rounding": "serialized is exact FrameResult.to_dict(); raw retains unrounded scalar/array/dataclass result fields and full candidate descriptors. Health/mount may already be rounded by the detector. xyz is not a result field serialized by the application; corridor membership is retained as dtype/shape/SHA-256.",
            "metadata": "Raw-only changes can also be additive unreported fields, not just rounding. Inspect field names/examples and source before assigning a cause.",
            "timing": "Shared Docker CPU performance is informational only; all excluded differences remain in excluded_timing_changes.jsonl."})
    write(out / "summary.json", report)
    lines = ["# Same-runtime full-frame comparison", "", f"Control: `{controls['baseline_commit']}`", f"Candidate: `{controls['candidate_commit']}`", "",
             f"Compared **{counts['frames']} frames**, including **{sf_rows} Set F rows**; **{counts['changed_frames']} frames** changed outside explicit timing telemetry.", "", "| Field group | Changed frames | Leaf changes |", "|---|---:|---:|"]
    for k, v in sorted(groups.items()):
        lines.append(f"| {k} | {v['frames']} | {v['field_changes']} |")
    lines += ["", "Exact field counts and examples: `summary.json`. Every changed field/value: `changes.jsonl`. Set F placement/scoring: `setF_report_changes.json`. Excluded timing audit: `excluded_timing_changes.jsonl`.", "", "## Interpretation", *["- " + s for s in report["interpretation"].values()]]
    (out / "SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(dict(counts=report["counts"], datasets=report["datasets"], groups={k: {f: v[f] for f in ("frames", "field_changes")} for k, v in groups.items()}), indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    compare(args.baseline, args.candidate, args.out)
