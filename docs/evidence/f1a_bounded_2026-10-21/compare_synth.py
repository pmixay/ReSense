#!/usr/bin/env python3
"""Per-frame comparison of a synthetic family, control (v1.2.0) vs candidate (PROTOCOL A1/A3).

For every scene (specs must be equal apart from the trace flag): matched frames on each side, frames lost
(control matched, candidate not), frames gained, the first matched frame on each side and whether the candidate's
comes later. Exit 1 if any frame is lost or any first STOP is later; 0 otherwise.
``--selftest``: positive control -- flips one matched frame of the candidate in memory (must be reported as lost and,
if it was the first, as later) and compares the control with itself (must be clean).

    python compare_synth.py <control json> <candidate json> [--selftest] [--json out.json]
"""
import argparse
import copy
import json
import sys


def first(rows):
    return next((r["frame"] for r in rows if r["matched"]), None)


def compare(ctrl, cand):
    out, lost_total, gain_total, later = [], 0, 0, 0
    assert len(ctrl) == len(cand), "different scene counts"
    for a, b in zip(ctrl, cand):
        sa = {k: v for k, v in a["spec"].items() if k not in ("trace", "neutralize")}
        sb = {k: v for k, v in b["spec"].items() if k not in ("trace", "neutralize")}
        assert sa == sb, (sa, sb)
        assert len(a["rows"]) == len(b["rows"])
        lost = [r["frame"] for r, q in zip(a["rows"], b["rows"]) if r["matched"] and not q["matched"]]
        gain = [r["frame"] for r, q in zip(a["rows"], b["rows"]) if q["matched"] and not r["matched"]]
        fa, fb = first(a["rows"]), first(b["rows"])
        is_later = fa is not None and (fb is None or fb > fa)
        lost_total += len(lost)
        gain_total += len(gain)
        later += is_later
        out.append(dict(spec=sa, ctrl=a["matched_frames"], cand=b["matched_frames"], lost=lost, gained=gain,
                        first_ctrl=fa, first_cand=fb, later=is_later,
                        first_dist_ctrl=None if fa is None else a["rows"][fa]["dist"],
                        first_dist_cand=None if fb is None else b["rows"][fb]["dist"]))
    gauge = lambda res: sum(bool(r["any_gauge"]) for x in res for r in x["rows"])  # noqa: E731
    summary = dict(scenes=len(out), frames_any_gauge_ctrl=gauge(ctrl), frames_any_gauge_cand=gauge(cand), matched_ctrl=sum(r["ctrl"] for r in out), matched_cand=sum(r["cand"] for r in out),
                   frames_lost=lost_total, frames_gained=gain_total, scenes_later=later,
                   scenes_with_loss=sum(bool(r["lost"]) for r in out),
                   scenes_with_gain=sum(bool(r["gained"]) for r in out))
    return summary, out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("control")
    ap.add_argument("candidate")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    ctrl = json.load(open(a.control))["results"]
    cand = json.load(open(a.candidate))["results"]
    if a.selftest:
        s0, _ = compare(ctrl, ctrl)
        assert s0["frames_lost"] == 0 and s0["frames_gained"] == 0 and s0["scenes_later"] == 0, s0
        bad = copy.deepcopy(cand)
        i = next((i for i, r in enumerate(bad) if r["matched_frames"]), None)
        if i is None:
            print("selftest: self-comparison clean; no matched frame to inject (family without targets)")
        else:
            k = first(bad[i]["rows"])
            bad[i]["rows"][k]["matched"] = False
            bad[i]["matched_frames"] -= 1
            s1, rows = compare(cand, bad)
            assert s1["frames_lost"] == 1 and rows[i]["lost"] == [k] and rows[i]["later"], s1
            print("selftest PASS (self-comparison clean; one injected loss found and marked later)")
    summary, rows = compare(ctrl, cand)
    for r in rows:
        if r["lost"] or r["gained"] or r["later"]:
            print(f"{r['spec']}: ctrl {r['ctrl']} cand {r['cand']} lost {r['lost']} gained {r['gained']} "
                  f"first {r['first_dist_ctrl']} -> {r['first_dist_cand']}{'  LATER' if r['later'] else ''}")
    print(json.dumps(summary))
    if a.json:
        json.dump(dict(summary=summary, rows=rows), open(a.json, "w"), indent=1)
    return 1 if summary["frames_lost"] or summary["scenes_later"] else 0


if __name__ == "__main__":
    sys.exit(main())
