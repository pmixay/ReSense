"""Summarize all raw Falcon frames and independent static-background changes."""
from collections import Counter
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


def main():
    folder = Path(__file__).resolve().parent
    rows = [json.loads(line) for line in (folder / "frame_characterization.jsonl").read_text().splitlines()]
    metadata = json.loads(Path("/home/resense/data/decoded/falcon_test_second_dark/meta.json").read_text())
    assert len(rows) == len(metadata) == 4443
    first = rows[0]["stamp"]
    bins = {}
    for row in rows:
        bins.setdefault(int((row["stamp"] - first) // 50), []).append(row)
    windows = []
    for index, window in bins.items():
        windows.append({"time_s": [50 * index, min(50 * (index + 1), rows[-1]["stamp"] - first)],
                        "frame_indices": [window[0]["frame"], window[-1]["frame"]], "frames": len(window),
                        "returns_median": float(np.median([row["finite_returns"] for row in window])),
                        "node_returns_median": float(np.median([row["node_returns"] for row in window])),
                        "maximum_raw_range_m": max(row["range_quantiles_m"][-1] for row in window),
                        "points_beyond250_per_frame_median": float(np.median([row["range_counts_gt_m"]["250"] for row in window])),
                        "intensity_median": float(np.median([row["intensity_quantiles"][1] for row in window]))})
    cache = Path("/home/resense/data/decoded/falcon_test_second_dark")
    with np.load(cache / "f_00000.npz") as data:
        reference = data["xyz"]
    reference = reference[(reference[:, 0] > 4) & (reference[:, 0] < 80)]
    tree = cKDTree(reference)
    geometry = []
    for index in sorted(set(range(0, 4443, 100)) | {4442}):
        with np.load(cache / f"f_{index:05d}.npz") as data:
            points = data["xyz"]
        points = points[(points[:, 0] > 4) & (points[:, 0] < 80)]
        _, selected = np.unique(np.floor(points / .25).astype(np.int32), axis=0, return_index=True)
        points = points[np.sort(selected)]
        distance = tree.query(points)[0]
        geometry.append({"frame": index, "voxel_selected_points": len(points),
                         "nearest_reference_distance_median_p90_m": np.percentile(distance, [50, 90]).tolist(),
                         "fraction_within_0_15_m": float(np.mean(distance <= .15))})
    summary = {"frames": len(rows), "duration_header_s": rows[-1]["stamp"] - first,
               "header_gap_s_min_median_max": np.percentile(np.diff([row["stamp"] for row in rows]), [0, 50, 100]).tolist(),
               "topics": dict(Counter(row["topic"] for row in metadata)),
               "frame_ids": dict(Counter(row["frame_id"] for row in metadata)),
               "all_missing_ring": all(not row["has_ring"] for row in metadata),
               "second_return_flagged_points_total": sum(row["second_return_flags"] for row in rows),
               "raw_returns_min_median_max": np.percentile([row["finite_returns"] for row in rows], [0, 50, 100]).tolist(),
               "raw_range_max_m": max(row["range_quantiles_m"][-1] for row in rows),
               "scan_id_bounds": [min(row["scan_id_bounds"][0] for row in rows), max(row["scan_id_bounds"][1] for row in rows)],
               "azimuth_bounds_deg": [min(row["azimuth_bounds_deg"][0] for row in rows), max(row["azimuth_bounds_deg"][1] for row in rows)],
               "elevation_bounds_deg": [min(row["elevation_bounds_deg"][0] for row in rows), max(row["elevation_bounds_deg"][1] for row in rows)],
               "windows": windows, "background_geometry": geometry,
               "background_geometry_method": "Every100frames plus final: 0.25m voxel representatives at raw forward4..80m, nearest original frame0 returns. This tests scene consistency, not calibrated odometry or exhaustive motion truth."}
    (folder / "characterization_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({key: value for key, value in summary.items() if key not in ("windows", "background_geometry")}))


if __name__ == "__main__":
    main()
