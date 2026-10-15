#!/usr/bin/env python3
"""Detector-free G3 structural, provenance, input-metadata and determinism checks.

Standard library only. No project imports, point loading, detector, ICP, rendering,
range/probe execution, result reading, or file writes. --print-* prints proposals
for review/apply_patch; the default verifies the committed registration.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SEED = 20261015
SHAPES = ("bed030", "rail030", "box200", "cable005", "plank", "lying", "polem", "polep", "trolley")
VARIANTS = ("base", "pitchp2", "pitchm2", "rollp2", "yawp3", "drop30", "drop50", "noise2cm", "hz5", "dedup", "dark10")
WINDOWS = (("w01", 1020, 1734), ("w02", 2550, 3264), ("w03", 6324, 7038), ("w04", 8823, 9537))
EXCLUDED = (
    ("A", "roundT_squareT_pressureGate_squareT", 150, 340),
    ("B", "roundT_doubleT", 50, None),
    ("C", "roundT_pressureGate_roundT", 0, None),
    ("D", "squareT_platform_squareT_switch", 100, 420),
    ("S", "squareT_platform_squareT_switch", 360, 620),
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def invalid(value):
        raise ValueError(f"nonfinite JSON constant: {value}")

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs, parse_constant=invalid)


def h(tag):
    return int.from_bytes(hashlib.sha256(f"{SEED}|{tag}".encode("utf-8")).digest()[:8], "big")


def generate_cases():
    rows = []
    for window, _, _ in WINDOWS:
        for shape in SHAPES:
            draw = h(f"{window}/{shape}/lateral") % 1801 - 900
            direction = -1 if h(f"{window}/{shape}/direction") % 2 == 0 else 1
            for motion in ("approach", "crossing"):
                case_id = f"g3-{window}-{shape}-{motion}"
                rows.append({"id": case_id, "window": window, "shape": shape,
                             "motion": motion, "lateral_draw_mm": draw,
                             "direction": direction if motion == "crossing" else 0,
                             "seed": h(case_id + "/seed") % 2147483647})
        for motion in ("approach", "crossing"):
            case_id = f"g3-{window}-bedneg-{motion}"
            rows.append({"id": case_id, "window": window, "shape": "bedneg",
                         "motion": motion, "lateral_draw_mm": h(f"{window}/bed030/lateral") % 1801 - 900,
                         "direction": (-1 if h(f"{window}/bed030/direction") % 2 == 0 else 1) if motion == "crossing" else 0,
                         "seed": h(case_id + "/seed") % 2147483647})
        case_id = f"g3-{window}-empty-control"
        rows.append({"id": case_id, "window": window, "shape": "empty", "motion": "control",
                     "lateral_draw_mm": 0, "direction": 0, "seed": h(case_id + "/seed") % 2147483647})
    return sorted(rows, key=lambda r: r["id"])


def check_spec(spec):
    required = {"schema", "registration_date", "base_commit", "status", "seed", "claim", "units", "paths",
                "exclusions", "exclusion_policy", "source_definition_directory", "windows", "window_policy",
                "shapes", "randomization", "motions", "geometry", "visibility", "variants", "variant_policy",
                "metrics", "execution", "cases"}
    require(set(spec) == required, "top-level schema keys differ")
    require(spec["schema"] == "resense-g3-preregistration-v1", "schema version")
    require(spec["seed"] == SEED and type(spec["seed"]) is int, "fixed integer seed")
    require(spec["status"] == "preregistered_not_executed", "registration must contain no execution state")
    require(spec["registration_date"] == "2026-10-15" and spec["base_commit"] == "3fdc879", "registration origin")
    require([(w["id"], w["start"], w["end"]) for w in spec["windows"]] == list(WINDOWS), "fixed windows")
    for w in spec["windows"]:
        require(w["recording"] == "new_data" and w["insert"] == w["start"] + 60, "ride or warm-up differs")
        require(w["end"] - w["start"] == 714, "window length")
        require(w["first_split"] * 51 == w["start"] and (w["last_split"] + 1) * 51 == w["end"], "split/global index mapping")
        require(w["category_status"] == "unconfirmed", "category is not verified at registration")
    for left, right in zip(spec["windows"], spec["windows"][1:]):
        require(left["end"] <= right["start"], "overlapping windows")
    exclusions = [(x["name"], x["recording"], x["start_inclusive"], x["end_exclusive"]) for x in spec["exclusions"]]
    require(exclusions == list(EXCLUDED), "A/B/C/D/S definitions changed")
    require(not {w["recording"] for w in spec["windows"]} & {x[1] for x in EXCLUDED}, "exclusion overlap")
    require([s["id"] for s in spec["shapes"]] == list(SHAPES), "shape coverage/order")
    dimensions = {"bed030": [0.3, 0.3, 0.1], "rail030": [0.3, 0.3, 0.1], "box200": [2.0, 2.0, 2.0],
                  "plank": [0.2, 2.0, 0.2], "lying": [1.8, 0.5, 0.3], "trolley": [1.5, 1.0, 1.0]}
    for shape in spec["shapes"]:
        if shape["id"] in dimensions:
            require(shape["primitive"] == "cuboid" and shape["size_lwh_m"] == dimensions[shape["id"]], "cuboid dimensions")
        else:
            diameter, height = (0.05, 2.5) if shape["id"] == "cable005" else (0.15, 2.5)
            require(shape["primitive"] == "vertical_cylinder" and shape["diameter_m"] == diameter and shape["height_m"] == height, "cylinder dimensions")
    require(len({s["class"] for s in spec["shapes"]}) == 8, "eight classes, nine shape/side configurations")
    require([v["id"] for v in spec["variants"]] == list(VARIANTS), "perturbation coverage")
    require(spec["cases"] == generate_cases(), "case table is not the exact deterministic 84-row matrix")
    require(len(spec["cases"]) == 84 and len({c["id"] for c in spec["cases"]}) == 84, "case count/IDs")
    for case in spec["cases"]:
        require(re.fullmatch(r"g3-w0[1-4]-[a-z0-9]+-(approach|crossing|control)", case["id"]), "invalid case ID")
        require(type(case["lateral_draw_mm"]) is int and -900 <= case["lateral_draw_mm"] <= 900, "lateral range")
    for section in ("window_policy", "randomization", "motions", "geometry", "visibility", "metrics", "execution"):
        require(isinstance(spec[section], dict) and all(isinstance(v, str) and v for v in spec[section].values()), f"empty/nontext policy: {section}")
    require({"match", "first_stop", "held90", "denominators", "misses", "controls", "perturbations"} == set(spec["metrics"]), "metric schema")
    require(not (HERE / "results.json").exists() and not (HERE / "run_final").exists(), "execution artifacts present during preregistration")
    canonical(spec)  # Reject NaN even when passed as an in-memory object.


def definition_hashes(spec):
    directory = ROOT / spec["source_definition_directory"]
    names = ("run_range_matrix.sh", "run_range_extra.sh", "run_probes.sh")
    hashes = {name: digest((directory / name).read_bytes()) for name in names}
    matrix = (directory / "run_range_matrix.sh").read_text(encoding="utf-8")
    for name, recording, start, end in EXCLUDED:
        pattern = rf'add "{name}_.*?\$C/{recording} .*?--start {start} --d0 (?:230|\$d)'
        if end is not None:
            pattern += rf' --end {end}'
        require(re.search(pattern, matrix), f"input definition missing: {name}")
    return hashes


def input_metadata(spec, data_root, original_root):
    """Read ONLY intake/timestamp input JSON and check point/bag filename presence."""
    compact = data_root / "cache" / "new_data"
    intake_path = compact / "intake_manifest.json"
    intake = load(intake_path)
    require(intake["schema"] == "resense-extended-ride-intake-v1" and intake["cache_frames"] == 11271, "ride intake")
    out = {"schema": "resense-g3-input-metadata-v1", "scope": "Input timestamps, declared archive identity and filename presence ONLY; no point geometry, detector output or outcomes.",
           "intake_sha256": digest(intake_path.read_bytes()),
           "declared_archive_sha256": intake["archive_sha256_actual"],
           "source_definition_sha256": definition_hashes(spec), "windows": []}
    for w in spec["windows"]:
        stamps, stamp_hashes, source_files = [], {}, []
        for split in range(w["first_split"], w["last_split"] + 1):
            name = f"new_data_{split}_stamps.json"
            path = compact / name
            m = load(path)
            require(m["bag"] == f"new_data_{split}" and m["frames"] == 51, f"split count: {split}")
            require(set(m["stamps"]) == {f"{i:04d}" for i in range(51)}, f"stamp coverage: {split}")
            stamp_hashes[name] = digest(path.read_bytes())
            require((original_root / f"new_data_{split}.db3").is_file(), f"original split absent: {split}")
            for local in range(51):
                filename = f"new_data_{split}_{local:04d}.npy.zst"
                require((compact / filename).is_file(), f"compact frame absent: {filename}")
                source_files.append(filename)
                value = m["stamps"][f"{local:04d}"]
                require(type(value) in (int, float) and math.isfinite(value), "timestamp type")
                stamps.append(value)
        gaps = [b - a for a, b in zip(stamps, stamps[1:])]
        require(all(g > 0 for g in gaps), "nonmonotonic source time")
        out["windows"].append({"id": w["id"], "frames": len(stamps), "point_files_present": len(source_files),
                               "first_bag_unix_s": stamps[0], "insert_bag_unix_s": stamps[60],
                               "last_bag_unix_s": stamps[-1], "span_s": round(stamps[-1] - stamps[0], 6),
                               "max_gap_s": round(max(gaps), 6), "gaps_over_0p25_s": sum(g > 0.25 for g in gaps),
                               "timestamp_sequence_sha256": digest(canonical(stamps)),
                               "ordered_point_filenames_sha256": digest(canonical(source_files)),
                               "stamp_file_sha256": stamp_hashes,
                               "geometry_status": "not_computed; category unconfirmed; no ride ICP available in supplied odometry directory"})
    return out


def self_test(spec):
    count = 0
    mutations = (
        lambda s: s["cases"].pop(),
        lambda s: s["cases"].append(s["cases"][0]),
        lambda s: s["cases"][0].update(seed=0),
        lambda s: s["windows"][0].update(recording="roundT_doubleT"),
        lambda s: s["windows"][1].update(start=1020),
        lambda s: s["shapes"][0].update(size_lwh_m=[0.3, 0.3, 0.3]),
        lambda s: s["variants"].pop(),
        lambda s: s.update(seed=True),
    )
    for mutate in mutations:
        changed = copy.deepcopy(spec)
        mutate(changed)
        try:
            check_spec(changed)
        except ValueError:
            count += 1
        else:
            raise ValueError("negative validation self-test accepted a mutation")
    require(canonical(generate_cases()) == canonical(generate_cases()), "repeat generation changed")
    return count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-cases", action="store_true")
    parser.add_argument("--print-metadata", action="store_true")
    parser.add_argument("--check-inputs", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--data-root", type=Path)
    parser.add_argument("--original-root", type=Path)
    args = parser.parse_args()
    spec = load(HERE / "spec.json")
    if args.print_cases:
        for case in generate_cases():
            print("    " + json.dumps(case, separators=(", ", ": ")) + ",")
        return
    data_root = args.data_root or Path(spec["paths"]["data_root"])
    original_root = args.original_root or Path(spec["paths"]["original_ride"])
    if args.print_metadata:
        print(json.dumps(input_metadata(spec, data_root, original_root), indent=2, allow_nan=False))
        return
    check_spec(spec)
    stored = load(HERE / "input_metadata.json")
    require(stored["source_definition_sha256"] == definition_hashes(spec), "harness input definitions changed")
    require(len(stored["windows"]) == 4 and all(w["frames"] == 714 for w in stored["windows"]), "metadata schema")
    if args.check_inputs:
        require(stored == input_metadata(spec, data_root, original_root), "input metadata/fingerprints changed")
    negative = self_test(spec) if args.self_test else 0
    print(json.dumps({"validation": "PASS", "cases": 84, "variants": 11, "scheduled_replays": 924,
                      "distinct_disjoint_ride_windows": 4, "classes": 8, "negative_mutations_rejected": negative,
                      "input_metadata_checked": args.check_inputs,
                      "spec_canonical_sha256": digest(canonical(spec)),
                      "case_table_sha256": digest(canonical(generate_cases())),
                      "input_metadata_canonical_sha256": digest(canonical(stored)),
                      "executed": "metadata/schema/determinism validation only"}, indent=2))


if __name__ == "__main__":
    main()
