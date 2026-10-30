#!/usr/bin/env python3
"""PROTOCOL B1/B2/B4/C1/D3: control vs candidate regression-gate runs.

1. Every leaf of the two gate result JSONs outside latency / run metadata, side by side (changed leaves listed).
2. Every per-frame JSONL of the two work directories (all recordings, ride pieces, set O) through compare_rows:
   rows changed, STOP (``obstacle``) rows lost / added per file.
3. Set O per object: STOP frames (cand >= ctrl) and first STOP frame (not later); doubleT_obstacle labelled hits.
Positive control (--selftest): a perturbed copy of the candidate result (one set O object's STOP frames - 1) must
be flagged. Exit 1 on any STOP row lost, any set O / labelled regression.

    python compare_gate.py <ctrl.json> <cand.json> <ctrl work> <cand work> [--selftest] [--json out.json]
"""
import copy
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compare_rows import compare, load  # noqa: E402

SKIP_TOP = {"created", "code", "config", "native", "run", "latency_ms", "gate", "schema"}


def leaves(x, p=""):
    if isinstance(x, dict):
        for k, v in x.items():
            if p == "" and k in SKIP_TOP:
                continue
            if "latency" in k or k.endswith("_ms") or k == "wall_s":
                continue
            yield from leaves(v, f"{p}/{k}")
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from leaves(v, f"{p}[{i}]")
    else:
        yield p, x


def set_o_check(A, B):
    bad = []
    oa, ob = A.get("set_O", {}), B.get("set_O", {})
    objs = oa.get("objects", oa)
    objs_b = ob.get("objects", ob)
    for name, a in objs.items():
        if not isinstance(a, dict) or "stop_frames" not in a:
            continue
        b = objs_b[name]
        if b["stop_frames"] < a["stop_frames"]:
            bad.append(f"set O {name}: STOP frames {a['stop_frames']} -> {b['stop_frames']}")
        fa, fb = a.get("first_stop_frame"), b.get("first_stop_frame")
        if fa is not None and (fb is None or fb > fa):
            bad.append(f"set O {name}: first STOP frame {fa} -> {fb}")
    la = (A["recordings"]["doubleT_obstacle"].get("labelled") or {})
    lb = (B["recordings"]["doubleT_obstacle"].get("labelled") or {})
    for k, v in (la.get("per_label") or {}).items():
        if lb["per_label"][k]["hits"] < v["hits"]:
            bad.append(f"doubleT_obstacle labelled {k}: hits {v['hits']} -> {lb['per_label'][k]['hits']}")
    for k in ("fp_frames", "fp_events"):
        if k in la and lb.get(k, 0) > la[k]:
            bad.append(f"doubleT_obstacle {k}: {la[k]} -> {lb[k]}")
    return bad


def main():
    a = sys.argv[1:]
    sel = "--selftest" in a
    js = a[a.index("--json") + 1] if "--json" in a else None
    A, B = json.load(open(a[0])), json.load(open(a[1]))
    wa, wb = a[2], a[3]
    if sel:
        assert not set_o_check(A, A)
        C = copy.deepcopy(B)
        objs = C["set_O"].get("objects", C["set_O"])
        name = next(n for n, o in objs.items() if isinstance(o, dict) and o.get("stop_frames"))
        objs[name]["stop_frames"] -= 1
        assert set_o_check(B, C), "perturbed set O object not flagged"
        print(f"selftest PASS (set O perturbation of {name} flagged; self-comparison clean)")
    la, lb = dict(leaves(A)), dict(leaves(B))
    changed = {k: (la.get(k), lb.get(k)) for k in sorted(set(la) | set(lb)) if la.get(k) != lb.get(k)}
    print(f"result leaves compared {len(set(la) | set(lb))}, changed {len(changed)}")
    for k, v in changed.items():
        print(f"  {k}: {v[0]} -> {v[1]}")
    files = {}
    lost_any = False
    for f in sorted(glob.glob(os.path.join(wa, "*.jsonl"))):
        g = os.path.join(wb, os.path.basename(f))
        s = compare(load(f), load(g))
        files[os.path.basename(f)] = s
        lost_any |= bool(s["stop_lost"])
        if s["rows_changed"] or s["stop_lost"] or s["stop_added"]:
            print(f"{os.path.basename(f)}: rows {s['rows']} changed {s['rows_changed']} STOP {s['stop_ctrl']} -> "
                  f"{s['stop_cand']} lost {s['stop_lost']} added {s['stop_added']} fields {list(s['fields'])[:8]}")
    print("per-frame files compared:", len(files), "with changes:", sum(bool(s["rows_changed"]) for s in files.values()))
    bad = set_o_check(A, B)
    for b in bad:
        print("REGRESSION", b)
    if js:
        json.dump(dict(changed_leaves=changed, files=files, regressions=bad), open(js, "w"), indent=1)
    return 1 if (bad or lost_any) else 0


if __name__ == "__main__":
    sys.exit(main())
