"""29.09 (new): the 28.09 judgement's figures next to this re-run's, from the summary JSONs of both
records and the 28.09 raw doubleT_obstacle run (for its first STOP frame and gaps).

    python compare_2809.py > comparison.json      # run inside docs/evidence/judgement_2026-09-29
"""
import gzip
import json

OLD, NEW = "../judgement_2026-09-28", "."
EMPTY = ["roundT_doubleT", "doubleT_platform", "roundT_pressureGate_roundT", "roundT_squareT_pressureGate_squareT",
         "squareT_platform_squareT_switch"]


def obstacle(summary, raw_rows):
    s = summary["doubleT_obstacle"]
    first = next((i for i, r in enumerate(raw_rows) if r["obstacle"]), None)
    gaps = [i for i, r in enumerate(raw_rows) if first is not None and i > first and not r["obstacle"]]
    ds = [r["nearest_distance"] for r in raw_rows if r["obstacle"] and r["nearest_distance"] is not None]
    return {"first_stop_frame": first, "stop_frames": s["stop_frames"], "frames": s["frames"],
            "non_stop_frames_after_first_stop": gaps, "stop_distance_m": [round(min(ds), 1), round(max(ds), 1)]}


def empty(summary):
    out = {}
    for b in EMPTY + ["_five_empty"]:
        s = summary[b]
        eps = s["stop_episodes"]
        out[b] = {"stop_frames": s["stop_frames"], "caution_frames": s["caution_frames"], "frames": s["frames"],
                  "caution_pct": round(100 * s["caution_frames"] / s["frames"], 1),
                  "stop_episodes": eps if isinstance(eps, int) else len(eps)}
        if not isinstance(eps, int):
            out[b]["episodes_frames_distance_m"] = eps
    return out


def ride(s):
    return {k: s[k] for k in ["splits", "frames", "stop_frames", "caution_frames", "stop_episodes",
                              "stop_episodes_per_km"]} | {
        "stop_pct": round(100 * s["stop_frames"] / s["frames"], 2),
        "caution_pct": round(100 * s["caution_frames"] / s["frames"], 1),
        "episode_distances_m": sorted(e["distance_m"] for e in s["episodes"])}


def set_o(s):
    objs = {k: {"in_gauge": v["in_gauge_intent"], "first_stop_m": v["first_stop_m"],
                "stop_frames_in_env": v["stop_frames_in_env"], "frames_in_env": v["frames_in_env"],
                "stop_frames": v["stop_frames"], "caution_frames": v["caution_frames"]}
            for k, v in s["objects"].items()}
    return {"objects": objs,
            "outside_objects_stop_frames": {k: v["stop_frames"] for k, v in s["objects"].items()
                                            if not v["in_gauge_intent"]},
            "stop_detections_near_no_object": s["stop_detections_near_no_object"],
            "frames_with_stop": s["frames_with_stop"]}


def transplant(s):
    return {"sustained_windows_by_range": {r: v["sustained"] for r, v in s["by_range"].items()},
            "any_stop_windows_by_range": {r: v["any_stop"] for r, v in s["by_range"].items()},
            "control_stop_frames_total": sum(w["control_stop_frames"] for w in s["windows"]),
            "windows": len(s["windows"])}


def load(path):
    try:
        return json.load(open(path))
    except FileNotFoundError:
        return None


def main():
    old_raw = [json.loads(line) for line in gzip.open(f"{OLD}/raw/offline/doubleT_obstacle.jsonl.gz", "rt")]
    new_raw = [json.loads(line) for line in gzip.open(f"{NEW}/raw/offline/doubleT_obstacle.jsonl.gz", "rt")]
    o_old, o_new = load(f"{OLD}/offline_summary.json"), load(f"{NEW}/offline_summary.json")
    out = {"doubleT_obstacle": {"2809": obstacle(o_old, old_raw), "2909": obstacle(o_new, new_raw)},
           "five_empty": {"2809": empty(o_old), "2909": empty(o_new)}}
    r_old, r_new = load(f"{OLD}/ride_summary.json"), load(f"{NEW}/ride_summary.json")
    if r_new:
        out["ride"] = {"2809": ride(r_old), "2909": ride(r_new)}
    s_old, s_new = load(f"{OLD}/setO.json"), load(f"{NEW}/setO.json")
    if s_new:
        out["set_O"] = {"2809": set_o(s_old), "2909": set_o(s_new)}
    t_old = load(f"{OLD}/transplant.json")
    t_def, t_off = load(f"{NEW}/transplant_default.json"), load(f"{NEW}/transplant_veto_off.json")
    out["transplant"] = {"2809": transplant(t_old)}
    if t_def:
        out["transplant"]["2909_default"] = transplant(t_def)
    if t_off:
        out["transplant"]["2909_ego_veto_off"] = transplant(t_off)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
