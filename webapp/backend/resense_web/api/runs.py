"""Runs: list / detail / rename / delete, chart series, frame paging, clouds, downloads."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from resense_web import clouds as clouds_mod
from resense_web import recordings as rec_mod
from resense_web import results
from resense_web import runs as runs_mod
from resense_web.api.deps import Context, get_ctx, not_found
from resense_web.util import content_disposition, download_filename, dumps, now_iso

router = APIRouter()
MAX_PAGE = 500
CLOUD_CACHE = "public, max-age=31536000, immutable"


class RunPatch(BaseModel):
    name: str = Field(max_length=200)


def _row(ctx: Context, run_id: str) -> dict:
    row = runs_mod.get(ctx.db, run_id)
    if row is None:
        raise not_found("Прогон не найден")
    return row


def _json(body: str | bytes, status: int = 200, headers: dict | None = None) -> Response:
    return Response(content=body, status_code=status, media_type="application/json", headers=headers)


def _detail(ctx: Context, row: dict) -> dict:
    episodes, events = runs_mod.episodes(ctx.settings, row["id"])
    rec = rec_mod.get(ctx.db, row["recording_id"]) if row["recording_id"] else None
    return {**runs_mod.to_api(row), "episodes": episodes, "events": events,
            "recording": rec_mod.to_api(ctx.settings, rec) if rec else None}


@router.get("/runs")
def list_runs(ctx: Context = Depends(get_ctx)) -> list[dict]:
    return [runs_mod.to_api(r) for r in runs_mod.list_all(ctx.db)]


@router.get("/runs/{run_id}")
def get_run(run_id: str, ctx: Context = Depends(get_ctx)) -> Response:
    return _json(dumps(_detail(ctx, _row(ctx, run_id))))


@router.patch("/runs/{run_id}")
def rename_run(run_id: str, body: RunPatch, ctx: Context = Depends(get_ctx)) -> dict:
    _row(ctx, run_id)
    name = body.name.strip()
    if not name:
        raise HTTPException(422, "Укажите название прогона")
    ctx.db.update("runs", run_id, {"name": name})
    return runs_mod.to_api(_row(ctx, run_id))


@router.delete("/runs/{run_id}", status_code=204)
def delete_run(run_id: str, ctx: Context = Depends(get_ctx)) -> Response:
    _row(ctx, run_id)
    ctx.db.execute("DELETE FROM runs WHERE id = ?", (run_id,))
    runs_mod.remove(ctx.settings, run_id)
    return Response(status_code=204)


@router.get("/runs/{run_id}/series")
def run_series(run_id: str, ctx: Context = Depends(get_ctx)) -> Response:
    _row(ctx, run_id)
    try:
        return _json(runs_mod.series_bytes(ctx.settings, run_id))
    except FileNotFoundError:
        raise not_found("Результаты прогона не найдены") from None


@router.get("/runs/{run_id}/frames")
def run_frames(run_id: str, start: int = Query(default=0, ge=0, alias="from"),
               count: int = Query(default=100, ge=1), ctx: Context = Depends(get_ctx)) -> Response:
    _row(ctx, run_id)
    count = min(count, MAX_PAGE)
    try:
        lines, total = results.read_lines(runs_mod.run_dir(ctx.settings, run_id), start, count)
    except FileNotFoundError:
        raise not_found("Результаты прогона не найдены") from None
    body = b"".join((f'{{"from":{min(start, total)},"count":{len(lines)},"total":{total},"frames":['.encode(),
                     b",".join(lines), b"]}"))
    return _json(body)


@router.get("/runs/{run_id}/clouds")
def run_clouds(run_id: str, ctx: Context = Depends(get_ctx)) -> dict:
    _row(ctx, run_id)
    index = clouds_mod.load_index(runs_mod.run_dir(ctx.settings, run_id))
    if not index:
        return {"frames": [], "points": 0, "format": clouds_mod.FORMAT}
    return {"frames": index["frames"], "points": int(index.get("points", 0)), "format": clouds_mod.FORMAT}


@router.get("/runs/{run_id}/clouds/{pos}")
def run_cloud(run_id: str, pos: int, ctx: Context = Depends(get_ctx)) -> Response:
    _row(ctx, run_id)
    d = runs_mod.run_dir(ctx.settings, run_id)
    index = clouds_mod.load_index(d)
    blob = clouds_mod.read_cloud(d, index, pos) if index else None
    if blob is None:
        raise not_found("Для этого кадра облако не сохранено")
    return Response(content=blob, media_type="application/octet-stream",
                    headers={"Cache-Control": CLOUD_CACHE, "ETag": f'"{run_id}-{pos}"'})


@router.get("/runs/{run_id}/download/results.jsonl")
def download_results(run_id: str, ctx: Context = Depends(get_ctx)) -> FileResponse:
    row = _row(ctx, run_id)
    path = runs_mod.run_dir(ctx.settings, run_id) / results.RESULTS
    if not path.is_file():
        raise not_found("Результаты прогона не найдены")
    name = download_filename(row["name"], ".results.jsonl")
    return FileResponse(path, media_type="application/x-ndjson",
                        headers={"Content-Disposition": content_disposition(name, f"{run_id}.results.jsonl")})


@router.get("/runs/{run_id}/download/report.json")
def download_report(run_id: str, ctx: Context = Depends(get_ctx)) -> Response:
    row = _row(ctx, run_id)
    detail = _detail(ctx, row)
    doc = runs_mod.read_summary_doc(ctx.settings, run_id)
    report = {"schema": "resense_web_report", "version": 1,
              "run": {k: v for k, v in detail.items() if k not in ("episodes", "events", "recording")},
              "episodes": detail["episodes"], "generated_at": now_iso(),
              "events": detail["events"], "recording": detail["recording"],
              "options": doc.get("options"), "overrides": doc.get("overrides"), "config": doc.get("config")}
    name = download_filename(row["name"], ".report.json")
    return _json(dumps(report), headers={"Content-Disposition": content_disposition(name, f"{run_id}.report.json")})


@router.get("/runs/{run_id}/download/frames.csv")
def download_csv(run_id: str, ctx: Context = Depends(get_ctx)) -> StreamingResponse:
    row = _row(ctx, run_id)
    try:
        runs_mod.series(ctx.settings, run_id)   # 404 / rebuild before the stream starts
    except FileNotFoundError:
        raise not_found("Результаты прогона не найдены") from None
    name = download_filename(row["name"], ".frames.csv")
    return StreamingResponse(runs_mod.frames_csv(ctx.settings, run_id), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": content_disposition(name, f"{run_id}.frames.csv")})
