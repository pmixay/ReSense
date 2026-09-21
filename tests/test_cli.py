"""CLI round trips on the synthetic tunnel (Open3D): labelled cached frames through
``eval --npy --gt`` (docs/DATASET.md "Label format"), and ``inject`` options through
``eval`` on an injected dataset."""
import json
import os

import numpy as np
import pytest

from resense.cli import run_cli
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
    out = run_cli(["eval", "--npy", str(d), "--gt", str(d / "gt.json"), "--repeat", "3", "--out", str(jsonl)])
    assert out["frames"] == 3 and out["empty_frames"] == 2 and out["gt_frames"] == 2
    assert out["recall"] == 1.0 and out["recall_by_class"] == {"box0.5": 1.0}
    assert out["first_detection_distance"] == {"box_a": 40.0}
    assert out["fp_frames"] == 0 and out["fp_events"] == 0 and out["alarm_events"] == 1
    assert out["frame_stride"] == 5 and "every 5th" in out["stride_caveat"]
    lines = [json.loads(l) for l in open(jsonl)]
    assert [l["frame"] for l in lines] == [0, 5, 10]          # keys come from the file names
    assert lines[2]["obstacle"] and abs(lines[2]["nearest_distance"] - 40.0) < 2.0
    # summarize on the JSONL reproduces the evaluation
    s = run_cli(["summarize", str(jsonl), "--gt", str(d / "gt.json"), "--json"])
    assert s["recall"] == 1.0 and s["fp_events"] == 0 and s["alarm_frames"] == 1


def test_eval_npy_labelled_only_and_stride(labelled_npy):
    d = labelled_npy
    out = run_cli(["eval", "--npy", str(d), "--gt", str(d / "gt.json"), "--labelled-only", "--text"])
    assert out["frames"] == 2 and out["frames_processed"] == 3     # frame 5 processed but not counted
    assert out["repeat"] == 1 and out["recall"] == 0.0              # a bag / npy source is processed once per frame:
    out = run_cli(["eval", "--npy", str(d), "--gt", str(d / "gt.json"), "--every", "2", "--repeat", "3"])
    assert out["frames"] == 2 and out["recall"] == 1.0 and out["frame_stride"] == 10   # ... persistence needs --repeat
    with pytest.raises(SystemExit):
        run_cli(["eval", "--npy", str(d)])                            # labels are required for a bag / npy source


def test_eval_gt_bbox_row(labelled_npy, tmp_path):
    """A label-tool row with only a vehicle-frame bbox is matched like an inject row."""
    d = labelled_npy
    gt = json.loads((d / "gt.json").read_text())
    box = gt["00010"][0]
    gt["00010"] = [{"bbox": [[40.0, -0.3 + 0.25, -0.5], [40.6, 0.3 + 0.25, 0.1]], "label": "box_bbox", "kind": "box"}]
    del box
    p = tmp_path / "gt_bbox.json"
    p.write_text(json.dumps(gt))
    out = run_cli(["eval", "--npy", str(d), "--gt", str(p), "--repeat", "3"])
    assert out["recall"] == 1.0 and out["first_detection_distance"] == {"box_bbox": 40.0}


# --- resense inject: catalogue, sequences, augmentation -> resense eval round trip -----------

def test_catalogue_spec_and_unknown_name():
    from resense.synthetic import OBJECT_CATALOGUE, catalogue_spec
    assert {"person", "hivis", "box0.2", "box0.5", "box1.0", "box", "plank", "trolley", "cylinder", "sphere"} <= set(OBJECT_CATALOGUE)
    assert OBJECT_CATALOGUE["box0.2"].size == (0.2, 0.2, 0.2) and OBJECT_CATALOGUE["box"].size == OBJECT_CATALOGUE["box0.5"].size
    rng = np.random.default_rng(0)
    for name, e in OBJECT_CATALOGUE.items():
        s = catalogue_spec(name, 50.0, rng=rng)
        assert s.kind == e.kind and s.size == e.size and e.reflectivity[0] <= s.reflectivity <= e.reflectivity[1]
    assert catalogue_spec("hivis", 10.0, rng=rng).reflectivity >= 150      # retro-reflective vest
    assert catalogue_spec("person", 10.0, reflectivity=33.0).reflectivity == 33.0
    with pytest.raises(KeyError):
        catalogue_spec("piano", 10.0)
    with pytest.raises(SystemExit):
        run_cli(["inject", "--npy", "/nonexistent", "--out", "/tmp/never", "--kinds", "piano"])


def test_inject_static_roundtrip(synth_npy_dir, tmp_path):
    """Two backgrounds, one catalogue object each at 35 m inside the gauge -> eval finds both."""
    out = tmp_path / "inj"
    run_cli(["inject", "--npy", str(synth_npy_dir), "--out", str(out), "--kinds", "box0.5,person",
          "--distances", "35:35", "--negative-fraction", "0", "--seed", "3"])
    gt = json.loads((out / "gt.json").read_text())
    assert gt["_meta"]["source"] == "inject" and gt["_meta"]["sequence"] == 1
    rows = [gt[k][0] for k in sorted(k for k in gt if not k.startswith("_"))]
    assert len(rows) == 2 and sorted(os.listdir(out)) == ["00000.npz", "00001.npz", "gt.json"]
    for r in rows:   # the keys inject has always written, plus the additive ones
        assert {"kind", "size", "distance", "lateral", "yaw_deg", "reflectivity", "label", "in_gauge", "n_points"} <= set(r)
        assert r["name"] in ("box0.5", "person") and r["in_gauge"] and r["n_points"] > 0
        assert r["seq_step"] == 0 and r["speed_mps"] == 0.0
    z = np.load(out / "00000.npz")
    assert {"xyz", "intensity", "labels", "stamp"} <= set(z.files) and (z["labels"] > 0).sum() == rows[0]["n_points"]
    res = run_cli(["eval", str(out)])
    assert res["repeat"] == 3 and res["frames"] == 2 and res["recall"] == 1.0 and res["fp_events"] == 0
    assert set(res["recall_by_class"]) <= {"box0.5", "person"}


def test_inject_sequence_and_augment_roundtrip(synth_npy_dir, tmp_path):
    """One background, an approach sequence of 4 steps at 20 m/s (2 m per step) with an
    augmented background: files in order, rows carry seq / seq_step / speed_mps, and eval with
    the automatic --repeat 1 confirms the object before the last step."""
    out = tmp_path / "seq"
    run_cli(["inject", "--npy", str(synth_npy_dir), "--limit", "1", "--out", str(out), "--kinds", "box1.0",
          "--distances", "50:50", "--negative-fraction", "0", "--sequence", "4", "--speed", "20", "--augment",
          "--seed", "5"])
    gt = json.loads((out / "gt.json").read_text())
    keys = sorted(k for k in gt if not k.startswith("_"))
    assert keys == ["00000", "00001", "00002", "00003"] and gt["_meta"]["augment"] is True
    dists = [gt[k][0]["distance"] for k in keys]
    assert dists == pytest.approx([50.0, 48.0, 46.0, 44.0])
    assert [gt[k][0]["seq_step"] for k in keys] == [0, 1, 2, 3]
    assert all(gt[k][0]["seq"] == 0 and gt[k][0]["speed_mps"] == 20.0 and gt[k][0]["label"] == "box1.0_0_0" for k in keys)
    stamps = [float(np.load(out / (k + ".npz"))["stamp"]) for k in keys]
    assert np.allclose(np.diff(stamps), 0.1)
    res = run_cli(["eval", str(out)])
    assert res["repeat"] == 1 and res["frames"] == 4
    assert res["first_detection_distance"]["box1.0_0_0"] >= 44.0        # confirmed by the last step at the latest
    assert res["fp_events"] == 0
    # negatives outside the gauge must not alarm and are not counted as gauge ground truth
    out2 = tmp_path / "neg"
    run_cli(["inject", "--npy", str(synth_npy_dir), "--limit", "1", "--out", str(out2), "--kinds", "plank",
          "--distances", "30:30", "--negative-fraction", "1", "--seed", "6"])
    gt2 = json.loads((out2 / "gt.json").read_text())
    assert gt2["00000"][0]["in_gauge"] is False and abs(gt2["00000"][0]["lateral"]) > 2.0
    res2 = run_cli(["eval", str(out2)])
    assert res2["empty_frames"] == 1 and res2["recall"] is None and res2["fp_frames"] == 0
