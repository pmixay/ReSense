"""Derive author component results from reported gauge tracks, never all-track return lists."""
from collections import defaultdict
import json
from pathlib import Path
import sys

run, out = Path(sys.argv[1]), Path(sys.argv[2])
reference = Path(r"C:\Users\alikh\AppData\Local\Temp\opencode\resense-integration-h4-safety-20261016\run-001")
assert out.parent.is_dir()
assert not out.exists(), out
result = dict(author=True, source=json.loads((run / "results/identity.json").read_text()), groups={})
for kind in ["physical", "surface"]:
    refs = json.loads((reference / "components-sealed-all" / (kind + "-derived-summary.json")).read_text())
    prior = json.loads((reference / "components-candidate-all" / (kind + "-derived-summary.json")).read_text())
    groups, losses, changes, witnesses = defaultdict(lambda: dict(variants=0, sealed=0, prior=0, candidate=0,
                                                               lost_sealed=0, lost_prior=0)), [], [], []
    path = run / "results" / (kind + ".jsonl")
    with path.open() as f, (reference / "components-sealed-all" / (kind + ".jsonl")).open() as rf:
        for row, original, ref, old in zip(map(json.loads, f), map(json.loads, rf), refs, prior, strict=True):
            assert row["case"] == ref["case"] == old["case"]
            assert row["params"] == ref["params"] == old["params"]
            for key in ["xyz", "labels"] + (["ring"] if kind == "physical" else []):
                assert row[key] == original[key], (kind, row["case"], key)
            labels = list(ref["matched_stop_frames"])
            stops = {k: [s["frame"] for s in row["frames"] if any(
                t.get("physical_label") == int(k) and t["reported"] and t["zone"] == "gauge"
                for t in s["tracks"])] for k in labels}
            p = row["params"]
            group = ("multi" if p["multi"] else "beam" if p["beam"] else "band-" + str(p["band"])
                     if p["band"] else "top-" + str(p["top"])) if kind == "physical" else "surface"
            g = groups[group]
            g["variants"] += 1
            lost = {k: sorted(set(ref["matched_stop_frames"][k]) - set(stops[k])) for k in labels}
            lost_old = {k: sorted(set(old["matched_stop_frames"][k]) - set(stops[k])) for k in labels}
            for k in labels:
                g["sealed"] += len(ref["matched_stop_frames"][k])
                g["prior"] += len(old["matched_stop_frames"][k])
                g["candidate"] += len(stops[k])
                g["lost_sealed"] += len(lost[k])
                g["lost_prior"] += len(lost_old[k])
            item = dict(case=row["case"], params=p, ring_mode=row.get("ring_mode"), dropout=row.get("dropout"),
                        sealed=ref["matched_stop_frames"], prior=old["matched_stop_frames"], candidate=stops,
                        lost_sealed=lost, lost_prior=lost_old)
            if any(lost.values()) or any(lost_old.values()):
                losses.append(item)
            if stops != old["matched_stop_frames"]:
                changes.append(item)
            if kind == "physical" and row["case"] in [44, 45] and row["ring_mode"] == "highest" and row["dropout"] == 0:
                witnesses.append(dict(**item, xyz=row["xyz"], initial=row["frames"][0]["pre"],
                                      frames=[dict(frame=s["frame"], tracks=[t for t in s["tracks"]
                                              if t.get("physical_label") == 1]) for s in row["frames"]]))
    result["groups"][kind] = dict(summary=dict(groups), losses=losses, changes=changes, witnesses=witnesses)
out.write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps({k: v["summary"] for k, v in result["groups"].items()}, indent=2))
print(json.dumps([dict(case=w["case"], sealed=w["sealed"], prior=w["prior"], candidate=w["candidate"])
                  for w in result["groups"]["physical"]["witnesses"]], indent=2))
