"""Exact STOP-frame/center comparison of author replays with independent sealed plain."""
import argparse
import hashlib
import json
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("run", type=Path)
ap.add_argument("out", type=Path)
ap.add_argument("--sealed", type=Path, default=Path(
    r"C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-h4-safety-20261016\run-001\replay-sealed-all"))
a = ap.parse_args()
assert a.out.parent.is_dir()
assert not a.out.exists(), a.out
result = dict(author=True, run=str(a.run), reference=str(a.sealed), pieces={})
for piece in ["ride_1", "ride_3"]:
    def rows(root):
        with (root / (piece + ".jsonl")).open() as f:
            return {r["frame_id"]: r for r in map(json.loads, f)}
    ref, got = rows(a.sealed), rows(a.run / "results")
    assert ref.keys() == got.keys()
    assert all(ref[k]["input"] == got[k]["input"] and ref[k]["stamp"] == got[k]["stamp"] for k in ref)
    stop = lambda data: {k for k, r in data.items() if r["serialized"]["obstacle"]}
    rs, gs = stop(ref), stop(got)
    extra = sorted(gs - rs)
    witnesses = []
    for key in extra:
        rr, gg = ref[key], got[key]
        pairs = []
        for det in gg["serialized"]["detections"]:
            warnings = [w for w in rr["serialized"]["warnings"] if w["center"] == det["center"]]
            pairs.append(dict(detection=det, exact_warning_matches=warnings))
        ids = {p["detection"]["id"] for p in pairs}
        centers = {tuple(p["detection"]["center"]) for p in pairs}
        relevant = lambda c: tuple(round(float(x), 2) for x in c["centroid"]) in centers
        witnesses.append(dict(frame=key, pairs=pairs, observer=gg["observer"], spares=gg["spares"],
                              candidates=[c for c in gg["candidates"] if relevant(c)],
                              tracks=[t for t in gg["tracks"] if t["id"] in ids]))
    result["pieces"][piece] = dict(frames=len(ref), sealed_stop=len(rs), candidate_stop=len(gs),
                                  extra_stop_frames=extra, lost_stop_frames=sorted(rs - gs), witnesses=witnesses)
result["identity"] = json.loads((a.run / "results/identity.json").read_text())
result["raw_sha256"] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                        for root in [a.run / "results", a.sealed] for p in root.glob("ride_*.jsonl")}
a.out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({p: {k: v for k, v in d.items() if k != "witnesses"} for p, d in result["pieces"].items()}, indent=2))
