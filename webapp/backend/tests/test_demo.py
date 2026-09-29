"""Synthetic demo recordings: bag layout, geometry, and what the sealed detector (default config)
answers on short versions of the three scenarios.

Measured with the default config (seed 0; 15 s unless noted), for reference:
* approach: first STOP on frame 4 at 137.4 m (person first 142.3 m ahead), STOP on every later
  frame down to the stop at 25.3 m; 30 s: first STOP at 199.9 m, as the person comes into range;
* crossing: STOP from 0.4 s after the person enters the envelope to 0.3-0.4 s after it leaves,
  on both crossings; GO before and between, CAUTION while it is in the advisory band;
* clear: no STOP (CAUTION next to the equipment cabinets and marker posts beside the envelope).
"""
from __future__ import annotations

import json
import time

import numpy as np
import pytest
import yaml

from resense.detector import Detector
from resense.io import bag_info, iter_bag_compact, iter_bag_frames
from resense_web import demo, evaluation
from resense_web.decision import decision_of
from resense_web.params import build_config

SEED = 0


def _run(tmp_path_factory, scenario: str, seconds: float) -> dict:
    out = tmp_path_factory.mktemp("demo") / f"demo_{scenario}"
    seen = []
    t0 = time.perf_counter()
    info = demo.generate_demo_bag(out, scenario, seconds=seconds, seed=SEED, progress=seen.append)
    gen_s = (time.perf_counter() - t0) / info["n_frames"]
    gt = json.loads((out / demo.GROUND_TRUTH).read_text(encoding="utf-8"))
    cfg = build_config({})                            # configs/default.yaml
    det = Detector(cfg)
    frames, clouds = [], []
    for i, fr in iter_bag_frames(str(out), cfg.sensor):
        d = det.process(fr).to_dict()
        d["frame"] = i
        d["decision"] = decision_of(d)
        frames.append(d)
        clouds.append(fr.xyz)
    return {"dir": out, "info": info, "gt": gt, "frames": frames, "clouds": clouds, "progress": seen,
            "gen_s": gen_s, "letters": "".join(f["decision"][0] for f in frames)}


@pytest.fixture(scope="module")
def approach(tmp_path_factory):
    return _run(tmp_path_factory, "approach", 5.0)


@pytest.fixture(scope="module")
def crossing(tmp_path_factory):
    return _run(tmp_path_factory, "crossing", 6.0)


@pytest.fixture(scope="module")
def clear(tmp_path_factory):
    return _run(tmp_path_factory, "clear", 5.0)


def _gt_rows(r, i):
    return r["gt"][f"{i:05d}"]


def test_bag_layout(approach):
    info, out = approach["info"], approach["dir"]
    assert info == {"name": "demo_approach", "n_frames": 50, "duration_s": 4.9, "topic": "/lidar_points",
                    "frame_id": "hesai_lidar", "scenario": "approach"}
    assert sorted(p.name for p in out.iterdir()) == ["demo_approach_0.db3", "ground_truth.json", "metadata.yaml"]
    meta = yaml.safe_load((out / "metadata.yaml").read_text())["rosbag2_bagfile_information"]
    assert meta["version"] == 5 and meta["storage_identifier"] == "sqlite3" and meta["message_count"] == 50
    bi = bag_info(str(out))
    assert bi["topics"] == [("/lidar_points", "sensor_msgs/msg/PointCloud2", 50)]
    assert bi["duration_s"] == pytest.approx(4.9)
    i, stamp, frame_id, arr = next(iter_bag_compact(str(out)))
    assert (i, frame_id) == (0, "hesai_lidar") and stamp == pytest.approx(1.7e9)
    assert 100_000 < arr.size <= 128_128
    assert set(arr.dtype.names) >= {"x", "y", "z", "intensity", "ring"}
    assert np.unique(arr["ring"]).size == 128
    p = approach["progress"]
    assert p[0] == 0.0 and p[-1] == 1.0 and all(b >= a for a, b in zip(p, p[1:]))
    assert approach["gen_s"] < 0.5          # ~0.06-0.07 s per frame on a 4-core VM


def test_cdr_matches_rosbags():
    rosbags = pytest.importorskip("rosbags.typesys")
    ts = rosbags.get_typestore(rosbags.Stores.ROS2_HUMBLE)
    T = ts.types
    pts = np.zeros(5, dtype=demo.POINT_DTYPE)
    pts["x"], pts["ring"], pts["timestamp"] = np.arange(5), 7, 946684800.5
    stamp = 1_700_000_000_123_456_789
    fields = [T["sensor_msgs/msg/PointField"](name=n, offset=o, datatype=t, count=1) for n, o, t in demo.POINT_FIELDS]
    header = T["std_msgs/msg/Header"](stamp=T["builtin_interfaces/msg/Time"](sec=stamp // 10 ** 9,
                                                                             nanosec=stamp % 10 ** 9),
                                      frame_id=demo.FRAME_ID)
    msg = T[demo.MSGTYPE](header=header, height=1, width=5, fields=fields, is_bigendian=False, point_step=26,
                          row_step=130, data=np.frombuffer(pts.tobytes(), dtype=np.uint8), is_dense=False)
    assert bytes(ts.serialize_cdr(msg, demo.MSGTYPE)) == demo.pointcloud2_cdr(pts, stamp)


def test_ground_truth_is_a_label_file(approach, crossing, clear):
    for r in (approach, crossing, clear):
        evaluation.validate_labels(r["gt"])
        assert r["gt"]["_meta"]["bag"] == r["info"]["name"]
        assert len([k for k in r["gt"] if not k.startswith("_")]) == r["info"]["n_frames"]
    assert all(_gt_rows(clear, i) == [] for i in range(clear["info"]["n_frames"]))


def _in_envelope(xyz: np.ndarray) -> np.ndarray:
    dy = xyz[:, 1] - demo.TRACK_Y
    h = xyz[:, 2] - demo.RAIL_TOP
    return (xyz[:, 0] > 3.0) & (np.abs(dy) <= 1.05) & (h >= 0.12) & (h <= 3.0)


def test_no_scenery_inside_the_envelope(clear, approach):
    # the tunnel furniture never enters the 2.1 x 3.0 m envelope; the person does
    assert max(int(_in_envelope(c).sum()) for c in clear["clouds"]) == 0
    assert all(_in_envelope(c).sum() >= 5 for c in approach["clouds"])


def test_clear_has_no_stop(clear):
    assert "S" not in clear["letters"], clear["letters"]
    assert "F" not in clear["letters"]
    s = evaluation.evaluate(clear["frames"], clear["dir"] / demo.GROUND_TRUTH)
    assert s["false_stop_frames"] == 0 and s["frames_with_object_in_gauge"] == 0


def test_approach_stops_well_before_the_train(approach):
    letters, frames, gt = approach["letters"], approach["frames"], approach["gt"]
    speed = gt["_meta"]["speed_mps"]
    first = letters.index("S")
    stopped = speed.index(0.0)
    assert first <= 5, letters                       # 0.5 s confirmation at 10 Hz
    assert stopped - first >= 30                     # >= 3 s before the train stands
    d_first = frames[first]["nearest_distance"]
    assert d_first == pytest.approx(_gt_rows(approach, first)[0]["distance"], abs=1.0)
    assert d_first > _gt_rows(approach, stopped)[0]["distance"] + 8.0
    assert letters[first:] == "S" * (len(letters) - first), letters
    assert frames[-1]["nearest_distance"] == pytest.approx(_gt_rows(approach, len(frames) - 1)[0]["distance"], abs=0.5)
    s = evaluation.evaluate(frames, approach["dir"] / demo.GROUND_TRUTH)
    assert s["false_stop_frames"] == 0 and s["recall"] >= 0.85


def test_crossing_stops_while_the_person_is_inside(crossing):
    letters = crossing["letters"]
    inside = [bool(_gt_rows(crossing, i)[0]["in_gauge"]) for i in range(len(letters))]
    assert "S" in letters and letters[0] == "G"
    assert crossing["gt"]["_meta"]["speed_mps"] == [0.0] * len(letters)          # the train stands
    for i, c in enumerate(letters):
        if c == "S":            # never STOP unless the person was inside within the last 0.6 s
            assert any(inside[max(0, i - 6): i + 1]), (i, letters)
        elif not any(inside[max(0, i - 6): i + 1]):
            assert c in "GC", (i, letters)
    n_in = sum(inside)
    assert n_in >= 15
    assert sum(1 for c, x in zip(letters, inside) if x and c == "S") >= 0.7 * n_in
    first_in = inside.index(True)
    assert first_in < letters.index("S") <= first_in + 5
    d = [f["nearest_distance"] for f in crossing["frames"] if f["obstacle"]]
    assert max(abs(v - _gt_rows(crossing, 0)[0]["distance"]) for v in d) < 1.0
    s = evaluation.evaluate(crossing["frames"], crossing["dir"] / demo.GROUND_TRUTH)
    assert s["recall"] >= 0.7 and s["false_stop_frames"] <= 6 and s["false_stop_episodes"] <= 1


@pytest.mark.parametrize("kw", [
    {"scenario": "flyby"},
    {"scenario": None},
    {"seconds": 0.5},
    {"seconds": 500},
    {"seconds": float("nan")},
    {"seconds": "10"},
    {"seed": -1},
    {"seed": 1.5},
    {"seed": True},
])
def test_bad_arguments(tmp_path, kw):
    args = {"scenario": "clear", "seconds": 2.0, "seed": 0, **kw}
    with pytest.raises(ValueError) as e:
        demo.generate_demo_bag(tmp_path / "bag", **args)
    assert any("а" <= ch <= "я" for ch in str(e.value).lower())
    assert not (tmp_path / "bag" / "metadata.yaml").exists()


def test_deterministic_for_a_seed(tmp_path):
    a = demo.generate_demo_bag(tmp_path / "a", "crossing", seconds=1.0, seed=5)
    b = demo.generate_demo_bag(tmp_path / "b", "crossing", seconds=1.0, seed=5)
    assert a["n_frames"] == b["n_frames"] == 10
    xa = [arr for _, _, _, arr in iter_bag_compact(str(tmp_path / "a"))]
    xb = [arr for _, _, _, arr in iter_bag_compact(str(tmp_path / "b"))]
    assert all(np.array_equal(p, q) for p, q in zip(xa, xb))
