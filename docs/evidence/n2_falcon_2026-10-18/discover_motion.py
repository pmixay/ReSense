"""Independent raw-cloud temporal discovery; no detector output defines candidates."""
import json
from pathlib import Path

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree


def region(points):
    # A broad discovery volume, not a ground-truth gauge: retain upper surfaces
    # relative to the near bed slope and inspect trajectories manually afterward.
    height = points[:, 2] + np.tan(np.radians(2.39)) * points[:, 0] + 1.77
    return (points[:, 0] > 2.5) & (points[:, 0] < 250) & (np.abs(points[:, 1]) < 5) & (height > .25) & (height < 2.8)


def main():
    folder = Path(__file__).resolve().parent
    cache = Path("/home/resense/data/decoded/falcon_test_second_dark")
    initial = []
    for index in (0, 250, 500, 750):
        with np.load(cache / f"f_{index:05d}.npz") as data:
            points = data["xyz"]
        initial.append(points[region(points)])
    reference = cKDTree(np.concatenate(initial))
    rows = []
    for index in sorted(set(range(0, 4443, 25)) | {4442}):
        with np.load(cache / f"f_{index:05d}.npz") as data:
            points = data["xyz"]
        points = points[region(points)]
        distance = reference.query(points)[0]
        novel = points[distance > .25]
        components = []
        if len(novel):
            pairs = cKDTree(novel).query_pairs(.8, output_type="ndarray")
            graph = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(len(novel), len(novel)))
            count, labels = connected_components(graph, directed=False)
            for label in range(count):
                group = novel[labels == label]
                if len(group) < 4:
                    continue
                size = np.ptp(group, axis=0)
                if size[0] > 3 or size[1] > 2.5 or size[2] > 3:
                    continue
                components.append({"points": len(group), "bbox": [group.min(axis=0).tolist(), group.max(axis=0).tolist()],
                                   "center": np.median(group, axis=0).tolist(), "size": size.tolist()})
        rows.append({"frame": index, "new_points": len(novel), "components": components})
    (folder / "motion_discovery.json").write_text(json.dumps({
        "method": "Every25frames plus final, raw2.5..250m/left±5m/broad height volume, >0.25m from union of four initial raw frames, connected components0.8m. These are discovery proposals, not exact labels or exhaustive negative truth.",
        "background_frames": [0, 250, 500, 750], "rows": rows}, indent=2) + "\n")
    print(json.dumps([{"frame": row["frame"], "components": [(round(c["center"][0], 1), round(c["center"][1], 2), c["points"]) for c in row["components"]]} for row in rows]))


if __name__ == "__main__":
    main()
