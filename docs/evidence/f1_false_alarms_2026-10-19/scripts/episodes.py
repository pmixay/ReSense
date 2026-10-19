#!/usr/bin/env python3
"""STOP episodes of replay.py outputs (``x.decision``, the node's rule): a run of consecutive STOP frames.
Per episode: onset frame, length, the onset frame's reporting detections (kind, distance, lateral, size,
low-cluster top / rail lines when recorded); low-kind = a ``kind == "low"`` detection on the onset frame
(``low_any``: on any frame of the episode). Also decision counts and, with a second run, per-frame
decision transitions.

    episodes.py RUN.jsonl [--against BASE.jsonl] [--json OUT]
"""
import argparse
import json
from collections import Counter


def load(path):
    return [json.loads(line) for line in open(path, encoding="utf-8")]


def episodes(rows):
    eps, cur = [], None
    for r in rows:
        stop = r["x"]["decision"] == "STOP"
        if stop and cur is None:
            cur = {"onset": r["frame"], "frames": [r["frame"]], "rows": [r]}
        elif stop:
            cur["frames"].append(r["frame"])
            cur["rows"].append(r)
        elif cur is not None:
            eps.append(cur)
            cur = None
    if cur is not None:
        eps.append(cur)
    out = []
    for e in eps:
        r0 = e["rows"][0]
        dets = [{"id": d["id"], "kind": d["kind"], "d": d["distance"], "lat": d["lateral"], "size": d["size"],
                 "reason": d["reason"], "hmin": d["height_min"]} for d in r0["detections"]]
        low = r0["x"].get("low", [])
        out.append({"onset": e["onset"], "frame_id": r0.get("frame_id"), "n": len(e["frames"]),
                    "last": e["frames"][-1], "dets": dets,
                    "low_onset": any(d["kind"] == "low" for d in r0["detections"]),
                    "low_any": any(d["kind"] == "low" for rr in e["rows"] for d in rr["detections"]),
                    "low_trace": [x for x in low if x.get("zone") == "gauge"],
                    "rail_slabs": r0["x"].get("rail_slabs"), "rail_score": r0["x"].get("rail_score"),
                    "ego": r0["x"].get("ego"),
                    "dist": [min((d["distance"] for d in rr["detections"]), default=None) for rr in e["rows"]][:1]
                    + [min((d["distance"] for d in e["rows"][-1]["detections"]), default=None)]})
    return out


def summary(rows):
    dec = Counter(r["x"]["decision"] for r in rows)
    eps = episodes(rows)
    events = {d["id"] for r in rows if r["x"]["decision"] == "STOP" for d in r["detections"]}
    return {"frames": len(rows), "decisions": dict(dec), "stop_frames": dec.get("STOP", 0),
            "stop_episodes": len(eps), "stop_events": len(events),
            "low_onset_episodes": sum(e["low_onset"] for e in eps), "low_any_episodes": sum(e["low_any"] for e in eps),
            "episodes": eps}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run")
    ap.add_argument("--against")
    ap.add_argument("--json")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    rows = load(a.run)
    s = summary(rows)
    if a.against:
        base = load(a.against)
        assert len(base) == len(rows)
        tr = Counter(f'{b["x"]["decision"]}->{r["x"]["decision"]}' for b, r in zip(base, rows)
                     if b["x"]["decision"] != r["x"]["decision"])
        s["transitions"] = dict(tr)
        bs = {b["frame"] for b in base if b["x"]["decision"] == "STOP"}
        rs = {r["frame"] for r in rows if r["x"]["decision"] == "STOP"}
        s["stop_lost"] = sorted(bs - rs)
        s["stop_new"] = sorted(rs - bs)
    if not a.quiet:
        print(json.dumps({k: v for k, v in s.items() if k != "episodes"}))
        for e in s["episodes"]:
            d = e["dets"][0] if e["dets"] else {}
            print(f'  ep {e["onset"]:>6} n={e["n"]:>3} low={int(e["low_onset"])}/{int(e["low_any"])} '
                  f'd={d.get("d")} lat={d.get("lat")} size={d.get("size")} kind={d.get("kind")!r} '
                  f'rail_slabs={e["rail_slabs"]} ego={e["ego"]} trace={e["low_trace"][:1]}')
    if a.json:
        json.dump(s, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
