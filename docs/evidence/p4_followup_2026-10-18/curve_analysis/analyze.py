#!/usr/bin/env python3
"""Offline B6/N1 crosswalk. Reads saved records; imports no detector or ICP code."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
P4_COMMIT = "1b880168ce2dbeec2071838892ac05eed5a9166a"
LOCAL_EVIDENCE = "cf188486f5c2339cd74adcb52ecdd21a59f8fad0"
B6 = "docs/evidence/gauge_stability_2026-10-18"
N1 = "docs/evidence/n1_n4_2026-10-18/final_core_f5ff15f"
BAGS = {"B": "roundT_doubleT", "C": "roundT_pressureGate_roundT"}
XS = np.arange(10.0, 201.0, 5.0)
ANCHORS = np.array([40.0, 80.0, 120.0])
POLY = np.column_stack([np.ones(3), ANCHORS, ANCHORS ** 2])


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(commit, path):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def quantiles(values):
    a = np.asarray(values, dtype=float)
    return {"n": len(a), **{f"p{q}": float(np.percentile(a, q)) if len(a) else None
                            for q in (50, 90, 99, 100)}}


def error_stats(values):
    a = np.abs(np.asarray(values, dtype=float))
    return {**quantiles(a), "share_over_0.5m": float(np.mean(a > .5)) if len(a) else None,
            "share_over_1.05m": float(np.mean(a > 1.05)) if len(a) else None}


def lateral(row, x):
    return row["center"] + row["tan_yaw"] * x + row["half_curv"] * x * x


def compose(rows):
    segment, pose, result = 0, np.eye(4), []
    for i, row in enumerate(rows):
        if row["T"] is None:
            segment += int(i > 0)
            pose = np.eye(4)
        else:
            transform = np.asarray(row["T"], dtype=float)
            assert transform.shape == (4, 4) and np.isfinite(transform).all()
            pose = pose @ transform
        result.append((segment, pose.copy()))
    return result


def paths(tracks, poses):
    """The same segment-safe forward-path construction as the archived B6 method."""
    result = []
    for i, row in enumerate(tracks):
        segment, pose = poses[i]
        inverse = np.linalg.inv(pose)
        rotation = np.asarray(row["R"])
        points = [np.zeros(3)]
        for j in range(i + 1, len(tracks)):
            if poses[j][0] != segment:
                break
            point = rotation @ (inverse @ poses[j][1])[:3, 3]
            points.append(point)
            if point[0] > max(XS):
                break
        points = np.asarray(points)
        points = points[points[:, 0] >= np.maximum.accumulate(points[:, 0])]
        _, first = np.unique(points[:, 0], return_index=True)
        result.append(points[np.sort(first)])
    return result


def path_y(points, x):
    if len(points) < 2 or x < points[0, 0] or x > points[-1, 0]:
        return None
    return float(np.interp(x, points[:, 0], points[:, 1]))


def compensated_step(previous, current, previous_rotation, current_rotation, transform, x):
    """B6-compatible lateral centerline metric at z=0, not a 3D rail-edge metric."""
    grid = np.arange(0.0, 260.0, 1.0)
    points = np.column_stack([grid, np.polynomial.polynomial.polyval(grid, previous),
                              np.zeros_like(grid)])
    inverse = np.linalg.inv(np.asarray(transform))
    mapped = (np.asarray(current_rotation) @ (
        inverse[:3, :3] @ (np.asarray(previous_rotation).T @ points.T)
        + inverse[:3, 3:4])).T
    if not np.all(np.diff(mapped[:, 0]) > 0) or not mapped[0, 0] <= x <= mapped[-1, 0]:
        return None
    return abs(float(np.polynomial.polynomial.polyval(x, current))
               - float(np.interp(x, mapped[:, 0], mapped[:, 1])))


def input_data():
    identities = {}

    def read(commit, path):
        raw = blob(commit, path)
        identities[f"{commit}:{path}"] = {"sha256": sha(raw), "bytes": len(raw)}
        return raw

    archive = read(P4_COMMIT, f"{B6}/b6_raw.tar.xz")
    expected = read(P4_COMMIT, f"{B6}/SHA256SUMS").decode().split()[0]
    assert sha(archive) == expected
    read(P4_COMMIT, "scripts/gauge_stability.py")
    read(P4_COMMIT, f"{B6}/README.md")
    monitored = json.loads(read(P4_COMMIT, f"{B6}/monitored.json"))
    subset, members = {}, {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:xz") as stream:
        for label, bag in BAGS.items():
            case = {}
            for key, member in [("poses", f"poses_{bag}.json"),
                                ("v110", f"v110/track_{bag}.json"),
                                ("v100", f"v100/track_{bag}.json")]:
                raw = stream.extractfile(member).read()
                members[member] = {"sha256": sha(raw), "bytes": len(raw)}
                case[key] = json.loads(raw)
            for version in ("v110", "v100"):
                case[f"monitored_{version}"] = monitored[f"{bag}|{version}"]
                for kind in ("measure", "honesty"):
                    case[f"{kind}_{version}"] = json.loads(read(
                        P4_COMMIT, f"{B6}/{version}/{kind}_{bag}.json"))
            subset[label] = case
    n1_raw = read(LOCAL_EVIDENCE, f"{N1}/rows/{BAGS['B']}.jsonl.gz")
    report = json.loads(read(LOCAL_EVIDENCE, f"{N1}/{BAGS['B']}.json"))
    assert sha(n1_raw) == report["rows_sha256"]
    assert report["source_sha256_at_start"] == report["source_sha256_at_end"]
    assert not report["source_changed_during_run"]
    n1 = [json.loads(line) for line in gzip.decompress(n1_raw).splitlines()]
    display_source = read(LOCAL_EVIDENCE, "ros2_ws/src/resense_ros/resense_ros/gauge_display.py")
    assert sha(display_source) == report["source_sha256_at_start"][
        "ros2_ws/src/resense_ros/resense_ros/gauge_display.py"]
    meta_path = Path("/home/resense/data/decoded") / BAGS["B"] / "meta.json"
    meta_raw = meta_path.read_bytes()
    assert sha(meta_raw) == report["cache_meta_sha256"]
    meta = json.loads(meta_raw)
    assert [row["frame"] for row in n1] == [item["i"] for item in meta] == list(range(252))
    assert all(row["stamp"] == item["stamp"] for row, item in zip(n1, meta))
    meta_archive = gzip.compress(meta_raw, mtime=0)
    (HERE / "inputs").mkdir(parents=True, exist_ok=True)
    (HERE / "inputs/B_cache_meta.json.gz").write_bytes(meta_archive)
    raw_subset = json.dumps(subset, separators=(",", ":")).encode()
    subset_archive = gzip.compress(raw_subset, mtime=0)
    (HERE / "inputs/b6_B_C_subset.json.gz").write_bytes(subset_archive)
    identities["local_cache_meta"] = {"original_path": str(meta_path), "sha256": sha(meta_raw),
                                      "archived_gzip_sha256": sha(meta_archive)}
    identities["selected_B6_members"] = members
    identities["selected_subset_gzip_sha256"] = sha(subset_archive)
    return subset, n1, report, identities


def check_alignment(case, n1):
    rows = case["v110"]["rows"]
    assert len(rows) == len(n1) == 252
    assert [row["i"] for row in rows] == list(range(252))
    errors, recurrence_errors = [], []
    previous_display = None
    previous_stamp = None
    for old, saved in zip(rows, n1):
        errors.append(float(np.max(np.abs(lateral(old, ANCHORS) - saved["raw_y"]))))
        assert old["axis_valid"] == saved["track"]["axis_valid"]
        assert np.array_equal(old["R"], np.eye(3))
        mount = saved["result"]["mount"]
        assert mount["orientation"] == "configured"
        assert (mount["roll_deg"], mount["pitch_deg"], mount["yaw_deg"]) == (0, 0, 0)
        # The archived source applies one scalar EMA/reset to the whole lateral
        # array. Validate its recurrence at every saved sample before using the
        # resulting quadratic between/beyond the three saved sample locations.
        assert saved["gauge"]["valid"]
        current_display = np.asarray(saved["display_y"])
        raw = np.asarray(saved["raw_y"])
        if previous_display is None or saved["gauge"]["reason"] == "reseeded_near_axis_change":
            expected_display = raw
        else:
            dt = min(1.0, max(0.0, saved["stamp"] - previous_stamp))
            speed = saved["display_speed_mps"]
            alpha = (max(1 - np.exp(-abs(speed) * dt / 9.0), 1 - np.exp(-dt / 1.6))
                     if speed is not None else 1 - np.exp(-dt / .8))
            expected_display = previous_display + alpha * (raw - previous_display)
        recurrence_errors.append(float(np.max(np.abs(current_display - expected_display))))
        previous_display, previous_stamp = current_display, saved["stamp"]
    assert max(errors) == 0
    assert max(recurrence_errors) < 1e-12
    range_changes = [i for i, row in enumerate(n1)
                     if row["health"]["monitored_range"] != case["monitored_v110"][i]]
    return {"frames": 252, "exact_raw_axis_samples": 756, "maximum_raw_axis_sample_delta_m": max(errors),
            "axis_valid_exact_all_frames": True, "B6_rotation_identity_all_frames": True,
            "N1_mount_configured_zero_angles_all_frames": True,
            "N1_stamp_and_frame_match_hash_verified_cache_meta": True,
            "display_quadratic_EMA_recurrence_checked_all_frames": True,
            "maximum_display_EMA_sample_recurrence_error_m": max(recurrence_errors),
            "monitored_range_differing_frames": range_changes,
            "scope": "Exact frame-index/geometry fingerprint, verified N1 timestamps and configured-axis correspondence. B6 stores no timestamps or point-payload hashes; byte-identical raw input cannot be proven from these B6 files. No new ICP or detector run."}


def analyze_case(label, case, n1=None):
    rows, prows = case["v110"]["rows"], case["poses"]["rows"]
    expected = 252 if label == "B" else 268
    assert len(rows) == len(prows) == expected
    assert [r["i"] for r in rows] == [r["i"] for r in prows] == list(range(expected))
    assert all(np.array_equal(r["R"], np.eye(3)) for r in rows)
    assert case["v100"]["rows"] == rows
    pose_chain = compose(prows)
    truth = paths(rows, pose_chain)
    raw_coefs = [np.array([r["center"], r["tan_yaw"], r["half_curv"]]) for r in rows]
    display_coefs = [np.linalg.solve(POLY, r["display_y"]) if r["display_y"] else None
                    for r in n1] if n1 is not None else None
    all_errors, axis_errors, monitored_old, monitored_new = [], [], [], []
    display_errors, same_visible_raw, display_self_anchor = [], [], []
    points, frame_rows = [], []
    for i, (row, path) in enumerate(zip(rows, truth)):
        frame = {"frame": i, "path_max_forward_m": float(path[-1, 0]),
                 "axis_valid_m": row["axis_valid"], "monitored_v110_m": case["monitored_v110"][i],
                 "monitored_v100_m": case["monitored_v100"][i], "errors_at_m": {}}
        if n1 is not None:
            frame.update(N1_monitored_m=n1[i]["health"]["monitored_range"],
                         N1_solid_m=n1[i]["gauge"]["solid_range_m"], N1_valid=n1[i]["gauge"]["valid"])
        for x in XS:
            target = path_y(path, x)
            if target is None:
                continue
            raw_error = float(lateral(row, x) - row["center"] - target)
            all_errors.append(raw_error)
            in_axis = x <= min(row["axis_valid"], case["v110"]["range_max"])
            in_monitored = x <= case["monitored_v110"][i]
            if in_axis:
                axis_errors.append(raw_error)
            if x <= case["monitored_v100"][i]:
                monitored_old.append(raw_error)
            if in_monitored:
                monitored_new.append(raw_error)
            point = {"frame": i, "distance_m": float(x), "driven_path_lateral_m": target,
                     "raw_axis_error_signed_m": raw_error, "within_axis": bool(in_axis),
                     "within_monitored_v110": bool(in_monitored), "display_error_signed_m": None}
            frame["errors_at_m"][str(int(x))] = raw_error
            if n1 is not None:
                visible = n1[i]["gauge"]["valid"] and 3 <= x <= n1[i]["gauge"]["solid_range_m"]
                point["N1_display_visible"] = bool(visible)
                point["within_N1_monitored"] = bool(x <= n1[i]["health"]["monitored_range"])
                if visible and display_coefs[i] is not None:
                    shown = float(np.polynomial.polynomial.polyval(x, display_coefs[i]))
                    display_error = shown - row["center"] - target
                    point["display_error_signed_m"] = display_error
                    display_errors.append(display_error)
                    same_visible_raw.append(raw_error)
                    display_self_anchor.append(shown - display_coefs[i][0] - target)
            points.append(point)
        frame_rows.append(frame)
    measured = case["honesty_v110"]
    assert len(monitored_new) == measured["steps_inside"]
    assert round(error_stats(monitored_new)["share_over_1.05m"], 3) == measured["inside_over_1.05m"]
    assert round(error_stats(monitored_old)["share_over_1.05m"], 3) == case["honesty_v100"]["inside_over_1.05m"]
    fixed = {}
    for distance in (40.0, 80.0, 90.0, 120.0, 135.0):
        values = []
        for row, path in zip(rows, truth):
            target = path_y(path, distance)
            if target is not None and distance <= min(row["axis_valid"], case["v110"]["range_max"]):
                values.append(lateral(row, distance) - row["center"] - target)
        fixed[str(int(distance))] = error_stats(values)
    for distance, bin_name in ((90, "80-100"), (135, "120-150")):
        for percentile in (50, 90, 99):
            assert round(fixed[str(distance)][f"p{percentile}"], 3) == case["measure_v110"]["offtrack"][bin_name]["within_trusted"][f"p{percentile}"]
    window_start, window_end = (140, 170) if label == "B" else (57, 117)
    window = {}
    for x in (80.0, 90.0, 100.0, 120.0, 135.0):
        values = []
        for i in range(window_start, window_end + 1):
            target = path_y(truth[i], x)
            if target is not None:
                values.append(lateral(rows[i], x) - rows[i]["center"] - target)
        window[str(int(x))] = error_stats(values)
    jitter = {}
    for j, x in enumerate(ANCHORS):
        raw_all, raw_visible, display_visible, visible_pairs, raw_3d, display_3d = [], [], [], [], [], []
        for i in range(1, expected):
            transform = prows[i]["T"]
            if transform is None:
                continue
            raw = compensated_step(raw_coefs[i - 1], raw_coefs[i], rows[i - 1]["R"], rows[i]["R"], transform, x)
            if raw is None:
                continue
            raw_all.append(raw)
            if n1 is None:
                continue
            a, b = n1[i - 1], n1[i]
            visible = a["gauge"]["valid"] and b["gauge"]["valid"] and min(
                a["gauge"]["solid_range_m"], b["gauge"]["solid_range_m"]) >= x
            if not visible:
                continue
            shown = compensated_step(display_coefs[i - 1], display_coefs[i], rows[i - 1]["R"], rows[i]["R"], transform, x)
            if shown is None:
                continue
            visible_pairs.append([i - 1, i])
            raw_visible.append(raw)
            display_visible.append(shown)
            raw_3d.append(float(np.hypot(b["raw_y"][j] - a["raw_y"][j], b["raw_z"][j] - a["raw_z"][j])))
            display_3d.append(float(np.hypot(b["display_y"][j] - a["display_y"][j], b["display_z"][j] - a["display_z"][j])))
        archived = case["measure_v110"]["jitter_compensated"][f"{int(x)}m"]
        assert len(raw_all) == archived["n"]
        for percentile in (50, 90):
            assert round(quantiles(raw_all)[f"p{percentile}"], 3) == archived[f"p{percentile}"]
        jitter[str(int(x))] = {"all_adjacent_pairs": expected - 1,
                              "raw_all_ICP_pairs_lateral_compensated_m": quantiles(raw_all),
                              "same_visible_pairs": visible_pairs if n1 is not None else None,
                              "raw_visible_lateral_compensated_m": quantiles(raw_visible) if n1 is not None else None,
                              "display_visible_lateral_compensated_m": quantiles(display_visible) if n1 is not None else None,
                              "raw_visible_3D_uncompensated_m": quantiles(raw_3d) if n1 is not None else None,
                              "display_visible_3D_uncompensated_m": quantiles(display_3d) if n1 is not None else None}
    return {"recording": BAGS[label], "frames": expected,
            "path_segments": pose_chain[-1][0] + 1, "ICP_fitness": quantiles([r["fitness"] for r in prows if r["T"] is not None]),
            "path_reference_frames": sum(len(p) > 1 for p in truth),
            "raw_axis_range_m": quantiles([min(r["axis_valid"], case["v110"]["range_max"]) for r in rows]),
            "monitored_v110_range_m": quantiles(case["monitored_v110"]),
            "monitored_v100_range_m": quantiles(case["monitored_v100"]),
            "raw_axis_error_all_reference_points": error_stats(all_errors),
            "raw_axis_error_within_axis_range": error_stats(axis_errors),
            "raw_axis_error_within_monitored_v100": error_stats(monitored_old),
            "raw_axis_error_within_monitored_v110": error_stats(monitored_new),
            "raw_axis_error_at_fixed_distance_within_axis": fixed,
            "prior_documented_curve_window": {"first_frame": window_start, "last_frame": window_end,
                                               "raw_error_where_path_available_regardless_of_trust": window},
            "display_available": n1 is not None,
            "N1_monitored_range_m": quantiles([r["health"]["monitored_range"] for r in n1]) if n1 else None,
            "display_solid_range_m": quantiles([r["gauge"]["solid_range_m"] for r in n1]) if n1 else None,
            "same_display_visible_raw_axis_error": error_stats(same_visible_raw) if n1 else None,
            "same_display_visible_display_error": error_stats(display_errors) if n1 else None,
            "display_self_origin_alignment_sensitivity": error_stats(display_self_anchor) if n1 else None,
            "jitter_metrics_kept_separate": jitter,
            "archived_B6_numeric_results_reproduced": True}, frame_rows, points


def main():
    cases, n1, n1_report, identities = input_data()
    alignment = check_alignment(cases["B"], n1)
    reports, records = {}, {}
    for label, case in cases.items():
        report, frames, points = analyze_case(label, case, n1 if label == "B" else None)
        reports[label] = report
        records[label] = {"frames": frames, "points": points}
    for x in ANCHORS:
        got = reports["B"]["jitter_metrics_kept_separate"][str(int(x))]
        old = n1_report["jitter"][str(int(x))]
        assert len(got["same_visible_pairs"]) == old["same_supported_adjacent_pairs"]
        assert abs(got["display_visible_3D_uncompensated_m"]["p90"] - old["display_3d_vertex_step_m"]["p90"]) < 1e-14
    row_bytes = gzip.compress(json.dumps(records, separators=(",", ":")).encode(), mtime=0)
    (HERE / "crosswalk_rows.json.gz").write_bytes(row_bytes)
    result = {"schema": "offline-curve-crosswalk-v1", "complete": True,
              "no_detector_or_ICP_rerun": True, "P4_evidence_commit": P4_COMMIT,
              "N1_evidence_commit": LOCAL_EVIDENCE, "N1_measured_source": "f5ff15f",
              "script_sha256": sha(Path(__file__).read_bytes()), "inputs": identities,
              "row_archive_sha256": sha(row_bytes), "B_alignment": alignment, "recordings": reports,
              "method": "Archived B6 ICP path, relative to the current raw axis center at x=0. Lateral error is shape/trajectory error, not surveyed absolute track-center error. Saved N1 display lateral profiles remain quadratic under the hash-verified spatially uniform EMA/reset; reconstruct them from three full-precision saved samples. Common current-raw-center anchoring retains display-center lag; a self-origin sensitivity is separate. Integer 5m samples match display grid nodes.",
              "limits": ["C has no saved N1 display capture; its display metrics are unavailable, not zero or passing.",
                         "B6 lacks source payload hashes and timestamps. Exact raw geometry matches at all252 B frames support correspondence; byte-identical source-point inputs are not established.",
                         "ICP is a future driven-sensor path proxy, independently corroborated in prior B6 review, not a surveyed track center. No truth is extrapolated beyond the saved forward path or across segment breaks.",
                         "Motion-compensated lateral centerline steps use the B6 z=0 convention and are not the N1 uncorrected 3D vertex metric. Only identical visible frame pairs are compared within each metric.",
                         "N1 rows retain their measured f5ff15f source; this offline crosswalk is not a new replay of the later selected detector/version.",
                         "A reduced error fraction after hiding far range is not improved detector curvature; availability and same-point errors are reported separately."]}
    (HERE / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"complete": True, "B_frames": 252, "C_frames": 268,
                      "alignment": alignment, "reports": reports}, indent=2))


if __name__ == "__main__":
    main()
