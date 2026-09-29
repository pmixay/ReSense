"""The «Папка на сервере» browser: a read-only view of ``RESENSE_DATA`` that never leaves it
(symlinks are resolved and anything pointing outside the root is refused or hidden)."""
from __future__ import annotations

import os
from pathlib import Path

from resense_web.probe import BAG_SUFFIXES, FRAME_SUFFIXES, bag_pc2_count
from resense_web.util import is_within, natural_key

MAX_ENTRIES = 2000


class BrowseError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def resolve(root: Path, rel: str | None) -> tuple[Path, str]:
    """(real path, normalized relative path) of ``rel`` under ``root``; BrowseError otherwise."""
    rel = (rel or "").strip()
    if "\x00" in rel or "\\" in rel:
        raise BrowseError(400, "Недопустимый путь")
    if rel.startswith("/") or rel.startswith("~"):
        raise BrowseError(400, "Путь должен быть относительным")
    parts = [p for p in rel.split("/") if p not in ("", ".")]
    if ".." in parts:
        raise BrowseError(400, "Путь не может содержать «..»")
    try:
        real_root = root.resolve(strict=True)
    except (OSError, RuntimeError):
        raise BrowseError(404, f"Папка данных на сервере не найдена: {root}") from None
    try:
        real = real_root.joinpath(*parts).resolve(strict=True)
    except (OSError, RuntimeError):
        raise BrowseError(404, "Путь не найден") from None
    if not is_within(real, real_root):
        raise BrowseError(403, "Путь ведёт за пределы папки данных")
    return real, "/".join(parts)


def _dir_info(p: Path) -> dict:
    """is_bag / is_npy_dir / n_frames / size of a directory from one scandir (cheap)."""
    has_meta = False
    storage_size = 0
    n_storage = 0
    n_frames_files = 0
    try:
        with os.scandir(p) as it:
            for i, e in enumerate(it):
                if i > 200_000:
                    break
                name = e.name.lower()
                if name == "metadata.yaml":
                    has_meta = True
                elif name.endswith(BAG_SUFFIXES) and e.is_file():
                    n_storage += 1
                    storage_size += e.stat().st_size
                elif name.endswith(FRAME_SUFFIXES):
                    n_frames_files += 1
    except OSError:
        pass
    is_bag = has_meta and n_storage > 0
    info = {"is_bag": is_bag, "is_npy_dir": (not is_bag) and n_frames_files > 0,
            "size_bytes": storage_size if is_bag else 0}
    if is_bag:
        info["n_frames"] = bag_pc2_count(p)
    elif n_frames_files:
        info["n_frames"] = n_frames_files
    return info


def listing(root: Path, rel: str | None) -> dict:
    real, norm = resolve(root, rel)
    if not real.is_dir():
        raise BrowseError(400, "Это файл, а не папка")
    real_root = root.resolve()
    entries = []
    truncated = False
    try:
        items = sorted(os.scandir(real), key=lambda e: natural_key(e.name))
    except OSError:
        raise BrowseError(403, "Нет доступа к папке") from None
    for e in items:
        if e.name.startswith("."):
            continue
        try:
            target = Path(e.path).resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if not is_within(target, real_root):
            continue
        child_rel = f"{norm}/{e.name}" if norm else e.name
        if target.is_dir():
            entry = {"name": e.name, "path": child_rel, "type": "dir", **_dir_info(target)}
        else:
            try:
                size = target.stat().st_size
            except OSError:
                continue
            entry = {"name": e.name, "path": child_rel, "type": "file", "size_bytes": size,
                     "is_bag": False, "is_npy_dir": False}
        entries.append(entry)
        if len(entries) >= MAX_ENTRIES:
            truncated = True
            break
    entries.sort(key=lambda x: (x["type"] != "dir", natural_key(x["name"])))
    parent = None
    if norm:
        parent = norm.rsplit("/", 1)[0] if "/" in norm else ""
    return {"path": norm, "parent": parent, "entries": entries, "truncated": truncated}
