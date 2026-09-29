"""The job queue: POST/GET/DELETE /api/jobs, cancel, retry, log."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

from resense_web import presets as presets_mod
from resense_web import recordings as rec_mod
from resense_web.api.deps import Context, get_ctx, not_found

router = APIRouter()
STATUSES = {"queued", "running", "done", "failed", "cancelled"}


class JobOptions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str | None = Field(default=None, max_length=512)
    every: int = Field(default=1, ge=1, le=10000)
    start: int = Field(default=0, ge=0)
    limit: int | None = Field(default=None, ge=1)
    clouds: bool = True
    cloud_points: int = Field(default=30000, ge=5000, le=120000)
    ego_speed: float | None = Field(default=None, ge=0, le=50)
    evaluate: bool = True


class JobCreate(BaseModel):
    recording_id: str
    preset_id: str = "standard"
    options: JobOptions | None = None


@router.post("/jobs", status_code=201)
def create_job(body: JobCreate, ctx: Context = Depends(get_ctx)) -> dict:
    rec = rec_mod.get(ctx.db, body.recording_id)
    if rec is None:
        raise not_found("Запись не найдена")
    preset = presets_mod.get(ctx.db, body.preset_id or "standard")
    if preset is None:
        raise not_found("Набор параметров не найден")
    opts = (body.options or JobOptions()).model_dump()
    return ctx.jobs.to_api(ctx.jobs.create(rec, preset, opts))


@router.get("/jobs")
def list_jobs(status: str | None = Query(default=None), ctx: Context = Depends(get_ctx)) -> list[dict]:
    wanted = None
    if status:
        wanted = {s.strip() for s in status.split(",") if s.strip()}
        bad = wanted - STATUSES
        if bad:
            raise HTTPException(422, f"Неизвестный статус задачи: {', '.join(sorted(bad))}")
    positions = ctx.jobs.positions()
    return [ctx.jobs.to_api(r, positions) for r in ctx.jobs.list(wanted)]


@router.delete("/jobs", status_code=204)
def clear_jobs(finished: bool = Query(default=False), ctx: Context = Depends(get_ctx)) -> Response:
    if not finished:
        raise HTTPException(422, "Укажите finished=true, чтобы очистить завершённые задачи")
    ctx.jobs.clear_finished()
    return Response(status_code=204)


@router.get("/jobs/{job_id}")
def get_job(job_id: str, ctx: Context = Depends(get_ctx)) -> dict:
    row = ctx.jobs.get(job_id)
    if row is None:
        raise not_found("Задача не найдена")
    return ctx.jobs.to_api(row)


@router.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str, ctx: Context = Depends(get_ctx)) -> dict:
    return ctx.jobs.to_api(ctx.jobs.cancel(job_id))


@router.post("/jobs/{job_id}/retry", status_code=201)
def retry_job(job_id: str, ctx: Context = Depends(get_ctx)) -> dict:
    return ctx.jobs.to_api(ctx.jobs.retry(job_id))


@router.delete("/jobs/{job_id}", status_code=204)
def delete_job(job_id: str, ctx: Context = Depends(get_ctx)) -> Response:
    ctx.jobs.delete(job_id)
    return Response(status_code=204)


@router.get("/jobs/{job_id}/log", response_class=PlainTextResponse)
def job_log(job_id: str, ctx: Context = Depends(get_ctx)) -> PlainTextResponse:
    if ctx.jobs.get(job_id) is None:
        raise not_found("Задача не найдена")
    return PlainTextResponse(ctx.jobs.log_tail(job_id), media_type="text/plain; charset=utf-8")

