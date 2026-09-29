"""Detector parameter presets. The built-in ``standard`` preset (the sealed configs/default.yaml,
no overrides) is not stored: it always exists and cannot be changed."""
from __future__ import annotations

from resense_web.db import Database, jload
from resense_web.util import dumps, new_id, now_iso

STANDARD_ID = "standard"
STANDARD = {
    "id": STANDARD_ID,
    "name": "Стандарт 1.0",
    "description": "Опечатанные параметры детектора (configs/default.yaml, 27.09) — как в ноде ROS 2",
    "builtin": True,
    "overrides": {},
    "created_at": "2026-09-27T20:55:07Z",
}
MAX_NAME = 80
MAX_DESCRIPTION = 1000


class PresetError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.message = message


def to_api(row: dict) -> dict:
    return {"id": row["id"], "name": row["name"], "description": row["description"] or "",
            "builtin": False, "overrides": jload(row["overrides"], {}), "created_at": row["created_at"]}


def list_all(db: Database) -> list[dict]:
    rows = db.query("SELECT * FROM presets ORDER BY created_at, rowid")
    return [dict(STANDARD)] + [to_api(r) for r in rows]


def get(db: Database, preset_id: str) -> dict | None:
    if preset_id == STANDARD_ID:
        return dict(STANDARD)
    row = db.one("SELECT * FROM presets WHERE id = ?", (preset_id,))
    return to_api(row) if row else None


def _clean_name(db: Database, name: str | None, exclude_id: str | None = None) -> str:
    name = (name or "").strip()
    if not name:
        raise PresetError(422, "Укажите название пресета")
    if len(name) > MAX_NAME:
        raise PresetError(422, f"Название пресета длиннее {MAX_NAME} символов")
    taken = {STANDARD["name"].lower()} | {
        r["name"].strip().lower() for r in db.query("SELECT id, name FROM presets") if r["id"] != exclude_id}
    if name.lower() in taken:
        raise PresetError(409, "Пресет с таким названием уже есть")
    return name


def _clean_overrides(overrides) -> dict:
    from resense_web import params
    if overrides is None:
        return {}
    if not isinstance(overrides, dict):
        raise PresetError(422, "Параметры пресета должны быть объектом «параметр: значение»")
    try:
        return params.validate_overrides(overrides)
    except ValueError as exc:
        raise PresetError(422, str(exc)) from exc


def _clean_description(text: str | None) -> str:
    text = (text or "").strip()
    if len(text) > MAX_DESCRIPTION:
        raise PresetError(422, f"Описание длиннее {MAX_DESCRIPTION} символов")
    return text


def create(db: Database, name: str | None, description: str | None, overrides) -> dict:
    row = {"id": new_id(), "name": _clean_name(db, name), "description": _clean_description(description),
           "overrides": dumps(_clean_overrides(overrides)), "created_at": now_iso()}
    db.insert("presets", row)
    return to_api(row)


def update(db: Database, preset_id: str, fields: dict) -> dict:
    if preset_id == STANDARD_ID:
        raise PresetError(403, "Встроенный пресет «Стандарт 1.0» изменить нельзя — сделайте копию")
    row = db.one("SELECT * FROM presets WHERE id = ?", (preset_id,))
    if row is None:
        raise PresetError(404, "Пресет не найден")
    changes = {}
    if fields.get("name") is not None:
        changes["name"] = _clean_name(db, fields["name"], exclude_id=preset_id)
    if fields.get("description") is not None:
        changes["description"] = _clean_description(fields["description"])
    if "overrides" in fields and fields["overrides"] is not None:
        changes["overrides"] = dumps(_clean_overrides(fields["overrides"]))
    if changes:
        db.update("presets", preset_id, changes)
    return to_api(db.one("SELECT * FROM presets WHERE id = ?", (preset_id,)))


def delete(db: Database, preset_id: str) -> None:
    if preset_id == STANDARD_ID:
        raise PresetError(403, "Встроенный пресет «Стандарт 1.0» удалить нельзя")
    if db.execute("DELETE FROM presets WHERE id = ?", (preset_id,)) == 0:
        raise PresetError(404, "Пресет не найден")
