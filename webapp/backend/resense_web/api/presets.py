"""Detector parameter presets and their schema."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from resense_web import presets as presets_mod
from resense_web.api.deps import Context, get_ctx, not_found

router = APIRouter()


class PresetCreate(BaseModel):
    name: str
    description: str | None = None
    overrides: dict[str, Any] = {}


class PresetPatch(BaseModel):
    name: str | None = None
    description: str | None = None
    overrides: dict[str, Any] | None = None


@router.get("/presets")
def list_presets(ctx: Context = Depends(get_ctx)) -> list[dict]:
    return presets_mod.list_all(ctx.db)


@router.get("/presets/schema")
def preset_schema() -> list[dict]:
    from resense_web import params
    return params.PARAM_SPECS


@router.get("/presets/{preset_id}")
def get_preset(preset_id: str, ctx: Context = Depends(get_ctx)) -> dict:
    p = presets_mod.get(ctx.db, preset_id)
    if p is None:
        raise not_found("Набор параметров не найден")
    return p


@router.post("/presets", status_code=201)
def create_preset(body: PresetCreate, ctx: Context = Depends(get_ctx)) -> dict:
    return presets_mod.create(ctx.db, body.name, body.description, body.overrides)


@router.patch("/presets/{preset_id}")
def update_preset(preset_id: str, body: PresetPatch, ctx: Context = Depends(get_ctx)) -> dict:
    return presets_mod.update(ctx.db, preset_id, body.model_dump(exclude_unset=True))


@router.delete("/presets/{preset_id}", status_code=204)
def delete_preset(preset_id: str, ctx: Context = Depends(get_ctx)) -> Response:
    presets_mod.delete(ctx.db, preset_id)
    return Response(status_code=204)
