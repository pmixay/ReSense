"""What a folder or file holds and what the worker can read from it: rosbag2 bags (sqlite3 or
mcap, through ``rosbags``), folders of ``.npy`` / ``.npz`` frames and results ``.jsonl`` files.

Every failure is a :class:`ProbeError` with a short Russian message for the user."""
from __future__ import annotations

import json
import os
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from resense_web.util import UnsafePath, is_within, natural_key, sanitize_relpath, tree_size

PC2 = "sensor_msgs/msg/PointCloud2"
PREFERRED_TOPICS = ("/lidar_points", "/sensing/lidar/hesai128/pointcloud")
BAG_SUFFIXES = (".db3", ".mcap")
FRAME_SUFFIXES = (".npy", ".npz")
SKIP_DIRS = {"__MACOSX"}
MAX_ZIP_MEMBERS = 200_000
ZIP_BOMB_RATIO = 1000        # uncompressed / compressed of one member
ZIP_BOMB_MIN = 64 * 1024 ** 2


class ProbeError(ValueError):
    """The input is not usable; ``str(exc)`` is a short Russian message."""


@dataclass
class Probe:
    kind: str                         # rosbag2 | npy | jsonl
    path: Path                        # bag dir or storage file, frames dir, jsonl file
    n_frames: int | None
    duration_s: float | None
    topics: list[dict] = field(default_factory=list)
    default_topic: str | None = None
    warnings: list[str] = field(default_factory=list)
    size_bytes: int = 0
    meta: dict = field(default_factory=dict)
    source_name: str = ""


# --- rosbag2 ------------------------------------------------------------------------------------

def storage_files(d: Path) -> list[Path]:
    try:
        return sorted((p for p in d.iterdir() if p.is_file() and p.suffix.lower() in BAG_SUFFIXES
                       and not p.name.startswith(".")), key=lambda p: natural_key(p.name))
    except OSError:
        return []


def is_bag_dir(d: Path) -> bool:
    return d.is_dir() and (d / "metadata.yaml").is_file() and bool(storage_files(d))


def choose_topic(topics: list[dict]) -> str | None:
    pcs = [t for t in topics if t["type"] == PC2 and t["count"] > 0]
    names = {t["name"] for t in pcs}
    for pref in PREFERRED_TOPICS:
        if pref in names:
            return pref
    return max(pcs, key=lambda t: t["count"])["name"] if pcs else None


def bag_pc2_count(bag_dir: Path) -> int | None:
    """PointCloud2 messages listed in a bag's metadata.yaml (cheap, for the folder browser)."""
    import yaml
    try:
        with open(bag_dir / "metadata.yaml", encoding="utf-8") as fh:
            info = (yaml.safe_load(fh) or {})["rosbag2_bagfile_information"]
        topics = [{"name": t["topic_metadata"]["name"], "type": t["topic_metadata"]["type"],
                   "count": int(t.get("message_count", 0))} for t in info.get("topics_with_message_count", [])]
    except (OSError, KeyError, TypeError, ValueError, yaml.YAMLError):
        return None
    name = choose_topic(topics)
    return next((t["count"] for t in topics if t["name"] == name), None) if name else 0


def probe_rosbag2(path: Path) -> Probe:
    from rosbags.rosbag2 import Reader
    from rosbags.typesys import Stores, get_typestore

    warnings: list[str] = []
    meta: dict = {}
    try:
        with Reader(path) as reader:
            agg: dict[str, dict] = {}
            for c in reader.connections:
                t = agg.setdefault(c.topic, {"name": c.topic, "type": c.msgtype, "count": 0})
                t["count"] += int(c.msgcount or 0)
            topics = sorted(agg.values(), key=lambda t: t["name"])
            default = choose_topic(topics)
            if default is None:
                raise ProbeError("В записи нет облаков точек (sensor_msgs/PointCloud2)")
            n = next(t["count"] for t in topics if t["name"] == default)
            n_pc = sum(1 for t in topics if t["type"] == PC2 and t["count"] > 0)
            if n_pc > 1:
                warnings.append(f"несколько топиков PointCloud2, выбран {default}")
            duration = reader.duration / 1e9 if reader.message_count > 1 else 0.0
            meta["start_ns"] = int(reader.start_time)
            meta["compression"] = reader.compression_mode or ""
            ts = get_typestore(Stores.ROS2_HUMBLE)
            conns = [c for c in reader.connections if c.topic == default]
            for conn, _t, raw in reader.messages(connections=conns):
                msg = ts.deserialize_cdr(raw, conn.msgtype)
                names = {f.name for f in msg.fields}
                if not {"x", "y", "z"} <= names:
                    raise ProbeError("В облаках точек нет полей x, y, z")
                if "intensity" not in names:
                    warnings.append("нет поля intensity")
                if "ring" not in names:
                    warnings.append("нет поля ring")
                if int(msg.width) * int(msg.height) == 0:
                    warnings.append("первый кадр пустой")
                meta["frame_id"] = msg.header.frame_id
                meta["fields"] = sorted(names)
                break
    except ProbeError:
        raise
    except FileNotFoundError as exc:
        raise ProbeError("Файлы записи rosbag2 не найдены (проверьте metadata.yaml и .db3/.mcap)") from exc
    except Exception as exc:   # rosbags raises several unrelated types for damaged bags
        raise ProbeError(f"Не удалось прочитать запись rosbag2: файл повреждён или неполон ({type(exc).__name__})") from exc
    if path.is_dir():
        meta["storage"] = "mcap" if any(p.suffix.lower() == ".mcap" for p in storage_files(path)) else "sqlite3"
        name = path.name
    else:
        meta["storage"] = "mcap" if path.suffix.lower() == ".mcap" else "sqlite3"
        name = path.stem
        if name.rsplit("_", 1)[-1].isdigit() and "_" in name:
            name = name.rsplit("_", 1)[0]
        warnings.append("нет metadata.yaml — запись прочитана напрямую из файла")
    return Probe(kind="rosbag2", path=path, n_frames=int(n), duration_s=round(duration, 3), topics=topics,
                 default_topic=default, warnings=warnings, size_bytes=tree_size(path), meta=meta,
                 source_name=name)


# --- .npy / .npz frames -------------------------------------------------------------------------

def frame_files(d: Path) -> list[Path]:
    try:
        files = [p for p in d.iterdir() if p.is_file() and p.suffix.lower() in FRAME_SUFFIXES
                 and not p.name.startswith(".")]
    except OSError:
        return []
    return sorted(files, key=lambda p: natural_key(p.name))


def array_layout(path: Path) -> tuple[str, set]:
    """("compact", field names) for a structured x/y/z array, ("array", {}) for an N x >=3 float
    array, ("npz", keys) for an .npz with ``xyz`` / ``points`` or a structured member."""
    try:
        if path.suffix.lower() == ".npz":
            with np.load(path, allow_pickle=False) as z:
                keys = set(z.files)
                if "xyz" in keys or "points" in keys:
                    return "npz", keys
                for k in z.files:
                    a = z[k]
                    if a.dtype.names and {"x", "y", "z"} <= set(a.dtype.names):
                        return "npz", set(a.dtype.names)
            raise ProbeError(f"Файл {path.name}: в .npz нужен массив xyz (N×3) или поля x, y, z")
        arr = np.load(path, mmap_mode="r", allow_pickle=False)
    except ProbeError:
        raise
    except Exception as exc:
        raise ProbeError(f"Файл {path.name} не читается как массив numpy") from exc
    if arr.dtype.names and {"x", "y", "z"} <= set(arr.dtype.names):
        return "compact", set(arr.dtype.names)
    if arr.ndim == 2 and arr.shape[1] >= 3 and arr.dtype.kind in "fiu":
        return "array", set()
    raise ProbeError(f"Файл {path.name}: нужен структурированный массив с полями x, y, z или массив N×3")


def probe_npy_dir(d: Path) -> Probe:
    from resense.io import load_cache_stamps, npy_frame_index

    files = frame_files(d)
    if not files:
        raise ProbeError("В папке нет кадров .npy / .npz")
    layout, names = array_layout(files[0])
    warnings = []
    if layout == "compact" and "ring" not in names:
        warnings.append("нет поля ring")
    if layout == "compact" and "intensity" not in names:
        warnings.append("нет поля intensity")
    if layout == "array":
        warnings.append("кадры без полей: столбцы x, y, z[, intensity]")
    idx = [npy_frame_index(str(f)) for f in files]
    from_name = all(i is not None for i in idx) and all(b > a for a, b in zip(idx, idx[1:]))
    all_npy = all(f.suffix.lower() == ".npy" for f in files)
    stamps = load_cache_stamps(str(d))
    if stamps:
        vals = [stamps[f.stem] for f in files if f.stem in stamps]
        duration = (max(vals) - min(vals)) if len(vals) > 1 else 0.0
    else:
        span = (idx[-1] - idx[0]) if from_name else len(files) - 1
        duration = 0.1 * span
    prefixes = {re.sub(r"[_-]?\d+$", "", f.stem) for f in files}
    meta = {"layout": "compact" if (all_npy and layout == "compact") else "generic",
            "index_from_name": bool(from_name), "files": len(files)}
    if len(prefixes) == 1 and next(iter(prefixes)):
        meta["stem_prefix"] = next(iter(prefixes))     # the bag name of a scripts/cache_frames.py cache
    return Probe(kind="npy", path=d, n_frames=len(files), duration_s=round(float(duration), 3),
                 warnings=warnings, size_bytes=tree_size(d), source_name=d.name, meta=meta)


# --- results .jsonl -----------------------------------------------------------------------------

def _result_line(line: bytes) -> dict | None:
    s = line.strip()
    if not s.startswith(b"{"):
        return None
    try:
        d = json.loads(s)
    except ValueError:
        return None
    return d if isinstance(d, dict) and "obstacle" in d else None


def probe_jsonl(path: Path) -> Probe:
    first = last_raw = None
    n = 0
    try:
        with open(path, "rb") as fh:
            for line in fh:
                if not line.lstrip().startswith(b"{"):
                    continue
                if first is None:
                    first = _result_line(line)
                    if first is None:
                        break
                n += 1
                last_raw = line
    except OSError as exc:
        raise ProbeError("Файл .jsonl не читается") from exc
    if first is None:
        raise ProbeError("Файл .jsonl не похож на результаты ReSense: нужна строка JSON с полем obstacle")
    last = _result_line(last_raw) if last_raw is not None else None
    duration = None
    try:
        if last is not None:
            duration = round(max(0.0, float(last["stamp"]) - float(first["stamp"])), 3)
    except (KeyError, TypeError, ValueError):
        duration = None
    warnings = ["только результаты: без облаков точек"]
    if "frame" not in first:
        warnings.append("нет поля frame — кадры пронумерованы по порядку")
    return Probe(kind="jsonl", path=path, n_frames=n, duration_s=duration, warnings=warnings,
                 size_bytes=path.stat().st_size, source_name=path.stem, meta={})


# --- dispatch -----------------------------------------------------------------------------------

def probe_path(p: Path) -> Probe:
    """Probe a bag dir / storage file / frames dir / jsonl file (server folders, finalized uploads)."""
    p = Path(p)
    if p.is_dir():
        if is_bag_dir(p):
            return probe_rosbag2(p)
        storage = storage_files(p)
        if len(storage) == 1:
            return probe_rosbag2(storage[0])
        if len(storage) > 1:
            raise ProbeError("В папке несколько файлов .db3/.mcap без metadata.yaml")
        if frame_files(p):
            return probe_npy_dir(p)
        jsonls = sorted(q for q in p.glob("*.jsonl") if q.is_file())
        if len(jsonls) == 1:
            return probe_jsonl(jsonls[0])
        raise ProbeError("В папке нет записи rosbag2 (metadata.yaml + .db3/.mcap) и кадров .npy/.npz")
    if p.is_file():
        suffix = p.suffix.lower()
        if p.name == "metadata.yaml" or suffix in BAG_SUFFIXES:
            return probe_rosbag2(p.parent if is_bag_dir(p.parent) else p)
        if suffix == ".jsonl":
            return probe_jsonl(p)
        if suffix in FRAME_SUFFIXES:
            return probe_npy_dir(p.parent)
        if suffix == ".zip":
            raise ProbeError("Архивы .zip загружайте через «Загрузку» — на месте они не распаковываются")
        raise ProbeError("Неизвестный тип файла: нужна запись rosbag2, кадры .npy/.npz или результаты .jsonl")
    raise ProbeError("Путь не найден")


def find_input(root: Path) -> tuple[Path, list[str]]:
    """The one usable input inside an upload staging tree: a rosbag2 folder, else a lone
    .db3/.mcap, else the folder with the most .npy/.npz frames, else a .jsonl."""
    bags: list[Path] = []
    lone: list[Path] = []
    frame_dirs: list[tuple[int, Path]] = []
    jsonls: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS)
        here = Path(dirpath)
        names = [f for f in filenames if not f.startswith(".")]
        storage = [f for f in names if f.lower().endswith(BAG_SUFFIXES)]
        if "metadata.yaml" in names and storage:
            bags.append(here)
            dirnames[:] = []
            continue
        lone.extend(here / f for f in storage)
        n_frames = sum(1 for f in names if f.lower().endswith(FRAME_SUFFIXES))
        if n_frames:
            frame_dirs.append((n_frames, here))
        jsonls.extend(here / f for f in names if f.lower().endswith(".jsonl"))
    warnings: list[str] = []

    def pick(cands: list[Path], what: str) -> Path:
        best = max(cands, key=tree_size)
        if len(cands) > 1:
            warnings.append(f"найдено несколько {what}, использована {best.name}")
        return best

    if bags:
        return pick(bags, "записей rosbag2"), warnings
    if lone:
        return pick(lone, "файлов .db3/.mcap"), warnings
    if frame_dirs:
        best = max(frame_dirs, key=lambda x: x[0])[1]
        if len(frame_dirs) > 1:
            warnings.append(f"кадры .npy/.npz найдены в нескольких папках, использована {best.name}")
        return best, warnings
    if jsonls:
        return pick(jsonls, "файлов .jsonl"), warnings
    raise ProbeError("В загрузке не найдено ни записи rosbag2 (metadata.yaml + .db3/.mcap), "
                     "ни кадров .npy/.npz, ни результатов .jsonl")


# --- zip ----------------------------------------------------------------------------------------

def safe_extract_zip(zip_path: Path, dest: Path, max_total: int) -> int:
    """Unpack ``zip_path`` under ``dest`` with zip-slip, symlink and zip-bomb guards; returns the
    bytes written. Raises ProbeError (nothing usable is left half-written on failure)."""
    import shutil
    import stat

    try:
        zf = zipfile.ZipFile(zip_path)
    except (zipfile.BadZipFile, OSError) as exc:
        raise ProbeError(f"Архив {zip_path.name} повреждён или это не .zip") from exc
    written = 0
    with zf:
        infos = zf.infolist()
        if len(infos) > MAX_ZIP_MEMBERS:
            raise ProbeError("В архиве слишком много файлов")
        plan: list[tuple[zipfile.ZipInfo, Path]] = []
        declared = 0
        for info in infos:
            if info.is_dir():
                continue
            if stat.S_ISLNK(info.external_attr >> 16):
                continue
            try:
                rel = sanitize_relpath(info.filename, allow_backslash=True)
            except UnsafePath as exc:
                raise ProbeError(f"Архив содержит недопустимый путь «{info.filename[:80]}»: {exc}") from exc
            if rel.parts[0] in SKIP_DIRS or rel.name == ".DS_Store":
                continue
            if info.flag_bits & 0x1:
                raise ProbeError("Архивы с паролем не поддерживаются")
            declared += int(info.file_size)
            if declared > max_total:
                raise ProbeError("Архив слишком большой после распаковки")
            if (info.file_size > ZIP_BOMB_MIN and info.compress_size > 0
                    and info.file_size / info.compress_size > ZIP_BOMB_RATIO):
                raise ProbeError("Архив подозрительно сильно сжат (zip-бомба?) — распаковка отменена")
            plan.append((info, dest.joinpath(*rel.parts)))
        free = shutil.disk_usage(dest if dest.exists() else dest.parent).free
        if declared > free - 64 * 1024 ** 2:
            raise ProbeError("Недостаточно места на диске для распаковки архива")
        dest.mkdir(parents=True, exist_ok=True)
        root = dest.resolve()
        for info, target in plan:
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise ProbeError(f"Архив содержит конфликтующие пути: {info.filename[:80]}") from exc
            if not is_within(target.parent.resolve(), root) or target.is_symlink() or target.is_dir():
                raise ProbeError("Архив содержит недопустимый путь")
            left = int(info.file_size)
            try:
                with zf.open(info) as src, open(target, "wb") as out:
                    while True:
                        chunk = src.read(1024 * 1024)
                        if not chunk:
                            break
                        left -= len(chunk)
                        written += len(chunk)
                        if left < 0 or written > max_total:
                            raise ProbeError("Архив повреждён: размер файла больше заявленного")
                        out.write(chunk)
            except ProbeError:
                raise
            except (zipfile.BadZipFile, OSError, EOFError, RuntimeError, NotImplementedError) as exc:
                raise ProbeError(f"Архив повреждён: не удалось распаковать {info.filename[:80]}") from exc
    return written
