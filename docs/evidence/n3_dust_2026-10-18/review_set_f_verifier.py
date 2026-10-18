"""Independent schema/tamper probes with artificial records, never detector evidence."""
from __future__ import annotations

from copy import deepcopy
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load_verifier():
    spec = importlib.util.spec_from_file_location("set_f_verifier_under_review", HERE / "summarize_set_f.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, separators=(",", ":")) + "\n")


def make_fixture(base, verifier):
    from scripts.dust_reference import _digest
    from scripts.dust_set_f import summarize

    cache, bank, out = (base / name for name in ("cache", "bank", "out"))
    for path in (cache, bank, out):
        path.mkdir()
    selected = {}
    for start in verifier.STARTS:
        for split in range(start, start + 3):
            stamps = {}
            for frame in range(51):
                stamp = 1000 + split * .51 + frame * .01
                stamps[f"{frame:04d}"] = stamp
                (cache / f"new_data_{split}_{frame:04d}.npy.zst").write_bytes(b"schema probe only")
            save(cache / f"new_data_{split}_stamps.json", {"bag": f"new_data_{split}", "stamps": stamps})
        for index in range(110):
            split, frame = start + index // 51, index % 51
            selected[f"new_data_{split}_{frame:04d}"] = 1000 + split * .51 + frame * .01
    helpers = {"scripts/dust_reference.py": sha(ROOT / "scripts/dust_reference.py")}
    manifest = {"schema": "set-f-dust-fixed-placement-v2-clean-reference",
                "source_root": str(ROOT), "configuration_yaml_sha256": sha(ROOT / "configs/default.yaml"),
                "native_status": "native artificial schema fixture only",
                "source_hashes": {"resense/dust.py": sha(ROOT / "resense/dust.py")},
                "script_sha256": sha(ROOT / "scripts/dust_set_f.py"),
                "speeds_sha256": sha(ROOT / "docs/extended_dataset_intake.json"),
                "selected_stamps_sha256": hashlib.sha256(json.dumps(selected, sort_keys=True).encode()).hexdigest(),
                "helper_sha256": helpers, "sequences": {}}
    planned = verifier.expected_paths(manifest, cache)
    report = {"schema": "set-f-dust-battery-v2-clean-reference", "script_sha256": manifest["script_sha256"],
              "configuration_yaml_sha256": manifest["configuration_yaml_sha256"], "native_status": manifest["native_status"],
              "helper_sha256": helpers, "dust_seed": 20261018, "dust_generator_sha256": sha(ROOT / "resense/dust.py"),
              "source_hashes": {"resense/dust.py": sha(ROOT / "resense/dust.py")},
              "detector_root": str(ROOT), "sequences": {}}
    reference = {"schema": "dust-clean-reference-v1", "input_to_model_rotation": [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]],
                 "rail_z_at20": -1.5, "source_frame_sha256": "0" * 64}
    reference["reference_sha256"] = _digest(reference)
    for start in verifier.STARTS:
        for kind in verifier.KINDS:
            name = f"{start}_{kind}"
            frozen = [{**row, "clean_returns": 2, "spec": {"lateral": 0.}, "rail_z": -1.5,
                       "dust_reference": reference, "clean_frame_sha256": "1" * 64} for row in planned[start]]
            save(bank / f"{name}.json", {"id": name, "kind": kind, "start_split": start,
                                        "requested_frames": 110, "frames": frozen})
            manifest["sequences"][name] = sha(bank / f"{name}.json")
            levels = {}
            for level, (density, extinction) in zip(verifier.LEVELS, ((0., 0.), (.1, .0005), (1., .003), (10., .02))):
                rows = []
                for item in frozen:
                    audit = {"seed": 20261018, "frame_index": item["index"], "rail_z": -1.5,
                             "placement_reference": reference, "added_returns": 0, "removed_returns": 0,
                             "spec": {"density": density, "extinction": extinction, "x_bounds": [2.5, 60.],
                                      "y_bounds": [-3., 3.], "height_bounds": [.1, 3.5], "intensity_max": 5.}}
                    rows.append({"index": item["index"], "cache_file": item["cache_file"], "distance": item["distance"],
                                 "clean_returns": 2, "retained_object_returns": 2, "hit": True, "false_detections": 0,
                                 "decision": "STOP", "degraded": False, "augmentation": audit,
                                 "dust_reference_sha256": reference["reference_sha256"], "clean_frame_sha256": "1" * 64,
                                 "result": {"stamp": item["stamp"], "obstacle": True, "warning": False,
                                            "health": {"level": "ok", "decision_level": "ok"},
                                            "detections": [{"distance": round(item["distance"], 2), "lateral": 0.}]}})
                path = out / f"{name}_{level}.jsonl.gz"
                with gzip.open(path, "wt") as stream:
                    for row in rows:
                        stream.write(json.dumps(row, separators=(",", ":")) + "\n")
                levels[level] = {**summarize(rows, levels.get("clean") if level != "clean" else None), "raw_sha256": sha(path)}
            report["sequences"][name] = {"levels": levels}
    save(bank / "manifest.json", manifest)
    report["placement_manifest_sha256"] = sha(bank / "manifest.json")
    save(out / "summary.json", report)
    save(out / "verified_ride_receipt.json", {"receipt": {"verified": True, "total_frames": 11271}})
    return cache, bank, out, report, manifest


def run(verifier, cache, bank, out):
    sys.argv = ["summarize_set_f", "--cache", str(cache), "--bank", str(bank), "--out", str(out)]
    verifier.main()


def main():
    sys.path.insert(0, str(ROOT))
    verifier = load_verifier()
    outcomes = {}
    with tempfile.TemporaryDirectory(prefix="set_f_verifier_review_") as directory:
        cache, bank, out, report, manifest = make_fixture(Path(directory), verifier)
        run(verifier, cache, bank, out)
        outcomes["unaltered_artificial_complete_fixture"] = "accepted"
        name = "46_person"
        original_raw = (out / f"{name}_clean.jsonl.gz").read_bytes()
        original_bank = (bank / f"{name}.json").read_bytes()
        for case in ("summary_hits", "summary_counts", "raw_hit", "raw_decision", "missing_sequence", "shortened_bank", "reference_changed", "placement_helper_changed"):
            altered = deepcopy(report)
            if case == "summary_hits":
                altered["sequences"][name]["levels"]["clean"]["hit_frames"].pop()
            elif case == "summary_counts":
                altered["sequences"][name]["levels"]["clean"]["counts"]["STOP"] += 1
            elif case == "missing_sequence":
                del altered["sequences"][name]
            elif case in ("shortened_bank", "placement_helper_changed"):
                content = json.loads(original_bank)
                if case == "shortened_bank":
                    content["frames"].pop()
                save(bank / f"{name}.json", content)
                changed_manifest = deepcopy(manifest)
                changed_manifest["sequences"][name] = sha(bank / f"{name}.json")
                if case == "placement_helper_changed":
                    changed_manifest["helper_sha256"]["scripts/dust_reference.py"] = "f" * 64
                save(bank / "manifest.json", changed_manifest)
                altered["placement_manifest_sha256"] = sha(bank / "manifest.json")
            else:
                rows = [json.loads(line) for line in gzip.decompress(original_raw).decode().splitlines()]
                if case == "raw_hit":
                    rows[0]["hit"] = False
                elif case == "raw_decision":
                    rows[0]["decision"] = "GO"
                else:
                    rows[0]["augmentation"]["placement_reference"]["rail_z_at20"] = -2.
                with gzip.open(out / f"{name}_clean.jsonl.gz", "wt") as stream:
                    for row in rows:
                        stream.write(json.dumps(row) + "\n")
                altered["sequences"][name]["levels"]["clean"]["raw_sha256"] = sha(out / f"{name}_clean.jsonl.gz")
            save(out / "summary.json", altered)
            try:
                run(verifier, cache, bank, out)
            except ValueError as error:
                outcomes[case] = str(error)
            else:
                raise AssertionError(f"tampered fixture accepted: {case}")
            (out / f"{name}_clean.jsonl.gz").write_bytes(original_raw)
            (bank / f"{name}.json").write_bytes(original_bank)
            save(bank / "manifest.json", manifest)
        (cache / "new_data_48_0007.npy.zst").unlink()
        try:
            verifier.expected_paths(manifest, cache)
        except ValueError as error:
            outcomes["missing_required_110th_source"] = str(error)
        else:
            raise AssertionError("missing required source accepted")
    result = {"scope": "Artificial schema fixtures only; no cloud decoding or detector calls and no measurement claim.",
              "verifier_sha256": sha(HERE / "summarize_set_f.py"), "probe_sha256": sha(Path(__file__)),
              "outcomes": outcomes}
    save(HERE / "independent_set_f_verifier_probes.json", result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
