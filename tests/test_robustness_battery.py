"""X3 evidence must fail closed; transforms must remain the judge's transforms."""
import copy
import importlib.util
import json
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import robustness_battery as battery


def meta(n=3):
    return [{"i": i, "stamp": 100 + i * .1, "bag_t": 200 + i * .1,
             "topic": "/cloud", "frame_id": "lidar", "has_ring": True,
             "n_raw": 100, "n_near": 0} for i in range(n)]


def row(m, stop=False):
    r = dict.fromkeys(battery.RECORD_KEYS)
    r.update({k: m[k] for k in ("i", "stamp", "bag_t", "topic", "frame_id")})
    r.update(decision="STOP" if stop else "GO", obstacle=stop, warning=False, warns=[],
             dets=[detection()] if stop else [], n_points=100, level="ok", dlevel="ok",
             decode_ms=0., detect_ms=0., total_ms=0., clear=100.)
    return r


def detection():
    return {"d": 50., "lat": 0., "c": [50., 0., 1.], "size": [1., 1., 1.],
            "zone": "gauge", "kind": "box", "reason": "", "conf": 1., "n": 20,
            "age": 3, "hmin": 0.}


def raw(tmp_path, rows):
    p = tmp_path / "run.jsonl"
    p.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return p


@pytest.mark.parametrize("corruption", ["truncated", "extra", "duplicate", "stamp", "decision",
                                         "missing", "detection", "json", "nan"])
def test_corrupt_reports_are_not_accepted(tmp_path, corruption):
    ms = meta()
    rs = [row(m, True) for m in ms]
    if corruption == "truncated":
        rs.pop()
    elif corruption == "extra":
        rs.append(rs[-1])
    elif corruption == "duplicate":
        rs[1] = rs[0]
    elif corruption == "stamp":
        rs[1]["stamp"] += .01
    elif corruption == "decision":
        rs[1]["decision"] = "GO"
    elif corruption == "missing":
        del rs[1]["dets"]
    elif corruption == "detection":
        del rs[1]["dets"][0]["c"]
    elif corruption == "nan":
        rs[1]["dets"][0]["d"] = float("nan")
    p = raw(tmp_path, rs)
    if corruption == "json":
        p.write_text('{"i":', encoding="utf-8")
    with pytest.raises((ValueError, KeyError, TypeError)):
        battery.checked_rows(p, ms)


def test_5hz_keeps_original_indices_and_counts_processed_transitions(tmp_path):
    ms = meta(5)
    rows = [row(ms[i], i != 4) for i in (0, 2, 4)]
    actual = battery.checked_rows(raw(tmp_path, rows), ms, every=2)
    assert battery.summarize(actual)["stop_episodes"] == 1
    assert [r["i"] for r in actual] == [0, 2, 4]


def test_object_matching_outside_and_unmatched_are_separate():
    rs = [row(m, True) for m in meta()]
    label = {"distance": 50., "size": [1., 1., 1.], "bbox": [[49.5, -.5, 0], [50.5, .5, 2]],
             "in_gauge": True, "label": "inside", "n_points": 2}
    outside = dict(label, label="outside", in_gauge=False)
    labels = {"00000": [label], "00001": [outside]}
    s = battery.summarize(rs, labels)
    assert s["objects"]["inside"]["stop_rows"] == 1
    assert s["objects"]["outside"]["stop_rows"] == 1
    assert s["outside_false_stop_episodes"] == 1
    assert s["unmatched_stop_frames"] == 1
    assert s["unmatched_stop_episodes"] == 1
    assert not battery.matches(dict(detection(), c=[50., 3., 0.]), label)


def test_directional_worse_not_absolute_difference():
    base = {"frames": 20, "false_stop_episodes": 10}
    good = battery.compare_metrics(base, dict(base, false_stop_episodes=1))[-1]
    assert good == {"metric": "false_stop_episodes", "baseline": 10, "current": 1,
                    "delta": -9, "absolute_delta": 9, "worse_by": 0, "tolerance": 1, "passed": True}
    assert battery.compare_metrics(base, dict(base, false_stop_episodes=11))[-1]["passed"]
    assert not battery.compare_metrics(base, dict(base, false_stop_episodes=12))[-1]["passed"]
    assert not battery.compare_metrics(base, dict(base, frames=19))[0]["passed"]


def test_positive_object_loss_cannot_hide_in_total_stop_count():
    base = battery.summarize([row(m, True) for m in meta()], {})
    base["objects"] = {"person": {"in_gauge": True, "visible_rows": 20, "inside_stop_rows": 10,
                                  "inside_visible_rows": 20, "outside_visible_rows": 0}}
    changed = copy.deepcopy(base)
    changed["objects"]["person"]["inside_stop_rows"] = 7
    comparison = battery.compare_metrics(base, changed)
    assert not next(r for r in comparison if r["metric"] == "objects.person.inside_stop_rows")["passed"]
    changed["objects"]["person"]["inside_stop_rows"] = 8
    assert all(r["passed"] for r in battery.compare_metrics(base, changed))
    changed["objects"]["person"]["visible_rows"] = 19
    with pytest.raises(ValueError, match="denominator"):
        battery.compare_metrics(base, changed)


def test_incomplete_reference_and_cache_rejected(tmp_path):
    with pytest.raises(ValueError, match="incomplete reference"):
        battery.validated_entries({"entries": {}, "errors": []}, tmp_path, tmp_path)
    (tmp_path / "meta.json").write_text(json.dumps(meta()), encoding="utf-8")
    with pytest.raises(ValueError, match="incomplete or extra"):
        battery.cache_meta(tmp_path, 3)


def test_crossing_label_scored_by_each_rows_intent():
    rs = [row(m, True) for m in meta()]
    outside = {"label": "crossing", "in_gauge": False, "distance": 50., "lateral": 0.}
    inside = dict(outside, in_gauge=True)
    labels = {"00000": [outside], "00001": [inside], "00002": [outside]}
    result = battery.summarize(rs, labels)
    obj = result["objects"]["crossing"]
    assert obj["inside_stop_rows"] == obj["inside_visible_rows"] == 1
    assert obj["outside_stop_rows"] == obj["outside_visible_rows"] == 2
    assert obj["outside_stop_episodes"] == 2
    assert obj["in_gauge"]
    assert all(r["passed"] for r in battery.compare_metrics(result, result))


def test_zero_exit_worker_with_truncated_raw_is_error_not_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(battery, "BAGS", {"sample": 3})
    monkeypatch.setattr(battery, "VARIANTS", {"nominal": []})
    monkeypatch.setattr(battery, "source_info", lambda *a: {})
    monkeypatch.setattr(battery, "cache_meta", lambda *a: (meta(), []))
    monkeypatch.setattr(battery, "git", lambda *a: "testcommit")

    def fake_worker(argv, **kwargs):
        job = battery.read_json(argv[-1])
        prefix = job["prefix"]
        with open(prefix + ".jsonl", "w", encoding="utf-8") as f:
            f.write(json.dumps(row(meta()[0])) + "\n")
        battery.write_new(prefix + ".complete.json", {"wall_s": 1., "identity": {}})
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(battery.subprocess, "run", fake_worker)
    out = tmp_path / "bad.json"
    assert battery.main(["--out", str(out), "--cache", str(tmp_path)]) == 2
    report = battery.read_json(out)
    assert report["status"] == "ERROR" and report["errors"]
    assert not report["entries"]


def test_no_overwrite_and_worker_cap(tmp_path):
    out = tmp_path / "result.json"
    out.write_text("user evidence", encoding="utf-8")
    with pytest.raises(SystemExit):
        battery.main(["--out", str(out)])
    assert out.read_text(encoding="utf-8") == "user evidence"
    with pytest.raises(SystemExit):
        battery.main(["--out", str(tmp_path / "new.json"), "-j", "3"])
    plan = tmp_path / "job.json"
    plan.write_text(json.dumps({"prefix": str(out.with_suffix(""))}), encoding="utf-8")
    out.with_suffix(".jsonl").write_text("retained raw", encoding="utf-8")
    with pytest.raises(FileExistsError):
        battery.worker(plan)
    assert out.with_suffix(".jsonl").read_text(encoding="utf-8") == "retained raw"


def test_actual_judge_transforms_deterministic_aligned_and_sensor_mapped(tmp_path, monkeypatch):
    captured = []
    rvs = np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1]], dtype=np.float32)
    monkeypatch.setitem(sys.modules, "judge_runner", SimpleNamespace(
        NodeReplica=lambda: SimpleNamespace(R_vs=rvs, resets=[]), record=lambda *args: {}))
    monkeypatch.setitem(sys.modules, "range_test", SimpleNamespace(
        run_frame=lambda rep, xyz, inten, ring, m, k: captured.append((k, xyz.copy(), inten.copy(), ring.copy()))))
    spec = importlib.util.spec_from_file_location("isolated_probe", battery.JUDGE / "probe.py")
    probe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(probe)
    monkeypatch.setattr(battery, "load_probe", lambda: probe)
    monkeypatch.setattr(battery, "identity", lambda repo: {"test": True})
    cache = tmp_path / "cache"
    cache.mkdir()
    ms = meta(4)
    (cache / "meta.json").write_text(json.dumps(ms), encoding="utf-8")
    xyz = np.repeat(np.arange(300, dtype=np.float32).reshape(100, 3), 2, axis=0)
    inten = np.arange(200, dtype=np.float32)
    ring = np.arange(200, dtype=np.uint16)
    for i in range(4):
        np.savez(cache / f"f_{i:05d}.npz", xyz=xyz, inten=inten, ring=ring)

    def run(seed, name, args):
        captured.clear()
        job = {"repo": str(tmp_path), "cache": str(cache), "prefix": str(tmp_path / name),
               "args": args, "seed": seed}
        plan = tmp_path / f"{name}.job.json"
        plan.write_text(json.dumps(job), encoding="utf-8")
        battery.worker(plan)
        return list(captured)

    args = ["--dedup", "--drop", ".3", "--pitch", "2", "--every", "2"]
    first = run(1, "first", args)
    again = run(1, "again", args)
    other = run(2, "other", args)
    assert [r[0] for r in first] == [0, 2]
    for a, b in zip(first, again):
        for x, y in zip(a[1:], b[1:]):
            np.testing.assert_array_equal(x, y)
    assert not np.array_equal(first[0][2], other[0][2])
    # The first duplicate's intensity/ring survive; arrays stay aligned.
    for _, points, intensity, rings in first:
        np.testing.assert_array_equal(intensity, rings)
        assert np.all(rings % 2 == 0)
        original = xyz[rings]
        theta = np.radians(2)
        rotation = np.array([[np.cos(theta), 0, np.sin(theta)], [0, 1, 0],
                             [-np.sin(theta), 0, np.cos(theta)]])
        expected = ((original.astype(np.float64) @ rvs.T) @ rotation.T @ rvs).astype(np.float32)
        np.testing.assert_array_equal(points, expected)
        assert points.dtype == np.float32
    nominal = run(7, "nominal", [])
    np.testing.assert_array_equal(nominal[0][1], xyz)
