"""Runs (results of finished jobs): rows, the API shape and the files of ``runs/<id>/``."""
from __future__ import annotations

import csv
import io
import shutil
from pathlib import Path
from typing import Iterator

from resense_web import clouds, results
from resense_web.db import Database, jload
from resense_web.presets import STANDARD_ID
from resense_web.settings import Settings
from resense_web.summary import SeriesBuilder, events_of, run_summary
from resense_web.util import atomic_write_json, dumps, now_iso, read_json

SUMMARY = "summary.json"
SERIES = "series.json"
CSV_COLUMNS = ("pos", "frame", "t", "decision", "nearest_distance", "clear_distance", "latency_ms",
               "n_detections", "n_warnings", "n_points")


def run_dir(settings: Settings, run_id: str) -> Path:
    return settings.runs_dir / run_id


def default_name(recording_name: str, preset_id: str, preset_name: str) -> str:
    return recording_name if preset_id == STANDARD_ID else f"{recording_name} · {preset_name}"


def to_api(row: dict) -> dict:
    return {
        "id": row["id"], "name": row["name"], "recording_id": row["recording_id"], "job_id": row["job_id"],
        "preset": {"id": row["preset_id"], "name": row["preset_name"]}, "created_at": row["created_at"],
        "has_clouds": bool(row["has_clouds"]), "cloud_frames": int(row["cloud_frames"] or 0),
        "source_kind": row["source_kind"], "summary": jload(row["summary"], {}),
    }


def get(db: Database, run_id: str) -> dict | None:
    return db.one("SELECT * FROM runs WHERE id = ?", (run_id,))


def list_all(db: Database) -> list[dict]:
    return db.query("SELECT * FROM runs ORDER BY created_at DESC, rowid DESC")


def insert_from_job(db: Database, settings: Settings, job: dict, run_id: str, source_kind: str) -> dict:
    d = run_dir(settings, run_id)
    doc = read_json(d / SUMMARY)
    if not isinstance(doc, dict) or "summary" not in doc:
        raise RuntimeError("summary.json missing")
    index = clouds.load_index(d)
    n_clouds = len(index["frames"]) if index else 0
    row = {
        "id": run_id, "name": default_name(job["recording_name"], job["preset_id"], job["preset_name"]),
        "recording_id": job["recording_id"], "recording_name": job["recording_name"], "job_id": job["id"],
        "preset_id": job["preset_id"], "preset_name": job["preset_name"], "created_at": now_iso(),
        "has_clouds": 1 if n_clouds else 0, "cloud_frames": n_clouds, "source_kind": source_kind,
        "summary": dumps(doc["summary"]),
    }
    db.insert("runs", row)
    return row


def remove(settings: Settings, run_id: str) -> None:
    shutil.rmtree(run_dir(settings, run_id), ignore_errors=True)


def read_summary_doc(settings: Settings, run_id: str) -> dict:
    doc = read_json(run_dir(settings, run_id) / SUMMARY, {})
    return doc if isinstance(doc, dict) else {}


def episodes(settings: Settings, run_id: str) -> tuple[list[dict], list[dict]]:
    doc = read_summary_doc(settings, run_id)
    eps = doc.get("episodes") or []
    evs = doc.get("events")
    return eps, (evs if evs is not None else events_of(eps))


def _size(path: Path) -> int | None:
    try:
        return path.stat().st_size
    except OSError:
        return None


def detail_extras(settings: Settings, run_id: str) -> dict:
    """The run-detail keys kept in ``summary.json`` / on disk: the job options and the preset
    overrides the run was made with, and the sizes of its stored files (bytes, None if absent)."""
    doc = read_summary_doc(settings, run_id)
    d = run_dir(settings, run_id)
    options = doc.get("options")
    overrides = doc.get("overrides")
    return {
        "options": options if isinstance(options, dict) else None,
        "overrides": overrides if isinstance(overrides, dict) else {},
        "sizes": {"results_jsonl": _size(d / results.RESULTS), "clouds": _size(d / "clouds.bin")},
    }


def labels_series(settings: Settings, run_id: str) -> dict:
    """Per processed frame, what the run's label file says: an in-gauge object and its along-track
    extent (``GET /runs/{id}/labels``). ``available`` is false when the run was made without labels
    or its label file is gone / no longer readable (e.g. the recording was deleted)."""
    empty = {"available": False, "labels_name": None, "in_gauge": [], "near": [], "far": []}
    doc = read_summary_doc(settings, run_id)
    path = doc.get("labels_path")
    if not path or not Path(path).is_file():
        return empty
    from resense_web import evaluation
    frames = series(settings, run_id)["frame"]
    try:
        in_gauge = evaluation.labels_in_gauge(frames, Path(path))
        near, far = evaluation.labels_extent(frames, Path(path))
    except (OSError, ValueError, KeyError, TypeError):
        return empty
    ev = (doc.get("summary") or {}).get("eval") or {}
    name = ev.get("labels_name") if isinstance(ev, dict) else None
    return {"available": True, "labels_name": name or Path(path).name, "in_gauge": in_gauge,
            "near": near, "far": far}


def series(settings: Settings, run_id: str) -> dict:
    """The chart arrays (``series.json``; rebuilt from results.jsonl when missing)."""
    d = run_dir(settings, run_id)
    data = read_json(d / SERIES)
    if isinstance(data, dict) and "decisions" in data:
        return data
    b = SeriesBuilder.from_frames(results.iter_results(d))
    data = b.series()
    atomic_write_json(d / SERIES, data)
    return data


def series_bytes(settings: Settings, run_id: str) -> bytes:
    """``series.json`` as stored (no re-encoding), rebuilt first when missing."""
    path = run_dir(settings, run_id) / SERIES
    try:
        return path.read_bytes()
    except FileNotFoundError:
        series(settings, run_id)
        return path.read_bytes()


def rebuild_summary(settings: Settings, run_id: str, processing_fps: float = 0.0) -> dict:
    """RunSummary recomputed from the stored series (kept for tools and tests)."""
    s = series(settings, run_id)
    b = SeriesBuilder()
    b.frame, b.t, b.letters = list(s["frame"]), list(s["t"]), list(s["decisions"])
    b.nearest, b.clear, b.latency_ms = list(s["nearest"]), list(s["clear"]), list(s["latency_ms"])
    b.n_detections, b.n_warnings = list(s["n_detections"]), list(s["n_warnings"])
    b.n_points, b.visibility = list(s["n_points"]), list(s["visibility"])
    return run_summary(b, processing_fps)


def frames_csv(settings: Settings, run_id: str) -> Iterator[str]:
    s = series(settings, run_id)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(CSV_COLUMNS)
    yield buf.getvalue()
    decisions = s["decisions"]
    names = {"G": "GO", "C": "CAUTION", "S": "STOP", "F": "FAULT"}
    for start in range(0, len(decisions), 1000):
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        for i in range(start, min(start + 1000, len(decisions))):
            nd = s["nearest"][i]
            vis_nd = "" if nd is None else f"{nd:g}"
            w.writerow((i, s["frame"][i], f"{s['t'][i]:g}", names.get(decisions[i], "FAULT"), vis_nd,
                        f"{s['clear'][i]:g}", f"{s['latency_ms'][i]:g}", s["n_detections"][i],
                        s["n_warnings"][i], s["n_points"][i]))
        yield buf.getvalue()
