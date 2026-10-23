#!/usr/bin/env python3
"""Per frame, per scene: GO while a target (the review's evalrows target positions, warps and scrolls applied) is in
the gauge (|lateral to the edited track| <= 0.8 m) and inside the reported clear distance and monitored range.
Lists the frames for v1.2.0 and the candidate and the frames only the candidate has.

    scene_go_frames.py <specdir> <rundir> --json out.json"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/rv/s")
import evalrows as E  # noqa: E402


def go_frames(rows, spec, lo):
    injected = spec.get("inject", {}).get("targets", [])
    out = set()
    for r in rows:
        if r["decision"] != "GO" or r["monitored"] is None:
            continue
        for name, x, y in E.targets(r["i"], r["i"] - lo, spec, injected):
            k = r["i"] - lo
            x0, y0 = E.moved(x, E.TRACK["a"] + E.TRACK["b"] * x, k, spec) if False else (x, None)
            # lateral of the target to the (edited) track: the track centre at x moves like a centre point
            xc, yc = E.moved(x, E.TRACK["a"] + E.TRACK["b"] * x, k, spec)
            lat = y - yc
            if abs(lat) <= 0.8 and x <= min(r["clear"], r["monitored"]):
                out.add((r["i"], name))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("specdir")
    ap.add_argument("rundir")
    ap.add_argument("--json", required=True)
    a = ap.parse_args()
    idx = json.loads((Path(a.specdir) / "index.json").read_text())
    res, only_cand = {}, 0
    for name, frames in idx:
        spec = json.loads((Path(a.specdir) / f"{name}.json").read_text())
        lo = int(frames.split(":")[0])
        g = {}
        for w in ("wt_v120", "wt_cand"):
            rows = [json.loads(line) for line in open(Path(a.rundir) / f"{name}__{w}.jsonl")]
            g[w] = go_frames(rows, spec, lo)
        oc = sorted(g["wt_cand"] - g["wt_v120"])
        only_cand += len(oc)
        res[name] = {"v120": len(g["wt_v120"]), "cand": len(g["wt_cand"]), "only_cand": oc}
    json.dump({"only_candidate_frames": only_cand, "scenes": res}, open(a.json, "w"), indent=1)
    print("frames only the candidate has:", only_cand, "| totals v1.2.0", sum(v["v120"] for v in res.values()),
          "cand", sum(v["cand"] for v in res.values()))
    for n, v in res.items():
        if v["only_cand"]:
            print(n, v)


if __name__ == "__main__":
    main()
