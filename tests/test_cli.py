"""CLI round trips on the synthetic tunnel (Open3D): labelled cached frames through
``eval --npy --gt`` (docs/DATASET.md "Label format"), and ``inject`` options through
``eval`` on an injected dataset."""
import json
import os

import numpy as np
import pytest

from resense.cli import main
from resense.config import SensorConfig
from resense.frame import axis_matrix
from resense.io import npy_frame_index
from resense.pointcloud import COMPACT_DTYPE
from resense.synthetic import ObstacleSpec, inject_obstacles


def save_compact(frame, path):
    """Vehicle-frame Frame -> compact sensor-frame *.npy as scripts/cache_frames.py writes it."""
    R = axis_matrix(SensorConfig())
    xyz_s = frame.xyz @ R
    arr = np.zeros(frame.n, COMPACT_DTYPE)
    arr["x"], arr["y"], arr["z"] = xyz_s.T
    arr["intensity"] = frame.intensity
    np.save(path, arr)


@pytest.fixture(scope="module")
def labelled_npy(tunnel, tmp_path_factory):
    """Cached frames 0 and 5 clear, frame 10 with a 0.6 m box at 40 m, and the gt.json
    that a label tool would export for them (frame 5 unlabelled)."""
    frame, _, gt = tunnel
    spec = ObstacleSpec(kind="box", size=(0.6, 0.6, 0.6), distance=40.0, lateral=0.0, reflectivity=60, label="box_a")
    inj = inject_obstacles(frame, gt, [spec], rng=np.random.default_rng(2))
    d = tmp_path_factory.mktemp("labelled")
    save_compact(frame, d / "synthetic_0000.npy")
    save_compact(frame, d / "synthetic_0005.npy")
    save_compact(inj.frame, d / "synthetic_0010.npy")
    labels = {"_meta": {"bag": "synthetic", "source": "test", "coords": "vehicle"},
              "00000": [],
              "00010": [dict(spec.to_dict(), name="box0.5", in_gauge=True)]}
    (d / "gt.json").write_text(json.dumps(labels, indent=1))
    return d


def test_npy_frame_index_from_name():
    assert npy_frame_index("cache/roundT_doubleT_0120.npy") == 120
    assert npy_frame_index("frame_0000.npy") == 0
    assert npy_frame_index("noindex.npy") is None


def test_eval_npy_against_labels(labelled_npy, tmp_path):
    d = labelled_npy
    jsonl = tmp_path / "res.jsonl"
    out = main(["eval", "--npy", str(d), "--gt", str(d / "gt.json"), "--repeat", "3", "--out", str(jsonl)])
    assert out["frames"] == 3 and out["empty_frames"] == 2 and out["gt_frames"] == 2
    assert out["recall"] == 1.0 and out["recall_by_class"] == {"box0.5": 1.0}
    assert out["first_detection_distance"] == {"box_a": 40.0}
    assert out["fp_frames"] == 0 and out["fp_events"] == 0 and out["alarm_events"] == 1
    assert out["frame_stride"] == 5 and "every 5th" in out["stride_caveat"]
    lines = [json.loads(l) for l in open(jsonl)]
    assert [l["frame"] for l in lines] == [0, 5, 10]          # keys come from the file names
    assert lines[2]["obstacle"] and abs(lines[2]["nearest_distance"] - 40.0) < 2.0
    # summarize on the JSONL reproduces the evaluation
    s = main(["summarize", str(jsonl), "--gt", str(d / "gt.json"), "--json"])
    assert s["recall"] == 1.0 and s["fp_events"] == 0 and s["alarm_frames"] == 1


def test_eval_npy_labelled_only_and_stride(labelled_npy):
    d = labelled_npy
    out = main(["eval", "--npy", str(d), "--gt", str(d / "gt.json"), "--labelled-only", "--text"])
    assert out["frames"] == 2 and out["frames_processed"] == 3     # frame 5 processed but not counted
    out = main(["eval", "--npy", str(d), "--gt", str(d / "gt.json"), "--every", "2"])
    assert out["frames"] == 2 and out["recall"] == 1.0 and out["frame_stride"] == 10
    with pytest.raises(SystemExit):
        main(["eval", "--npy", str(d)])                            # labels are required for a bag / npy source


def test_eval_gt_bbox_row(labelled_npy, tmp_path):
    """A label-tool row with only a vehicle-frame bbox is matched like an inject row."""
    d = labelled_npy
    gt = json.loads((d / "gt.json").read_text())
    box = gt["00010"][0]
    gt["00010"] = [{"bbox": [[40.0, -0.3 + 0.25, -0.5], [40.6, 0.3 + 0.25, 0.1]], "label": "box_bbox", "kind": "box"}]
    del box
    p = tmp_path / "gt_bbox.json"
    p.write_text(json.dumps(gt))
    out = main(["eval", "--npy", str(d), "--gt", str(p)])
    assert out["recall"] == 1.0 and out["first_detection_distance"] == {"box_bbox": 40.0}
