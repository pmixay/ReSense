#!/usr/bin/env python3
"""Compact X3 tables for 1.1.0 against the Linux 707ea9c control (PROTOCOL §B.3).

    make_x3_report.py <control battery.json> <1.1.0 battery.json> <out dir>

Writes battery_table_1.1.0.json (per variant and recording, same layout as the v1.0.0
battery_table.json), comparison_rows.json (every directional acceptance row of the driver, failing
rows first), judge_rows_1.1.0.json (the historical v1.0.0 judge figures recomputed for 1.1.0, for
information only) and x3_tables.md (per-variant table with deltas, per-object table, P2 table).
"""
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location("rb", ROOT / "scripts/robustness_battery.py")
rb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rb)
NAMES = {"nominal": "nominal", "pitch_p2": "pitch +2°", "pitch_m2": "pitch −2°", "roll_p2": "roll +2°",
         "hz5": "5 Hz", "drop30_s1": "dropout 30%, seed 1", "drop30_s2": "dropout 30%, seed 2",
         "drop30_s3": "dropout 30%, seed 3", "drop30_judge7": "dropout 30%, judge seed 7", "dedup": "dedup"}
SQ, OB, RS, SO = ("squareT_platform_squareT_switch", "doubleT_obstacle", "roundT_squareT_pressureGate_squareT",
                  "cloud_with_fake_obj")


def compact(m):
    out = {k: m[k] for k in ("frames", "stop_frames", "stop_episodes")}
    if "objects" in m:
        out.update({k: m[k] for k in ("outside_false_stop_frames", "outside_false_stop_episodes",
                                      "unmatched_stop_frames", "unmatched_stop_episodes")})
        out["inside_matched_stop_rows"] = sum(o["inside_stop_rows"] for o in m["objects"].values())
        out["inside_visible_rows"] = sum(o["inside_visible_rows"] for o in m["objects"].values())
    return out


def d(c, b):
    return f"{c}" if c == b else f"{c} ({c - b:+d})"


def main(ctrl_path, cand_path, out_dir):
    ctrl, cand = (json.loads(Path(p).read_text()) for p in (ctrl_path, cand_path))
    out = Path(out_dir)
    table = [{"variant": v, **{b: compact(cand["entries"][f"{b}/{v}"]["metrics"]) for b in rb.BAGS}}
             for v in rb.VARIANTS]
    (out / "battery_table_1.1.0.json").write_text(json.dumps(table, indent=2) + "\n")
    rows = [dict(r, case=case) for case, rs in cand["comparison"]["cases"].items() for r in rs]
    rows.sort(key=lambda r: (r["passed"], -r["worse_by"]))
    (out / "comparison_rows.json").write_text(json.dumps(
        {"passed": cand["comparison"]["passed"], "status": cand["status"], "rows": rows}, indent=1) + "\n")
    judge = rb.judge_comparison(cand["entries"])
    (out / "judge_rows_1.1.0.json").write_text(json.dumps(
        {"note": "historical v1.0.0 judge figures, absolute ±1; information for 1.1.0, not acceptance", **judge},
        indent=1) + "\n")

    md = ["| variant | squareT false episodes (STOP frames) | obstacle STOP / processed | roundT-squareT false episodes "
          "| Set O inside matched / visible rows | Set O outside false frames / episodes | Set O unmatched frames / episodes |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    for v in rb.VARIANTS:
        c = {b: compact(cand["entries"][f"{b}/{v}"]["metrics"]) for b in rb.BAGS}
        r = {b: compact(ctrl["entries"][f"{b}/{v}"]["metrics"]) for b in rb.BAGS}
        md.append(f"| {NAMES[v]} | {d(c[SQ]['stop_episodes'], r[SQ]['stop_episodes'])} "
                  f"({d(c[SQ]['stop_frames'], r[SQ]['stop_frames'])}) "
                  f"| {d(c[OB]['stop_frames'], r[OB]['stop_frames'])}/{c[OB]['frames']} "
                  f"| {d(c[RS]['stop_episodes'], r[RS]['stop_episodes'])} "
                  f"| {d(c[SO]['inside_matched_stop_rows'], r[SO]['inside_matched_stop_rows'])}/{c[SO]['inside_visible_rows']} "
                  f"| {d(c[SO]['outside_false_stop_frames'], r[SO]['outside_false_stop_frames'])} / "
                  f"{d(c[SO]['outside_false_stop_episodes'], r[SO]['outside_false_stop_episodes'])} "
                  f"| {d(c[SO]['unmatched_stop_frames'], r[SO]['unmatched_stop_frames'])} / "
                  f"{d(c[SO]['unmatched_stop_episodes'], r[SO]['unmatched_stop_episodes'])} |")
    md += ["", "Per object, nominal (inside matched STOP rows / inside visible; first STOP m), control → 1.1.0:", "",
           "| recording | object | intent | control | 1.1.0 |", "|---|---|---|---|---|"]
    for b in (OB, SO):
        oc, ob = (e["entries"][f"{b}/nominal"]["metrics"]["objects"] for e in (cand, ctrl))
        for name in ob:
            x, y = ob[name], oc[name]
            intent = "inside" if x["in_gauge"] else "outside"
            fmt = (lambda o: f"{o['inside_stop_rows']}/{o['inside_visible_rows']}; {o['first_stop_m']}") if x["in_gauge"] \
                else (lambda o: f"outside STOP rows {o['outside_stop_rows']}, episodes {o['outside_stop_episodes']}")
            md.append(f"| {b} | {name} | {intent} | {fmt(x)} | {fmt(y)} |")
    failing = [r for r in rows if not r["passed"]]
    md += ["", f"Directional acceptance rows: **{len(rows)}**, failing **{len(failing)}**; status **{cand['status']}**."]
    for r in failing:
        md.append(f"- FAIL {r['case']} {r['metric']}: {r['baseline']} → {r['current']} (worse by {r['worse_by']}, "
                  f"tolerance {r['tolerance']})")
    (out / "x3_tables.md").write_text("\n".join(md) + "\n")
    print(cand["status"], "rows", len(rows), "failing", len(failing))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
