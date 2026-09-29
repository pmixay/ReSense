"""Recordings (sources): rows, their API shape, labels, registration and removal."""
from __future__ import annotations

import json
import logging
import shutil
from functools import lru_cache
from pathlib import Path

from resense_web.db import Database, jload
from resense_web.probe import Probe
from resense_web.settings import Settings
from resense_web.util import dumps, new_id, now_iso

log = logging.getLogger("resense_web.recordings")

LABELS_FILE = "labels.json"
BUNDLED_LABELS = "ground_truth.json"  # next to the bag: written by resense_web.demo, kept in its zip


@lru_cache(maxsize=256)
def _builtin_labels_cached(name: str) -> str | None:
    from resense_web import evaluation
    p = evaluation.find_builtin_labels(name)
    return str(p) if p else None


def builtin_labels(row: dict) -> Path | None:
    """Built-in labels (repo ``labels/*.json``) matched by the recording name or its source name."""
    meta = jload(row.get("meta"), {})
    names = [row.get("name") or ""]
    for extra in (meta.get("source_name"), meta.get("stem_prefix")):
        if extra and extra not in names:
            names.append(extra)
    for name in names:
        if not name:
            continue
        p = _builtin_labels_cached(name)
        if p:
            return Path(p)
    return None


def recording_dir(settings: Settings, rec_id: str) -> Path:
    return settings.recordings_dir / rec_id


def uploaded_labels_path(settings: Settings, row: dict) -> Path | None:
    p = recording_dir(settings, row["id"]) / LABELS_FILE
    return p if row.get("labels_name") and p.is_file() else None


@lru_cache(maxsize=256)
def _is_label_file(path: str, mtime_ns: int, size: int) -> bool:
    from resense_web import evaluation
    try:
        with open(path, encoding="utf-8") as fh:
            evaluation.validate_labels(json.load(fh))
    except (OSError, ValueError):
        return False
    return True


def bundled_labels(row: dict) -> Path | None:
    """A valid ``ground_truth.json`` next to the bag: the demo's ground truth, also when a demo
    zip is uploaded again or its folder is copied into the server folder."""
    base = Path(row["path"])
    p = (base if base.is_dir() else base.parent) / BUNDLED_LABELS
    try:
        st = p.stat()
    except OSError:
        return None
    return p if _is_label_file(str(p), st.st_mtime_ns, st.st_size) else None


def _builtin_or_bundled(row: dict) -> Path | None:
    p = bundled_labels(row)
    if p:
        return p
    try:
        return builtin_labels(row)
    except Exception:   # a broken labels folder must not break the recordings list
        log.exception("built-in labels lookup failed for %s", row.get("name"))
        return None


def labels_path(settings: Settings, row: dict) -> Path | None:
    """The labels a job scores against: uploaded, else a ground_truth.json next to the bag, else built-in."""
    return uploaded_labels_path(settings, row) or _builtin_or_bundled(row)


def labels_state(settings: Settings, row: dict) -> dict:
    if uploaded_labels_path(settings, row):
        return {"available": True, "source": "upload", "name": row["labels_name"]}
    p = _builtin_or_bundled(row)
    if p:
        if p.name != BUNDLED_LABELS:
            name = p.stem
        elif row.get("source") == "demo":
            name = f"{row['name']} (эталон демо)"
        else:
            name = f"{BUNDLED_LABELS} (рядом с записью)"
        return {"available": True, "source": "builtin", "name": name}
    return {"available": False, "source": None, "name": None}


def to_api(settings: Settings, row: dict) -> dict:
    return {
        "id": row["id"], "name": row["name"], "kind": row["kind"], "source": row["source"],
        "path": row["path"], "size_bytes": int(row["size_bytes"] or 0), "n_frames": row["n_frames"],
        "duration_s": row["duration_s"], "topics": jload(row["topics"], []),
        "default_topic": row["default_topic"], "labels": labels_state(settings, row),
        "created_at": row["created_at"], "warnings": jload(row["warnings"], []),
    }


def get(db: Database, rec_id: str) -> dict | None:
    return db.one("SELECT * FROM recordings WHERE id = ?", (rec_id,))


def list_all(db: Database) -> list[dict]:
    return db.query("SELECT * FROM recordings ORDER BY created_at DESC, rowid DESC")


def insert(db: Database, probe: Probe, *, name: str, source: str, rec_id: str | None = None,
           extra_warnings: list[str] | None = None, meta: dict | None = None) -> dict:
    rec_id = rec_id or new_id()
    warnings = list(dict.fromkeys([*(extra_warnings or []), *probe.warnings]))
    row = {
        "id": rec_id, "name": name.strip() or probe.source_name or "запись", "kind": probe.kind,
        "source": source, "path": str(probe.path), "size_bytes": int(probe.size_bytes),
        "n_frames": probe.n_frames, "duration_s": probe.duration_s, "topics": dumps(probe.topics),
        "default_topic": probe.default_topic, "labels_name": None, "warnings": dumps(warnings),
        "meta": dumps({**probe.meta, **(meta or {}), "source_name": probe.source_name}),
        "created_at": now_iso(),
    }
    db.insert("recordings", row)
    return row


def remove_files(settings: Settings, row: dict) -> None:
    """Delete what the app owns: the recording dir (uploads, demo bags, uploaded labels) and cached
    downloads. Server folders registered in place are never touched."""
    shutil.rmtree(recording_dir(settings, row["id"]), ignore_errors=True)
    for p in settings.cache_dir.glob(f"{row['id']}*"):
        try:
            p.unlink()
        except OSError:
            pass
