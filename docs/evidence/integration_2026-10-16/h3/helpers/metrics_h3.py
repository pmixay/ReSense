#!/usr/bin/env python3
"""Collect complete legacy and same-runtime metric tables using the measured evaluator."""
import argparse
import json
from pathlib import Path
import sys

from frame_diff import changes, load, write


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    args = parser.parse_args()
    repo = Path("/evalworkspace") / args.candidate.name
    sys.path[:0] = [str(repo), str(repo / "scripts")]
    import regression_gate
    candidate = load(args.candidate / "gate.json")
    summaries = {}
    for name, baseline in (("same_runtime", args.baseline / "gate.json"),
                           ("shell_off_2026_09_29", repo / "docs/evidence/results/regression_baseline_2026-09-29_shell_off.json")):
        control = load(baseline)
        rows = regression_gate.compare(control, candidate)
        summary = regression_gate.gate_summary(rows, control, str(baseline), ())
        summary.update(total_rows=len(rows), gated_rows=sum(r["gated"] for r in rows),
                       non_latency_rows=sum(not r["metric"].startswith("latency_ms.") for r in rows),
                       identical_non_latency_rows=sum(r["verdict"] == "same" for r in rows if not r["metric"].startswith("latency_ms.")),
                       changed_non_latency_rows=[r for r in rows if not r["metric"].startswith("latency_ms.") and r["verdict"] != "same"])
        write(args.analysis / ("metrics_vs_" + name + ".json"), dict(summary=summary, rows=rows))
        (args.analysis / ("metrics_vs_" + name + ".txt")).write_text(regression_gate.table(rows) + "\n")
        summaries[name] = summary
    before = load(args.baseline / "evaluation_source.json")
    after = load(args.candidate / "evaluation_source.json")
    active = ("scripts/regression_gate.py", "scripts/eval_real.py", "scripts/far_range_eval.py", "scripts/cache_io.py", "scripts/score_fake_objects.py", "docs/extended_dataset_intake.json")
    active_hashes = {p: dict(baseline=before[p], candidate=after[p], identical=before[p] == after[p]) for p in active}
    labels = {p: dict(baseline=before[p], candidate=after.get(p), identical=before[p] == after.get(p)) for p in before if p.startswith("labels/")}
    ca, cb = load(args.baseline / "gate_work/config.yaml.json"), load(args.candidate / "gate_work/config.yaml.json")
    config_changes = [dict(field=p, baseline=a, candidate=b) for p, a, b in changes(ca, cb)]
    write(args.analysis / "evaluation_and_config.json", dict(active_evaluator_and_intake=active_hashes, labels=labels,
        all_active_evaluator_and_labels_identical=all(v["identical"] for v in [*active_hashes.values(), *labels.values()]),
        canonical_config_changes=config_changes, metrics_summaries=summaries))
    print(json.dumps(dict(summaries=summaries, active_evaluator_identical=all(v["identical"] for v in active_hashes.values()), config_changes=config_changes), indent=2))


if __name__ == "__main__":
    main()
