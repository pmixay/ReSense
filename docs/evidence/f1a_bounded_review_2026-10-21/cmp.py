#!/usr/bin/env python3
"""Reviewer's per-frame comparison (own code): control JSON vs candidate JSON of one attack.py family.

Per scene: matched frames each side, frames lost (control matched, candidate not), gained, first matched frame and its
distance on each side, later flag. If the candidate JSON carries a trace (attack.py --trace): new-branch rejections
(candidate rejects, v1.2.0 keeps), how many are on the target, and how many violate the subset claims
(pre0 = capped top < all-returns line + margin; pre1 = 0acb18c pre-repair rule on the low-free line).
--selftest: control vs itself must be clean; one injected loss must be found.

    python cmp.py control.json cand.json [--plain cand_plain.json] [--selftest] [--show N]
"""
import argparse
import copy
import json


def first(rows):
    return next((r for r in rows if r["matched"]), None)


def spec_key(s):
    return json.dumps({k: v for k, v in s.items() if k != "trace"}, sort_keys=True)


def compare(A, B):
    res = []
    for a, b in zip(A, B):
        assert spec_key(a["spec"]) == spec_key(b["spec"]), "spec mismatch"
        lost = [r["frame"] for r, q in zip(a["rows"], b["rows"]) if r["matched"] and not q["matched"]]
        gain = [r["frame"] for r, q in zip(a["rows"], b["rows"]) if q["matched"] and not r["matched"]]
        fa, fb = first(a["rows"]), first(b["rows"])
        later = fa is not None and (fb is None or fb["frame"] > fa["frame"])
        tr = b.get("trace") or []
        new = [dict(x, frame=t["frame"]) for t in tr for x in t["new"]]
        res.append(dict(spec=a["spec"], ctrl=a["matched_frames"], cand=b["matched_frames"], lost=lost, gained=gain,
                        first_ctrl=None if fa is None else fa["dist"], first_cand=None if fb is None else fb["dist"],
                        later=later, new=new, only_ctrl=sum(t.get("only_ctrl", 0) for t in tr)))
    return res


def summary(res):
    new = [x for r in res for x in r["new"]]
    return dict(scenes=len(res), matched_ctrl=sum(r["ctrl"] for r in res), matched_cand=sum(r["cand"] for r in res),
                frames_lost=sum(len(r["lost"]) for r in res), frames_gained=sum(len(r["gained"]) for r in res),
                scenes_with_loss=sum(bool(r["lost"]) for r in res), scenes_later=sum(r["later"] for r in res),
                new_rejections=len(new), new_on_target=sum(x["target"] for x in new),
                frames_with_new=len({(i, x["frame"]) for i, r in enumerate(res) for x in r["new"]}),
                scenes_with_new=sum(bool(r["new"]) for r in res),
                not_pre0=sum(not x["pre0"] for x in new), not_pre1=sum(not x["pre1"] for x in new),
                ctrl_rejects_cand_keeps=sum(r["only_ctrl"] for r in res))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("control")
    ap.add_argument("cand")
    ap.add_argument("--plain", help="untraced candidate run: must equal the traced one (matched + any_gauge)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--show", type=int, default=40)
    a = ap.parse_args()
    A = json.load(open(a.control))["results"]
    B = json.load(open(a.cand))["results"]
    if a.selftest:
        s0 = summary(compare(A, A))
        assert s0["frames_lost"] == 0 and s0["frames_gained"] == 0 and s0["scenes_later"] == 0, s0
        bad = copy.deepcopy(A)
        i = next((i for i, r in enumerate(bad) if r["matched_frames"]), None)
        if i is not None:
            k = first(bad[i]["rows"])["frame"]
            bad[i]["rows"][k]["matched"] = False
            s1 = summary(compare(A, bad))
            assert s1["frames_lost"] == 1 and s1["scenes_later"] == 1, s1
            print("selftest PASS (self clean, injected loss found, marked later)")
        else:
            print("selftest: self clean; no matched frame to inject")
    if a.plain:
        P = json.load(open(a.plain))["results"]
        neq = sum(1 for p, b in zip(P, B) for x, y in zip(p["rows"], b["rows"])
                  if x["matched"] != y["matched"] or x["any_gauge"] != y["any_gauge"])
        print(f"traced vs plain: {neq} differing frames of {sum(len(b['rows']) for b in B)}")
    res = compare(A, B)
    shown = 0
    for r in res:
        if (r["lost"] or r["gained"] or r["later"] or any(x["target"] for x in r["new"])) and shown < a.show:
            s = {k: v for k, v in r["spec"].items() if k not in ("trace",)}
            tgt = [x for x in r["new"] if x["target"]]
            print(f"{json.dumps(s)}\n   ctrl {r['ctrl']} cand {r['cand']} lost {r['lost']} gained {r['gained']} "
                  f"first {r['first_ctrl']} -> {r['first_cand']}{'  LATER' if r['later'] else ''}; "
                  f"new-branch rejections {len(r['new'])} (target {len(tgt)})")
            for x in tgt[:3]:
                print("     ", json.dumps(x))
            shown += 1
    print(json.dumps(summary(res)))


if __name__ == "__main__":
    main()
