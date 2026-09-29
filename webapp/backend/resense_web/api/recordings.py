"""Recordings (sources): uploads, the server folder browser, demo bags, labels."""
from __future__ import annotations

import json
import os
import shutil
import zipfile

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect

from resense_web import recordings as rec_mod
from resense_web import serverfiles
from resense_web.api.deps import Context, get_ctx, not_found
from resense_web.probe import probe_path
from resense_web.uploads import disk_free, unlink_quiet
from resense_web.util import (UnsafePath, atomic_write_json, download_filename, is_within, new_id,
                              sanitize_relpath)

router = APIRouter()

WRITE_CHUNK = 4 * 1024 * 1024
DISK_MARGIN = 256 * 1024 ** 2
MAX_LABELS_BYTES = 64 * 1024 ** 2
SCENARIOS = ("approach", "crossing", "clear")


class UploadCreate(BaseModel):
    name: str | None = Field(default=None, max_length=200)


class FromServer(BaseModel):
    path: str = Field(max_length=4096)


class DemoCreate(BaseModel):
    scenario: str = "approach"
    seconds: float = Field(default=15.0, ge=5, le=60)
    seed: int | None = Field(default=None, ge=0, le=2 ** 31 - 1)


def _recording_or_404(ctx: Context, rec_id: str) -> dict:
    row = rec_mod.get(ctx.db, rec_id)
    if row is None:
        raise not_found("Запись не найдена")
    return row


# --- uploads ------------------------------------------------------------------------------------

@router.post("/uploads")
def create_upload(body: UploadCreate | None = Body(default=None), ctx: Context = Depends(get_ctx)) -> dict:
    return {"upload_id": ctx.uploads.create(body.name if body else None)}


@router.put("/uploads/{upload_id}/files")
async def put_upload_file(upload_id: str, request: Request, path: str = Query(..., max_length=4096),
                          ctx: Context = Depends(get_ctx)) -> dict:
    store = ctx.uploads
    try:
        rel = sanitize_relpath(path)
    except UnsafePath as exc:
        raise HTTPException(422, str(exc)) from None
    dest = store.target(upload_id, rel)
    declared = request.headers.get("content-length", "")
    if declared.isdigit():
        n = int(declared)
        if n > ctx.settings.max_upload_bytes:
            gb = ctx.settings.max_upload_bytes / 1024 ** 3
            raise HTTPException(413, f"Превышен максимальный размер загрузки ({gb:g} ГБ)")
        if n > disk_free(ctx.settings.uploads_dir) - DISK_MARGIN:
            raise HTTPException(507, "Недостаточно места на диске сервера")
    existing = dest.stat().st_size if dest.is_file() else 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.part-{new_id(6)}")
    reserved = written = 0
    fh = open(tmp, "wb")
    try:
        buf = bytearray()
        async for chunk in request.stream():
            if not chunk:
                continue
            store.reserve(upload_id, len(chunk))
            reserved += len(chunk)
            buf += chunk
            if len(buf) >= WRITE_CHUNK:
                data, buf = bytes(buf), bytearray()
                await run_in_threadpool(fh.write, data)
                written += len(data)
        if buf:
            await run_in_threadpool(fh.write, bytes(buf))
            written += len(buf)
        fh.close()
        os.replace(tmp, dest)
    except ClientDisconnect:
        fh.close()
        unlink_quiet(tmp)
        store.release(upload_id, reserved)
        return Response(status_code=400)
    except BaseException:
        fh.close()
        unlink_quiet(tmp)
        store.release(upload_id, reserved)
        raise
    if existing:
        store.release(upload_id, existing)
    return {"path": rel.as_posix(), "size_bytes": written}


@router.post("/uploads/{upload_id}/finalize", status_code=201)
def finalize_upload(upload_id: str, ctx: Context = Depends(get_ctx)) -> dict:
    probe, name, warnings, rec_dir = ctx.uploads.finalize(upload_id)
    row = rec_mod.insert(ctx.db, probe, name=name, source="upload", rec_id=rec_dir.name, extra_warnings=warnings)
    return rec_mod.to_api(ctx.settings, row)


@router.delete("/uploads/{upload_id}", status_code=204)
def delete_upload(upload_id: str, ctx: Context = Depends(get_ctx)) -> Response:
    ctx.uploads.delete(upload_id)
    return Response(status_code=204)


# --- server folder ------------------------------------------------------------------------------

@router.get("/server-files")
def server_files(path: str = Query(default="", max_length=4096), ctx: Context = Depends(get_ctx)) -> dict:
    return serverfiles.listing(ctx.settings.server_root, path)


@router.post("/recordings/from-server", status_code=201)
def register_from_server(body: FromServer, response: Response, ctx: Context = Depends(get_ctx)) -> dict:
    real, _norm = serverfiles.resolve(ctx.settings.server_root, body.path)
    probe = probe_path(real)
    if not is_within(probe.path.resolve(), ctx.settings.server_root.resolve()):
        raise HTTPException(403, "Путь ведёт за пределы папки данных")
    existing = ctx.db.one("SELECT * FROM recordings WHERE source = 'server' AND path = ?", (str(probe.path),))
    if existing:
        response.status_code = 200
        return rec_mod.to_api(ctx.settings, existing)
    row = rec_mod.insert(ctx.db, probe, name=probe.source_name, source="server")
    return rec_mod.to_api(ctx.settings, row)


# --- demo ---------------------------------------------------------------------------------------

@router.post("/recordings/demo", status_code=201)
def create_demo(body: DemoCreate | None = Body(default=None), ctx: Context = Depends(get_ctx)) -> dict:
    body = body or DemoCreate()
    if body.scenario not in SCENARIOS:
        raise HTTPException(422, "Сценарий должен быть одним из: approach, crossing, clear")
    from resense_web import demo as demo_mod
    rec_id = new_id()
    rec_dir = ctx.settings.recordings_dir / rec_id
    out = rec_dir / f"demo_{body.scenario}"
    seed = 0 if body.seed is None else int(body.seed)
    try:
        info = demo_mod.generate_demo_bag(out, scenario=body.scenario, seconds=float(body.seconds), seed=seed)
        probe = probe_path(out)
    except ValueError as exc:
        shutil.rmtree(rec_dir, ignore_errors=True)
        raise HTTPException(422, str(exc)) from None
    except BaseException:
        shutil.rmtree(rec_dir, ignore_errors=True)
        raise
    name = (info or {}).get("name") or probe.source_name
    row = rec_mod.insert(ctx.db, probe, name=name, source="demo", rec_id=rec_id,
                         meta={"scenario": body.scenario, "seconds": float(body.seconds), "seed": seed})
    return rec_mod.to_api(ctx.settings, row)


# --- recordings ---------------------------------------------------------------------------------

@router.get("/recordings")
def list_recordings(ctx: Context = Depends(get_ctx)) -> list[dict]:
    return [rec_mod.to_api(ctx.settings, r) for r in rec_mod.list_all(ctx.db)]


@router.get("/recordings/{rec_id}")
def get_recording(rec_id: str, ctx: Context = Depends(get_ctx)) -> dict:
    return rec_mod.to_api(ctx.settings, _recording_or_404(ctx, rec_id))


@router.delete("/recordings/{rec_id}", status_code=204)
def delete_recording(rec_id: str, ctx: Context = Depends(get_ctx)) -> Response:
    row = _recording_or_404(ctx, rec_id)
    ctx.jobs.cancel_for_recording(rec_id)
    with ctx.db.transaction() as db:
        db.execute("UPDATE runs SET recording_id = NULL WHERE recording_id = ?", (rec_id,))
        db.execute("DELETE FROM recordings WHERE id = ?", (rec_id,))
    rec_mod.remove_files(ctx.settings, row)
    return Response(status_code=204)


def _build_zip(src, dest) -> None:
    tmp = dest.with_name(f".{dest.name}.{new_id(6)}.tmp")
    base = src if src.is_dir() else src.parent
    try:
        with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=True) as zf:
            for p in sorted(base.rglob("*")):
                if p.is_file() and not p.is_symlink():
                    zf.write(p, arcname=f"{base.name}/{p.relative_to(base).as_posix()}")
        os.replace(tmp, dest)
    except BaseException:
        unlink_quiet(tmp)
        raise


@router.get("/recordings/{rec_id}/download")
def download_recording(rec_id: str, ctx: Context = Depends(get_ctx)) -> FileResponse:
    row = _recording_or_404(ctx, rec_id)
    if row["source"] != "demo":
        raise HTTPException(403, "Скачать можно только демонстрационную запись")
    src = rec_mod.recording_dir(ctx.settings, rec_id)
    bag = next((p for p in src.iterdir() if p.is_dir()), None) if src.is_dir() else None
    if bag is None:
        raise not_found("Файлы демо-записи не найдены")
    dest = ctx.settings.cache_dir / f"{rec_id}.zip"
    if not dest.is_file():
        ctx.settings.cache_dir.mkdir(parents=True, exist_ok=True)
        _build_zip(bag, dest)
    return FileResponse(dest, media_type="application/zip", filename=download_filename(row["name"], ".zip"))


@router.put("/recordings/{rec_id}/labels")
async def put_labels(rec_id: str, request: Request, ctx: Context = Depends(get_ctx)) -> dict:
    row = _recording_or_404(ctx, rec_id)
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > MAX_LABELS_BYTES:
        raise HTTPException(413, "Файл разметки слишком большой")
    raw = bytearray()
    async for chunk in request.stream():
        raw += chunk
        if len(raw) > MAX_LABELS_BYTES:
            raise HTTPException(413, "Файл разметки слишком большой")
    try:
        data = json.loads(bytes(raw).decode("utf-8-sig"))
    except (UnicodeDecodeError, ValueError):
        raise HTTPException(422, "Файл разметки — не корректный JSON") from None
    if not isinstance(data, dict):
        raise HTTPException(422, "Файл разметки должен быть JSON-объектом в формате labels/*.json")
    from resense_web import evaluation
    try:
        await run_in_threadpool(evaluation.validate_labels, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc) or "Это не файл разметки") from None
    meta = data.get("_meta") if isinstance(data.get("_meta"), dict) else {}
    name = str(meta.get("bag") or meta.get("name") or "разметка")[:120]
    path = rec_mod.recording_dir(ctx.settings, rec_id) / rec_mod.LABELS_FILE
    await run_in_threadpool(atomic_write_json, path, data)
    ctx.db.update("recordings", rec_id, {"labels_name": name})
    row = rec_mod.get(ctx.db, rec_id) or row
    return rec_mod.to_api(ctx.settings, row)


@router.delete("/recordings/{rec_id}/labels")
def delete_labels(rec_id: str, ctx: Context = Depends(get_ctx)) -> dict:
    _recording_or_404(ctx, rec_id)
    unlink_quiet(rec_mod.recording_dir(ctx.settings, rec_id) / rec_mod.LABELS_FILE)
    ctx.db.update("recordings", rec_id, {"labels_name": None})
    return rec_mod.to_api(ctx.settings, rec_mod.get(ctx.db, rec_id))

