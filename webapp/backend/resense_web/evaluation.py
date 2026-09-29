"""Scoring a run against ground-truth labels (the ``labels/*.json`` / ``gt.json`` format of
docs/DATASET.md "Label format") with ``resense.metrics``, as ``resense eval`` does: a frame is keyed
by its bag index; a frame absent from the labels counts as empty (no object). The headline keys of
the EvalSummary (webapp/API.md) are frame-level and consistent with ``Evaluation.summary()``:
``frames_with_object_in_gauge`` = frames - empty_frames, ``false_stop_frames`` = fp_frames,
``frames_detected`` = alarm_frames - fp_frames.

A label file without frame keys but with ``_meta.bag`` and an ``events`` list (``labels/
new_data_objects.json``: mined tracks of an obstacle-free ride) declares an obstacle-free recording:
every frame is an empty labelled frame.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

import resense
from resense.config import DetectorConfig
from resense.metrics import Evaluation, gt_objects, load_gt

LABEL_DIRS = (
    Path(__file__).resolve().parents[3] / "labels",
    Path(resense.__file__).resolve().parents[1] / "labels",
)
MAX_FRAME_KEY = 10 ** 7


def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(float(v))


def _check_row(key: str, j: int, row) -> None:
    where = f"кадр {key}, объект {j + 1}"
    if not isinstance(row, dict):
        raise ValueError(f"Разметка, {where}: объект должен быть JSON-объектом")
    bbox = row.get("bbox")
    if bbox is not None:
        ok = (isinstance(bbox, list) and len(bbox) == 2 and all(isinstance(c, list) and len(c) == 3 for c in bbox)
              and all(_is_number(v) for c in bbox for v in c))
        if not ok:
            raise ValueError(f"Разметка, {where}: bbox должен быть [[xmin, ymin, zmin], [xmax, ymax, zmax]]")
    elif "distance" not in row:
        raise ValueError(f"Разметка, {where}: нужно поле distance (м) или bbox")
    for k in ("distance", "lateral"):
        if k in row and not _is_number(row[k]):
            raise ValueError(f"Разметка, {where}: поле {k} должно быть числом")
    if "size" in row:
        size = row["size"]
        if not (isinstance(size, list) and len(size) == 3 and all(_is_number(v) for v in size)):
            raise ValueError(f"Разметка, {where}: size должен быть [длина, ширина, высота] в метрах")
    if "in_gauge" in row and not isinstance(row["in_gauge"], bool):
        raise ValueError(f"Разметка, {where}: in_gauge должен быть true или false")
    if "n_points" in row and not _is_number(row["n_points"]):
        raise ValueError(f"Разметка, {where}: n_points должен быть числом")


def validate_labels(data: dict) -> None:
    """Raise ValueError (Russian) unless ``data`` is a label file: ``{"_meta": {...}, "00042":
    [{"distance": .., "lateral": .., "size": [..], "in_gauge": ..} | {"bbox": ..}, ...], ...}``,
    or an obstacle-free declaration (``_meta.bag`` + an ``events`` list, no frame keys)."""
    if not isinstance(data, dict):
        raise ValueError("Файл разметки должен быть JSON-объектом с ключами-номерами кадров")
    meta = data.get("_meta")
    if meta is not None and not isinstance(meta, dict):
        raise ValueError("Разметка: поле _meta должно быть объектом")
    frame_keys = 0
    for key, rows in data.items():
        if not isinstance(key, str) or key.startswith("_"):
            continue
        if key == "events":
            if not isinstance(rows, list):
                raise ValueError("Разметка: поле events должно быть списком")
            continue
        if not key.isdigit() or int(key) >= MAX_FRAME_KEY:
            raise ValueError(f"Разметка: ключ «{key[:40]}» не номер кадра (ожидается, например, «00042»)")
        if not isinstance(rows, list):
            raise ValueError(f"Разметка, кадр {key}: ожидается список объектов (пустой список — кадр без объектов)")
        for j, row in enumerate(rows):
            _check_row(key, j, row)
        frame_keys += 1
    if frame_keys == 0 and not (isinstance(meta, dict) and meta.get("bag") and isinstance(data.get("events"), list)):
        raise ValueError("В файле разметки нет ни одного кадра")


@lru_cache(maxsize=64)
def _meta_bag(path: str, mtime_ns: int, size: int) -> str | None:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        validate_labels(data)
    except (OSError, ValueError):
        return None
    bag = (data.get("_meta") or {}).get("bag")
    return str(bag) if bag else None


def _label_files() -> list[Path]:
    seen, out = set(), []
    for d in LABEL_DIRS:
        try:
            files = sorted(d.glob("*.json"))
        except OSError:
            continue
        for f in files:
            r = f.resolve()
            if r not in seen:
                seen.add(r)
                out.append(r)
    return out


def find_builtin_labels(recording_name: str) -> Path | None:
    """The repository's ``labels/*.json`` whose ``_meta.bag`` is this recording's name (exact
    match first, then ignoring case), or None."""
    if not recording_name:
        return None
    by_bag = []
    for f in _label_files():
        try:
            st = f.stat()
        except OSError:
            continue
        bag = _meta_bag(str(f), st.st_mtime_ns, st.st_size)
        if bag:
            by_bag.append((bag, f))
    for bag, f in by_bag:
        if bag == recording_name:
            return f
    low = recording_name.lower()
    for bag, f in by_bag:
        if bag.lower() == low:
            return f
    return None


@lru_cache(maxsize=8)
def _load(path: str, mtime_ns: int, size: int) -> tuple[dict, bool]:
    """{bag frame index: rows} and whether the file declares an obstacle-free recording."""
    gt = load_gt(path)
    frames = {int(k): v for k, v in gt.items() if k.isdigit()}
    return frames, not frames


def _labels(labels_path: Path) -> tuple[dict, bool]:
    p = Path(labels_path)
    st = p.stat()
    return _load(str(p), st.st_mtime_ns, st.st_size)


def _in_gauge(rows) -> bool:
    return any(g.in_gauge for g in gt_objects(rows or []))


def labels_in_gauge(frame_indices: Sequence[int], labels_path: Path) -> list[bool]:
    """Per bag frame index: whether a labelled, visible (``n_points`` != 0) in-gauge object is
    there - the frames the detector must answer with STOP."""
    frames, _ = _labels(labels_path)
    return [_in_gauge(frames.get(int(i))) if i is not None else False for i in frame_indices]


def _json_safe(o):
    if isinstance(o, dict):
        return {str(k): _json_safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_json_safe(v) for v in o]
    if isinstance(o, np.generic):
        o = o.item()
    if isinstance(o, float) and not math.isfinite(o):
        return None
    return o


def evaluate(frames: Iterable[dict], labels_path: Path, cfg: DetectorConfig | None = None) -> dict:
    """EvalSummary (webapp/API.md) of a run's ``/frames`` dicts (processed order, ``frame`` = bag
    index) against a label file. ``cfg`` (the run's detector config) only shapes the
    subsampling caveat of the raw summary."""
    labels_path = Path(labels_path)
    gt, obstacle_free = _labels(labels_path)
    if cfg is None:
        cfg = DetectorConfig()
    ev = Evaluation(confirm_hits=cfg.tracking.frames_to_confirm(), frame_dt=cfg.tracking.frame_dt,
                    min_hits=cfg.tracking.confirm_hits, confirm_time_s=cfg.tracking.confirm_time_s,
                    stamp_dt_range=tuple(cfg.accumulation.stamp_dt_range))
    n_labelled = n_in_gauge = n_detected = n_false = n_false_ep = n_occluded = 0
    prev_false = False
    for pos, d in enumerate(frames):
        if "detections" not in d:
            d = {**d, "detections": []}
        idx = d.get("frame")
        idx = int(idx) if idx is not None else pos
        rows = gt.get(idx)
        if rows is not None or obstacle_free:
            n_labelled += 1
        rows = rows or []
        n_occluded += sum(1 for r in rows if r.get("n_points", 1) == 0)
        objs = gt_objects(rows)
        ev.add_frame(d, objs, frame_index=idx)
        stop = bool(d.get("obstacle"))
        in_gauge = any(g.in_gauge for g in objs)
        if in_gauge:
            n_in_gauge += 1
            n_detected += int(stop)
        false_stop = stop and not in_gauge
        n_false += int(false_stop)
        n_false_ep += int(false_stop and not prev_false)
        prev_false = false_stop
    raw = ev.summary()
    raw["occluded_gt_skipped"] = n_occluded
    raw["gt_frames"] = len(gt)
    raw["obstacle_free_declaration"] = obstacle_free
    first = raw.get("first_detection_distance") or {}
    return _json_safe({
        "labels_name": labels_path.name,
        "frames_labelled": n_labelled,
        "frames_with_object_in_gauge": n_in_gauge,
        "frames_detected": n_detected,
        "recall": (n_detected / n_in_gauge) if n_in_gauge else None,
        "false_stop_frames": n_false,
        "false_stop_episodes": n_false_ep,
        "first_detection_distance": round(max(first.values()), 2) if first else None,
        "raw": raw,
    })
