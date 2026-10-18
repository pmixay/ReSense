"""Revalidate completed L16 outputs without importing or running a detector."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
VARIANTS = ("upright", "case04_explicit", "case05_explicit", "case05_wrong")
BAGS = {"roundT_squareT_pressureGate_squareT": 545, "doubleT_obstacle": 201}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((HERE / name).read_text())


def operational(row):
    value = deepcopy(row)
    for field in ("decode_ms", "detect_ms", "total_ms"):
        del value[field]
    for data, message_key, level_key, decision_key in (
        (value, "msgs", "level", "dlevel"),
        (value["health_detail"], "messages", "level", "decision_level"),
    ):
        kept = [text for text in data[message_key] if not text.startswith("latency p95 ")]
        if kept != data[message_key] and data[level_key] == "warn":
            data[level_key] = data[decision_key]
        data[message_key] = kept
    del value["health_detail"]["latency_p95_ms"]
    return value


def stop_intervals(indices):
    groups = []
    for index in indices:
        if groups and index == groups[-1][-1] + 1:
            groups[-1][-1] = index
        else:
            groups.append([index, index])
    return groups


def main():
    reg, execution, summary = (read(name) for name in ("registration.json", "execution.json", "summary.json"))
    assert execution["status"] == "COMPLETE" and execution["returncode"] == 0
    assert execution["summary_sha256"] == sha(HERE / "summary.json")
    assert execution["log_sha256"] == sha(HERE / "run.log")
    assert execution["wrapper_sha256"] == sha(HERE / "execute_mapping.py")
    assert execution["registration_sha256"] == summary["registration_sha256"] == sha(HERE / "registration.json")
    assert reg["harness_sha256"] == sha(HERE / "run_mapping.py")
    assert reg["protocol_sha256"] == sha(HERE / "PROTOCOL.md")
    assert reg["variants"] == list(VARIANTS)
    assert summary["rows"] == reg["maximum_rows"] == 2984
    assert summary["source"] == reg["source"]
    assert reg["source"]["commit"] == "e9d8fc649f2dd51dd5cd1e4b04ac8c306cc02569"
    original_manifest = json.loads((Path(reg["source"]["root"]) /
        "docs/evidence/detector_freeze_2026-10-18_lidar.json").read_text())
    assert len(reg["source"]["files"]) == 38
    assert set(reg["source"]["files"]) == set(original_manifest["files"])
    assert len(reg["source"]["native"]) == 1
    assert list(reg["source"]["native"].values()) == [
        "511f7766639f0ddab471a77263f7a343de19d0a8217dd7cd3a11635c8a7db2c8"]
    for name, expected in (reg["source"]["files"] | reg["source"]["native"]).items():
        assert sha(Path(reg["source"]["root"]) / name) == expected
    assert summary["source_unchanged"] and summary["harness_unchanged"]
    for item in reg["p4_evidence"].values():
        assert sha(HERE / item["snapshot"]) == item["sha256"]
    output, all_hashes = {}, {}
    for bag, count in BAGS.items():
        metadata_path = Path("/home/resense/data/decoded") / bag / "meta.json"
        assert sha(metadata_path) == reg["inputs"][bag]["meta_sha256"]
        metadata = json.loads(metadata_path.read_text())
        assert len(metadata) == count
        recorded = {item["name"]: item for item in summary["bags"][bag]}
        assert set(recorded) == set(VARIANTS)
        rows_by_name = {}
        for name in VARIANTS:
            item = recorded[name]
            path = HERE / item["raw"]
            assert sha(path) == item["raw_sha256"]
            all_hashes[item["raw"]] = sha(path)
            rows = [json.loads(line) for line in path.read_text().splitlines()]
            assert len(rows) == item["frames"] == count
            for i, (row, meta) in enumerate(zip(rows, metadata)):
                assert row["i"] == i
                assert row["stamp"] == round(meta["stamp"], 4)
                assert row["bag_t"] == round(meta["bag_t"], 4)
                assert row["frame_id"] == meta["frame_id"] and row["topic"] == meta["topic"]
                assert type(row["obstacle"]) is bool and row["obstacle"] == bool(row["dets"])
                expected = ("STOP" if row["obstacle"] else "FAULT" if row["level"] == "error"
                            else "CAUTION" if row["warning"] or row["dlevel"] == "warn" else "GO")
                assert row["decision"] == expected
                assert row["health_detail"]["orientation_confirmed"] == row["mount_detail"]["orientation_confirmed"]
            rows_by_name[name] = rows
        baseline = rows_by_name["upright"]
        baseline_stop = [r["i"] for r in baseline if r["decision"] == "STOP"]
        assert len(baseline_stop) == (193 if count == 201 else 0)
        checked = {}
        for name, rows in rows_by_name.items():
            item = recorded[name]
            stop = [r["i"] for r in rows if r["decision"] == "STOP"]
            lost = sorted(set(baseline_stop) - set(stop))
            added = sorted(set(stop) - set(baseline_stop))
            changes = [i for i, (a, b) in enumerate(zip(baseline, rows)) if operational(a) != operational(b)]
            field_changes = Counter(key for a, b in zip(baseline, rows)
                                    for key, value in operational(a).items() if value != operational(b)[key])
            confirmed_stop = [r["i"] for r in rows if r["decision"] == "STOP"
                              and r["mount_detail"]["orientation_confirmed"]]
            ok_stop = [r["i"] for r in rows if r["decision"] == "STOP" and r["mount_detail"]["status"] == "ok"]
            first_confirmed = next((r["i"] for r in rows if r["mount_detail"]["orientation_confirmed"]), None)
            assert item["decisions"] == dict(Counter(r["decision"] for r in rows))
            assert item["statuses"] == dict(Counter(r["mount_detail"]["status"] for r in rows))
            assert item["first_orientation_confirmed"] == first_confirmed
            assert item["stop_while_confirmed"] == confirmed_stop and item["stop_after_status_ok"] == ok_stop
            assert item["stop_indices"] == stop and item["stop_intervals"] == stop_intervals(stop)
            assert item["lost_stop"] == lost and item["added_stop"] == added
            assert item["changed_non_timing_rows"] == changes and item["changed_fields"] == dict(field_changes)
            assert item["forward_cone_equal_frames"] == count
            if name != "case05_wrong":
                assert not changes and not lost and not added
                assert item["exact_vehicle_input_frames"] == count
            if "explicit" in name:
                expected_axes = {"forward": "-y", "left": "-z" if name == "case04_explicit" else "+z",
                                 "up": "+x" if name == "case04_explicit" else "-x"}
                assert item["overrides"] == {f"sensor.{k}": v for k, v in expected_axes.items()}
                assert item["explicit_mapping_pass"] is True
            else:
                assert item["overrides"] == {} and item["explicit_mapping_pass"] is None
            checked[name] = {"rows": count, "decisions": item["decisions"], "statuses": item["statuses"],
                             "first_confirmed": first_confirmed, "stop_intervals": stop_intervals(stop),
                             "confirmed_stop_count": len(confirmed_stop), "ok_stop_count": len(ok_stop),
                             "changed_rows": len(changes), "lost_stop": lost, "added_stop": added}
        output[bag] = checked
    assert summary["explicit_mapping_pass"] is True
    result = {"status": "EXPLICIT_KNOWN_MAPPING_PASS_AUTOMATIC_SIDE_MOUNT_UNRESOLVED",
              "checked_utc": datetime.now(timezone.utc).isoformat(), "source_commit": reg["source"]["commit"],
              "reviewer_sha256": sha(Path(__file__)), "registration_sha256": sha(HERE / "registration.json"),
              "execution_sha256": sha(HERE / "execution.json"), "summary_sha256": sha(HERE / "summary.json"),
              "rows": 2984, "raw_hashes": all_hashes, "bags": output,
              "limits": ["No detector rerun by this reviewer; input byte equivalence is asserted by the pinned producer on every frame.",
                         "Known synthetic signed-axis remounts of real inputs, not automatic recovery or a physical remount measurement.",
                         "Offline node replica; DDS, source freshness, throughput and arbitrary 24-mount recovery are outside this check.",
                         "All non-timing serialized fields compared exactly; full internal floating-point detector state is not serialized."]}
    (HERE / "review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])


if __name__ == "__main__":
    main()
