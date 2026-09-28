"""Event identity and denominator accounting used by manual ride scene review."""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from scripts.cache_frames import _atomic_save
from scripts.cache_io import load_cache_array
from resense.pointcloud import COMPACT16_DTYPE


spec = importlib.util.spec_from_file_location(
    "ride_event_scenes", Path(__file__).resolve().parents[1] / "scripts/ride_event_scenes.py")
scenes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scenes)


def write_rows(path, frame_ids, ids):
    rows = []
    for i, (frame, tracks) in enumerate(zip(frame_ids, ids)):
        rows.append({"frame_id": frame, "stamp": i * 0.1, "obstacle": bool(tracks),
                     "detections": [{"id": t, "distance": 50.0, "center": [50, 0, 1]} for t in tracks]})
    path.write_text("\n".join(json.dumps(r) for r in rows))


def test_event_scopes_and_overlapping_alarm_frames_stay_distinct(tmp_path):
    a, b = tmp_path / "new_data_0.jsonl", tmp_path / "new_data_1.jsonl"
    write_rows(a, ["a0", "a1", "a2", "a3"], [[1, 2], [1], [], [1]])
    write_rows(b, ["b0", "b1"], [[1], []])
    data = scenes.collect([a, b])
    assert data["frames"] == 6 and data["alarm_frames"] == 4
    assert data["alarm_events"] == 3 and data["stop_episodes"] == 3
    assert sum(e["alarm_frames"] for e in data["events"]) == 5
    assert all(e["scene"] == "unreviewed" for e in data["events"])


def test_duplicate_frame_ids_refuse_double_counting(tmp_path):
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    write_rows(a, ["same"], [[1]])
    write_rows(b, ["same"], [[2]])
    with pytest.raises(ValueError, match="duplicate ride frame"):
        scenes.collect([a, b])


def test_scene_cache_index_loads_compressed_frame(tmp_path):
    frame = np.zeros(3, dtype=COMPACT16_DTYPE)
    frame["x"] = [1, 2, 3]
    frame_id = "new_data_0_0000"
    _atomic_save(str(tmp_path / f"{frame_id}.npy.zst"), frame, zstd_level=3)

    indexed = scenes.cache_index(tmp_path)

    assert indexed[frame_id].endswith(".npy.zst")
    np.testing.assert_array_equal(load_cache_array(indexed[frame_id]), frame)
