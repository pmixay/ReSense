#!/usr/bin/env python3
"""Screen rules taken from other teams' repositories against the team's saved detector outputs.

    python scripts/screen_competitor_rules.py --out docs/evidence/results/competitor_rule_screen_2026-09-29.json

No recordings, no ROS and no detector change: it reads only what is committed under
``docs/evidence`` (the independent judgement's per-frame outputs of 28.09, the residual false STOP
inventory of the ride) and ``labels/``. Each rule is applied as a *post-filter* on the STOP
detections the sealed detector already produced, so it answers one question before a gate run is
spent on it: how many false alarms would the rule remove, and which true detections would it take
with them? A post-filter is a first-order proxy: it cannot show what a rule would change inside
the tracker (a vetoed frame would also break a track's confirmation), and it cannot see objects
the detector never reported.

The set O scoring is the independent judge's matcher (``docs/evidence/judgement_2026-09-28/scripts/
score_setO.py``: a detection matches an object when it lies within 3 m of the object's box along the
track). The screen first reproduces the published ``setO.json`` exactly and stops if it does not,
so a change to the harness cannot silently change the numbers it reports.

Rules are ported with their source thresholds unchanged; nothing here is tuned on this data.
"""
import argparse
import gzip
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
JUDGEMENT = "judgement_2026-09-28"                      # under --evidence (docs/evidence)
RESIDUAL = "results/residual_events_2026-09-28.json"
LABELS = "labels/cloud_with_fake_obj.json"

# the five organizer recordings without obstacles; doubleT_obstacle is the only real positive
EMPTY_BAGS = ("doubleT_platform", "roundT_doubleT", "roundT_pressureGate_roundT",
              "roundT_squareT_pressureGate_squareT", "squareT_platform_squareT_switch")
REAL_BAG = "doubleT_obstacle"
SET_O_BAG = "cloud_with_fake_obj"

BEAM_VERTICAL_RAD = 0.00218       # Pandar128 fine vertical spacing, 0.125 deg (docs/SENSOR.md)
MATCH_MARGIN_M = 3.0              # the judge's matcher: within 3 m of the object's box along the track


@dataclass(frozen=True)
class Rule:
    """A veto on one STOP detection (the ``detections`` entries of a per-frame result)."""
    name: str
    source: str
    veto: Callable[[dict], bool]


def _tunnelguard_shape(d: dict) -> bool:
    # EhimenNathan/tunnelguard-lct2026 core/detector.py: shape_fail = s_min > extent_min_s (40) and
    # n < extent_min_points_exempt (15) and vertical extent < extent_min_beams (1.2) beam spacings
    dist = d["distance"]
    return (dist > 40.0 and d["n_points"] < 15
            and d["size"][2] < 1.2 * BEAM_VERTICAL_RAD * dist)


def _tunnelguard_gravity(d: dict) -> bool:
    # same file: gravity_fail = s_min > gravity_min_s (60) and h_min > gravity_max_base (1.0):
    # beyond 60 m only an object standing on the floor may give STOP
    return d["distance"] > 60.0 and d["height_min"] > 1.0


RULES: Dict[str, Rule] = {r.name: r for r in (
    Rule("tunnelguard_shape", "EhimenNathan/tunnelguard-lct2026 core/detector.py", _tunnelguard_shape),
    Rule("tunnelguard_gravity", "EhimenNathan/tunnelguard-lct2026 core/detector.py", _tunnelguard_gravity),
)}


def episodes(flags: List[bool]) -> int:
    """Runs of consecutive True."""
    n, prev = 0, False
    for f in flags:
        n += f and not prev
        prev = f
    return n


def load_frames(evidence_root: Path, bag: str) -> List[dict]:
    path = evidence_root / JUDGEMENT / "raw" / "offline" / f"{bag}.jsonl.gz"
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _near(det: dict, box) -> bool:
    return box[0][0] - MATCH_MARGIN_M <= det["distance"] <= box[1][0] + MATCH_MARGIN_M


def score_set_o(frames: List[dict], labels: dict, veto: Optional[Callable[[dict], bool]] = None) -> dict:
    """The judge's set O score with the STOP detections that ``veto`` flags removed first."""
    def kept(r):
        return [d for d in r["detections"] if not (veto and veto(d))]

    stray = 0
    for r in frames:
        objs = [o for o in labels.get(f"{r['frame']:05d}", []) if o["plausible"]]
        stray += sum(1 for d in kept(r) if not any(_near(d, o["bbox"]) for o in objs))
    objects = {}
    for name, meta in labels["_meta"]["objects"].items():
        first_frame, last_frame = meta["frames"]
        stop, first = 0, None
        for r in frames[first_frame:last_frame + 1]:
            rows = [x for x in labels.get(f"{r['frame']:05d}", []) if x["name"] == name and x["plausible"]]
            if not rows:
                continue
            hit = [d for d in kept(r) if _near(d, rows[0]["bbox"])]
            if hit:
                stop += 1
                if first is None:
                    first = round(hit[0]["distance"], 1)
        objects[name] = {"in_gauge": bool(meta["in_gauge"]), "stop_frames": stop, "first_stop_m": first}
    return {"objects": objects, "stray_stop_detections": stray}


def check_reproduces_published(evidence_root: Path, labels: dict, frames: List[dict]) -> None:
    """Stop unless the harness returns the independent judge's published set O numbers."""
    pub = json.loads((evidence_root / JUDGEMENT / "setO.json").read_text(encoding="utf-8"))
    mine = score_set_o(frames, labels)
    for name, o in mine["objects"].items():
        want = pub["objects"][name]
        if (o["stop_frames"], o["first_stop_m"]) != (want["stop_frames"], want["first_stop_m"]):
            raise SystemExit(f"harness does not reproduce the published set O row {name}: "
                             f"{(o['stop_frames'], o['first_stop_m'])} != "
                             f"{(want['stop_frames'], want['first_stop_m'])}")
    if mine["stray_stop_detections"] != pub["stop_detections_near_no_object"]:
        raise SystemExit("harness does not reproduce the published stray STOP count")


def screen_empty(bags: Dict[str, List[dict]], veto: Optional[Callable[[dict], bool]]) -> dict:
    """Every STOP on a recording without obstacles is a false alarm."""
    frames = episodes_n = dets = vetoed = 0
    for rows in bags.values():
        flags = [any(not (veto and veto(d)) for d in r["detections"]) for r in rows]
        frames += sum(flags)
        episodes_n += episodes(flags)
        for r in rows:
            for d in r["detections"]:
                dets += 1
                vetoed += bool(veto and veto(d))
    return {"stop_frames": frames, "stop_episodes": episodes_n, "detections": dets, "vetoed": vetoed}


def screen_real(rows: List[dict], veto: Optional[Callable[[dict], bool]]) -> dict:
    flags = [any(not (veto and veto(d)) for d in r["detections"]) for r in rows]
    return {"stop_frames": sum(flags), "first_stop_frame": flags.index(True) if any(flags) else None}


def screen_ride_events(events: List[dict], veto: Callable[[dict], bool]) -> dict:
    """The ride's residual false events (the ``fresh_stop_v1`` capture): events every record of
    which the rule vetoes disappear; the others stay."""
    records = removed_records = removed_events = 0
    for e in events:
        dets = [r["candidate_detection"] for r in e["candidate_stop_records"]]
        records += len(dets)
        flags = [veto(d) for d in dets]
        removed_records += sum(flags)
        removed_events += bool(dets) and all(flags)
    return {"events": len(events), "records": records,
            "events_removed": removed_events, "records_removed": removed_records}


def promotion_screen(evidence_root: Path, labels: dict, bags: Dict[str, List[dict]],
                     set_o: List[dict], reasons=("beyond_axis", "beyond_height_ref"),
                     lateral_max: float = 0.6) -> dict:
    """What promoting advisory (CAUTION) detections of the given reasons to STOP would do.

    An uncertainty-aware gauge (TunnelGuard ``core/gauge.py``) lets an object deep inside the
    envelope give STOP beyond the trusted axis range. The advisories that carry the demotion
    reason and lie near the centre line are what such a rule would promote: on the empty
    recordings each one is a false alarm, on set O the ones matched to an in-gauge object are gains.
    """
    empty = {r: 0 for r in reasons}
    for rows in bags.values():
        for fr in rows:
            for w in fr["warnings"]:
                if w.get("reason") in reasons and abs(w["lateral"]) < lateral_max:
                    empty[w["reason"]] += 1
    gain = {r: 0 for r in reasons}
    gain_range = {r: [] for r in reasons}
    for fr in set_o:
        objs = [o for o in labels.get(f"{fr['frame']:05d}", []) if o["plausible"] and o["in_gauge"]]
        for w in fr["warnings"]:
            if w.get("reason") in reasons and abs(w["lateral"]) < lateral_max \
                    and any(_near(w, o["bbox"]) for o in objs):
                gain[w["reason"]] += 1
                gain_range[w["reason"]].append(w["distance"])
    return {"reasons": list(reasons), "lateral_max_m": lateral_max,
            "empty_recordings_would_be_false_stops": empty,
            "set_o_in_gauge_object_gains": gain,
            "set_o_gain_range_m": {r: ([round(min(v), 1), round(max(v), 1)] if v else None)
                                   for r, v in gain_range.items()}}


def run(evidence_root: Path, labels_path: Path) -> dict:
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    bags = {b: load_frames(evidence_root, b) for b in EMPTY_BAGS}
    real = load_frames(evidence_root, REAL_BAG)
    set_o = load_frames(evidence_root, SET_O_BAG)
    check_reproduces_published(evidence_root, labels, set_o)
    events = json.loads((evidence_root / RESIDUAL).read_text(encoding="utf-8"))["events"]
    baseline = {"empty_recordings": screen_empty(bags, None), "doubleT_obstacle": screen_real(real, None),
                "set_o": score_set_o(set_o, labels)}
    out = {"schema": "resense-competitor-rule-screen-v1", "baseline": baseline, "rules": {},
           "promotion": promotion_screen(evidence_root, labels, bags, set_o)}
    for name, rule in RULES.items():
        entry = {"source": rule.source,
                 "empty_recordings": screen_empty(bags, rule.veto),
                 "doubleT_obstacle": screen_real(real, rule.veto),
                 "set_o": score_set_o(set_o, labels, rule.veto)}
        entry["ride_residual_events"] = screen_ride_events(events, rule.veto)
        base_o = baseline["set_o"]["objects"]
        entry["set_o_changed"] = {
            k: {"stop_frames": [base_o[k]["stop_frames"], v["stop_frames"]],
                "first_stop_m": [base_o[k]["first_stop_m"], v["first_stop_m"]]}
            for k, v in entry["set_o"]["objects"].items()
            if (v["stop_frames"], v["first_stop_m"]) != (base_o[k]["stop_frames"], base_o[k]["first_stop_m"])}
        out["rules"][name] = entry
    return out


def markdown(res: dict) -> str:
    b = res["baseline"]
    lines = ["| rule | empty bags: STOP frames / episodes | doubleT_obstacle STOP frames | ride residual events removed "
             "| set O objects changed |", "|---|---|---|---|---|",
             f"| (sealed detector) | {b['empty_recordings']['stop_frames']} / {b['empty_recordings']['stop_episodes']} "
             f"| {b['doubleT_obstacle']['stop_frames']} | 0 | - |"]
    for name, r in res["rules"].items():
        e, ride = r["empty_recordings"], r["ride_residual_events"]
        ch = "; ".join(f"{k} {v['stop_frames'][0]}->{v['stop_frames'][1]} frames, first {v['first_stop_m'][0]}->"
                       f"{v['first_stop_m'][1]} m" for k, v in r["set_o_changed"].items()) or "none"
        lines.append(f"| {name} | {e['stop_frames']} / {e['stop_episodes']} | {r['doubleT_obstacle']['stop_frames']} | "
                     f"{ride['events_removed']} of {ride['events']} | {ch} |")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--evidence", default=str(ROOT / "docs" / "evidence"))
    p.add_argument("--labels", default=str(ROOT / LABELS))
    p.add_argument("--out", default=None, help="write the screen as JSON")
    a = p.parse_args()
    res = run(Path(a.evidence), Path(a.labels))
    print(markdown(res))
    print("\npromotion of advisory detections:", json.dumps(res["promotion"], ensure_ascii=False))
    if a.out:
        Path(a.out).write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
