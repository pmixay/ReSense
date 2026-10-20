"""Re-score committed v5c evidence; no detector replay or acceptance-criterion changes.

Run from the repository with Python 3.12 / numpy 1.26.4:
    PYTHONPATH=. python docs/evidence/k1_k2_review_2026-10-20/audit.py > /tmp/opencode/audit.json
"""
from __future__ import annotations

import contextlib
import copy
import hashlib
import io
import json
import lzma
import runpy
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.regression_gate import compare
from scripts.robustness_battery import compare_metrics

ROOT = Path(__file__).resolve().parents[3]
EV = ROOT / "docs/evidence"
V5 = EV / "k2_v5c_2026-10-20"
DATA = V5 / "runs/data_8c2bf51"
HASHES = {}


def read(path):
    data = path.read_bytes()
    HASHES[str(path.relative_to(ROOT))] = hashlib.sha256(data).hexdigest()
    return lzma.decompress(data).decode() if path.suffix == ".xz" else data.decode()


def document(path):
    return json.loads(read(path))


def aligned(rows, expected=None):
    if expected is not None and len(rows) != expected:
        raise ValueError("incomplete recording")
    if [r["i"] for r in rows] != list(range(len(rows))):
        raise ValueError("duplicate, missing or reordered frame IDs")
    return rows


def recording(path, expected=None):
    return aligned([json.loads(line) for line in read(path).splitlines()], expected)


def differences(base, candidate):
    return {"lost": sorted(base - candidate), "gained": sorted(candidate - base)}


def gate_audit():
    baseline = document(EV / "results/regression_baseline_2026-09-29_shell_off.json")
    reports = {name: document(DATA / f"gate/gate_{name}.json") for name in ("off", "v5c15", "v5c30")}
    result = {}
    for name, report in reports.items():
        failed = [r for r in compare(baseline, report) if r["fails"]]
        assert [r["metric"] for r in failed] == report["gate"]["worse_gated"]
        assert report["gate"]["passed"] == (not failed)
        assert not report["gate"]["allow"] and not report["gate"]["missing_gated"]
        result[name] = {"strict_pass": not failed, "failures": failed,
                        "ride_episodes": report["ride"]["stop_episodes"],
                        "empty_episodes": report["five_empty"]["stop_episodes"]}
    assert not any(r["fails"] for r in compare(reports["off"], reports["off"]))
    return result


def x3_audit():
    reports = {name: document(DATA / f"x3/x3_{name}.json") for name in ("off", "B", "v5c15")}
    ref = reports["off"]
    assert len(ref["entries"]) == 40
    result = {}
    for name, report in reports.items():
        assert report["sources"] == ref["sources"] and not report["errors"]
        assert report["protocol"] == ref["protocol"]
        assert set(report["entries"]) == set(ref["entries"])
        rows = {key: compare_metrics(ref["entries"][key]["metrics"], entry["metrics"])
                for key, entry in report["entries"].items()}
        if name != "off":
            assert rows == report["comparison"]["cases"]
        failed = [{"case": key, **row} for key, values in rows.items() for row in values if not row["passed"]]
        result[name] = {"comparisons": sum(map(len, rows.values())), "failures": failed}
    assert not result["off"]["failures"]
    assert len(result["v5c15"]["failures"]) == len(result["B"]["failures"]) == 6
    # Positive control: an extra positive loss is rejected by the same comparison.
    key = "doubleT_obstacle/nominal"
    original = ref["entries"][key]["metrics"]
    planted = copy.deepcopy(original)
    planted["stop_frames"] -= 3
    assert any(not r["passed"] for r in compare_metrics(original, planted))
    result["planted_three_frame_loss_rejected"] = True
    return result


def falcon_audit():
    runs = {name: recording(DATA / f"falcon/falcon_{name}.jsonl.xz", 4443)
            for name in ("off", "v5c15", "v5c30")}
    ref = runs["off"]
    for run in runs.values():
        assert [(r["stamp"], r["bag_t"], r["topic"]) for r in run] == [
            (r["stamp"], r["bag_t"], r["topic"]) for r in ref]
    script = V5 / "scripts/score_falcon_person.py"
    read(script)
    # Execute the proposed scorer unchanged, then inspect its actual matched-frame sets.
    old_argv = sys.argv
    with tempfile.TemporaryDirectory(prefix="k2-review-", dir="/tmp/opencode") as tmp:
        path = Path(tmp) / "reference.jsonl"
        path.write_text("\n".join(json.dumps(r) for r in ref) + "\n")
        try:
            sys.argv = [str(script), str(path)]
            with contextlib.redirect_stdout(io.StringIO()):
                scope = runpy.run_path(str(script))
        finally:
            sys.argv = old_argv
    score = scope["score"]
    first, reference_hits, other = score(ref)
    assert len(reference_hits) == 1360 and first == (2972, 124.84)
    assert other == [159, 2312, 2313, 2314]
    result = {}
    for name, run in runs.items():
        first, hits, other = score(run)
        delta = differences(set(reference_hits), set(hits))
        # Independent decision-only lower bound: no STOP cannot be a retained person STOP.
        no_stop = [i for i in reference_hits if run[i]["decision"] != "STOP"]
        assert no_stop == delta["lost"]
        result[name] = {"first_by_proposed_scorer": first, "person_stop_frames": len(hits),
                        "unattributed_or_nonperson_stop_frames": other, **delta,
                        "lost_row_details": [{"i": i, "reference_nearest": ref[i]["nearest"],
                                              "candidate_decision": run[i]["decision"],
                                              "candidate_warns": run[i]["warns"]} for i in no_stop]}
    planted = copy.deepcopy(ref)
    planted[3100].update(decision="CAUTION", dets=[])
    assert score(planted)[1] == [i for i in reference_hits if i != 3100]
    reordered = list(ref)
    reordered[3100], reordered[3101] = reordered[3101], reordered[3100]
    try:
        aligned(reordered, 4443)
    except ValueError:
        pass
    else:
        raise AssertionError("review must reject reordered records")
    result["controls"] = {"self_equal": not result["off"]["lost"] and not result["off"]["gained"],
                          "planted_loss_found": True, "review_rejects_reordered_input": True}
    return result


def marker_hits(markers, run):
    """Independent implementation of the registered per_object.py matching bounds."""
    found = {}
    for row in markers:
        i = row["i"]
        for box in row["markers"]:
            if box["type"] != "LINE_LIST" or box["action"] != 0 or not box["n_points"]:
                continue
            lo, hi = box["pts_min"], box["pts_max"]
            near = -hi[1]
            if max(b - a for a, b in zip(lo, hi)) < 0.1 or not 2.5 <= near <= 250:
                continue
            item = found.setdefault(box["id"], {"visible": [], "stop": [], "first_m": None})
            item["visible"].append(i)
            if run[i]["decision"] == "STOP" and any(
                abs(d["d"] - near) <= max(3, .03 * near)
                and abs(d["c"][1] - (lo[0] + hi[0]) / 2) <= 1.5 for d in run[i]["dets"]
            ):
                item["stop"].append(i)
                if item["first_m"] is None:
                    item["first_m"] = near
    return found


def markers_audit():
    result = {}
    for bag, count in (("platform", 386), ("switch", 736), ("tunnels", 545)):
        markers = recording(EV / f"synth_markers_2026-10-19/out/markers_{bag}.jsonl.xz", count)
        runs = {name: recording(DATA / f"markers/{name}_{bag}.jsonl.xz", count)
                for name in ("off", "v5c15", "v5c30")}
        scored = {name: marker_hits(markers, run) for name, run in runs.items()}
        base = scored["off"]
        result[bag] = {}
        for name, current in scored.items():
            assert current.keys() == base.keys()
            rows = []
            for oid, item in current.items():
                old = base[oid]
                assert item["visible"] == old["visible"]
                rows.append({"object": oid, "visible": len(item["visible"]),
                             "stop_before": len(old["stop"]), "stop_after": len(item["stop"]),
                             "first_before_m": old["first_m"], "first_after_m": item["first_m"],
                             **differences(set(old["stop"]), set(item["stop"]))})
            result[bag][name] = rows
        assert not any(r["lost"] or r["gained"] for r in result[bag]["off"])
        oid = next(oid for oid, s in base.items() if s["stop"])
        frame = base[oid]["stop"][0]
        planted = copy.deepcopy(runs["off"])
        planted[frame].update(decision="GO", dets=[])
        assert frame in set(base[oid]["stop"]) - set(marker_hits(markers, planted)[oid]["stop"])
    return result


def standing_audit():
    result = {}
    for name in ("off", "B", "v5c15", "v5c30"):
        report = document(DATA / f"k1_2/{name}_S_person_150.json")
        visible = [r for r in report["rows"] if r["n_obj"] > 0]
        hits = [r["k"] for r in visible if r["hit"]]
        assert len(hits) == report["summary"]["stop_frames"]
        assert len(visible) == report["summary"]["visible_frames"] == 259
        result[name] = {"visible": len(visible), "matched_stop_rows": hits,
                        "meets_original_150_frame_minimum": len(hits) >= 150}
    assert len(result["off"]["matched_stop_rows"]) == 90
    return result


def main():
    report = {"scope": "committed historical evidence re-score, not a new detector/data run",
              "review_checkout": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "gate": gate_audit(), "x3": x3_audit(), "falcon": falcon_audit(),
              "markers": markers_audit(), "standing_150": standing_audit()}
    report["inputs_sha256"] = HASHES
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
