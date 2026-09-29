"""Pure helpers: the decision rule, episodes / events / summary, RSC1 clouds, the results index,
path sanitizing."""
from __future__ import annotations

import json

import numpy as np
import pytest

from resense_web import clouds, results
from resense_web.decision import decision_of
from resense_web.summary import SeriesBuilder, episodes_of, events_of, run_summary
from resense_web.util import UnsafePath, content_disposition, dumps, sanitize_relpath


def test_decision_rule_matches_the_node():
    assert decision_of({"obstacle": True, "health": {"level": "error"}}) == "STOP"
    assert decision_of({"obstacle": False, "health": {"level": "error", "decision_level": "ok"}}) == "FAULT"
    assert decision_of({"warning": True, "health": {"level": "ok"}}) == "CAUTION"
    assert decision_of({"health": {"level": "warn", "decision_level": "ok"}}) == "GO"   # latency-only warning
    assert decision_of({"health": {"level": "warn"}}) == "CAUTION"                      # older core: level
    assert decision_of({"health": {"level": "ok", "decision_level": "warn"}}) == "CAUTION"
    assert decision_of({}) == "GO"


def _frames(decisions: str, nearest=None):
    out = []
    for i, c in enumerate(decisions):
        dec = {"G": "GO", "C": "CAUTION", "S": "STOP", "F": "FAULT"}[c]
        nd = (nearest or {}).get(i, 50.0 + i if c == "S" else None)
        out.append({"frame": 100 + i, "t": 0.1 * i, "decision": dec, "nearest_distance": nd,
                    "clear_distance": 80.0, "timing_ms": {"total": 10.0 + i},
                    "detections": [{}] if c == "S" else [], "warnings": [{}] if c == "C" else [],
                    "n_points": 1000, "health": {"visibility": 150.0}})
    return out


def test_episodes_and_events():
    b = SeriesBuilder.from_frames(_frames("GGSSGSCGSSFGG"))
    eps = episodes_of(b.frame, b.t, b.decisions, b.nearest)
    assert [e["decision"][0] + str(e["n_frames"]) for e in eps] == \
        ["G2", "S2", "G1", "S1", "C1", "G1", "S2", "F1", "G2"]
    assert eps[1]["first_frame"] == 102 and eps[1]["last_frame"] == 103
    assert eps[1]["distance_min"] == 52.0 and eps[1]["distance_max"] == 53.0
    assert eps[0]["distance_min"] is None
    assert eps[1]["t0"] == pytest.approx(0.2) and eps[1]["t1"] == pytest.approx(0.3)
    evs = events_of(eps)
    # the GO between two STOPs and the GO between STOP-CAUTION-...-STOP are gaps; leading / trailing GO are not
    assert [e["decision"][0] for e in evs] == ["S", "G", "S", "C", "G", "S", "F"]


def test_run_summary():
    b = SeriesBuilder.from_frames(_frames("GGSSSCG", nearest={2: 60.0, 3: None, 4: 58.5}))
    s = run_summary(b, processing_fps=12.345)
    assert s["n_frames"] == 7 and s["decisions"] == "GGSSSCG"
    assert s["counts"] == {"GO": 3, "CAUTION": 1, "STOP": 3, "FAULT": 0}
    assert s["stop_episodes"] == 1
    assert s["first_stop"] == {"frame": 102, "t": 0.2, "distance": 60.0}
    assert (s["distance_min"], s["distance_max"]) == (58.5, 60.0)
    assert s["latency_ms"]["max"] == 16.0 and s["latency_ms"]["p50"] == 13.0
    assert s["duration_s"] == pytest.approx(0.6)
    assert s["processing_fps"] == 12.35
    assert s["clear_distance_median"] == 80.0 and s["visibility_median"] == 150.0
    assert s["eval"] is None
    series = b.series([True, False, True, True, True, False, False])
    assert series["labels_in_gauge"][0] is True and len(series["frame"]) == 7
    empty = run_summary(SeriesBuilder(), 0.0)
    assert empty["n_frames"] == 0 and empty["first_stop"] is None and empty["clear_distance_median"] is None


def test_rsc1_roundtrip_flags_and_sampling():
    rng = np.random.default_rng(1)
    xyz = rng.uniform([0, -5, -2], [100, 5, 3], size=(20000, 3)).astype(np.float32)
    xyz[0] = [400.0, 0, 0]                          # beyond int16 centimetres: dropped
    xyz[1] = [np.nan, 0, 0]                          # non-finite: dropped
    xyz[2:12] = [30.0, 0.0, 0.5]                     # inside the obstacle box
    xyz[12:17] = [60.0, 2.0, 0.5]                    # inside the warning box
    inten = rng.uniform(0, 300, 20000)
    corridor = np.arange(100, 400)
    det = [{"center": [30.0, 0.0, 0.5], "size": [0.4, 0.4, 1.0]}]
    warn = [{"center": [60.0, 2.0, 0.5], "size": [0.2, 0.2, 0.2]}]
    blob, n = clouds.pack_frame_cloud(xyz, inten, corridor, det, warn, budget=1000, seed=(1, 2))
    assert blob[:4] == b"RSC1" and len(blob) == 8 + 8 * n
    pts, it, flags = clouds.unpack_rsc1(blob)
    assert n == 1000 and pts.shape == (1000, 3)
    assert np.all(np.abs(pts) < 327.68)
    assert (flags & clouds.FLAG_CORRIDOR).sum() >= 300          # every corridor point kept
    assert (flags & clouds.FLAG_OBJECT).sum() >= 10
    assert (flags & clouds.FLAG_WARNING).sum() >= 5
    assert it.max() <= 255
    obj = pts[(flags & clouds.FLAG_OBJECT) != 0]
    assert np.allclose(obj[:10], [30.0, 0.0, 0.5], atol=0.006)
    # deterministic for a seed; everything kept when under budget
    assert clouds.pack_frame_cloud(xyz, inten, corridor, det, warn, 1000, seed=(1, 2))[0] == blob
    _, n_all = clouds.pack_frame_cloud(xyz[:500], inten[:500], None, [], [], budget=5000)
    assert n_all == 498                              # all valid points (two were invalid)
    with pytest.raises(ValueError):
        clouds.unpack_rsc1(b"XXXX" + blob[4:])
    # flagged points are kept even over budget
    _, n_over = clouds.pack_frame_cloud(xyz, inten, np.arange(2, 20000), [], [], budget=100)
    assert n_over == 19998


def test_cloud_stride_and_writer(tmp_path):
    assert clouds.cloud_stride(None) == 1 and clouds.cloud_stride(3000) == 1
    assert clouds.cloud_stride(3001) == 2 and clouds.cloud_stride(11271) == 4
    w = clouds.CloudWriter(tmp_path, budget=100, stride=2, max_clouds=3)
    for pos in range(10):
        if w.wants(pos):
            w.add(pos, clouds.pack_rsc1(np.full((pos + 1, 3), pos, np.float32), np.zeros(pos + 1), np.zeros(pos + 1)))
    idx = w.close()
    assert idx["frames"] == [0, 2, 4] and idx["format"] == "RSC1"
    loaded = clouds.load_index(tmp_path)
    blob = clouds.read_cloud(tmp_path, loaded, 4)
    pts, _, _ = clouds.unpack_rsc1(blob)
    assert pts.shape == (5, 3) and np.all(pts == 4.0)
    assert clouds.read_cloud(tmp_path, loaded, 3) is None


def test_results_index_and_paging(tmp_path):
    w = results.ResultsWriter(tmp_path)
    for i in range(1234):
        w.write({"pos": i, "frame": i * 2, "x": float("nan") if i == 5 else 1.5, "s": "ё"})
    w.close()
    lines, total = results.read_lines(tmp_path, 1200, 100)
    assert total == 1234 and len(lines) == 34
    assert json.loads(lines[0])["pos"] == 1200
    assert json.loads(results.read_lines(tmp_path, 5, 1)[0][0])["x"] is None    # NaN -> null
    assert results.read_lines(tmp_path, 5000, 10) == ([], 1234)
    # a missing / stale index is rebuilt from the file
    (tmp_path / results.INDEX).unlink()
    with open(tmp_path / results.RESULTS, "a", encoding="utf-8") as fh:
        fh.write("\n" + json.dumps({"pos": 1234}) + "\n\n")
    lines, total = results.read_lines(tmp_path, 1233, 5)
    assert total == 1235 and [json.loads(x)["pos"] for x in lines] == [1233, 1234]
    assert sum(1 for _ in results.iter_results(tmp_path)) == 1235


@pytest.mark.parametrize("bad", ["/etc/passwd", "../x", "a/../../b", "a\\b", "a\x00b", "C:/x", "", "./", "a/" * 40])
def test_sanitize_rejects(bad):
    with pytest.raises(UnsafePath):
        sanitize_relpath(bad)


def test_sanitize_accepts_and_normalizes():
    assert sanitize_relpath("bag/./x_0.db3").as_posix() == "bag/x_0.db3"
    assert sanitize_relpath("папка/файл.npy").as_posix() == "папка/файл.npy"
    assert sanitize_relpath("a\\b.txt", allow_backslash=True).as_posix() == "a/b.txt"


def test_json_and_headers():
    assert dumps({"a": float("inf"), "b": np.float32(1.5), "c": [np.int64(3)]}) == '{"a":null,"b":1.5,"c":[3]}'
    cd = content_disposition("Прогон_1.frames.csv", "x.csv")
    assert cd.startswith('attachment; filename="') and "filename*=UTF-8''" in cd and "%D0%9F" in cd
