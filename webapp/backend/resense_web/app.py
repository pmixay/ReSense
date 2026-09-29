"""The FastAPI application: ``create_app()``."""
from __future__ import annotations

import logging
import re
import time
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.gzip import GZipMiddleware

import resense_web
from resense_web.api import jobs as jobs_api
from resense_web.api import presets as presets_api
from resense_web.api import recordings as recordings_api
from resense_web.api import runs as runs_api
from resense_web.api import system as system_api
from resense_web.api.deps import Context
from resense_web.db import Database
from resense_web.jobs import JobError, JobManager
from resense_web.live import router as live_router
from resense_web.presets import PresetError
from resense_web.probe import ProbeError
from resense_web.serverfiles import BrowseError
from resense_web.settings import Settings, get_settings
from resense_web.uploads import UploadError, UploadStore
from resense_web.util import is_within

log = logging.getLogger("resense_web")

DEV_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173", "http://127.0.0.1:4173"]
NO_GZIP = re.compile(r"^/api/(runs/[^/]+/clouds/\d+|recordings/[^/]+/download)$")

NOT_BUILT = """<!doctype html><html lang="ru"><meta charset="utf-8"><title>ReSense</title>
<body style="font-family:sans-serif;padding:40px">
<h1>ReSense web: API работает</h1>
<p>Интерфейс не собран: выполните <code>npm ci &amp;&amp; npm run build</code> в <code>webapp/frontend</code>
или откройте dev-сервер Vite на порту 5173. Проверка API: <a href="/api/system">/api/system</a>.</p>
</body></html>"""

_RU = {
    "missing": "обязательное поле",
    "int_parsing": "должно быть целым числом",
    "int_type": "должно быть целым числом",
    "int_from_float": "должно быть целым числом",
    "float_parsing": "должно быть числом",
    "float_type": "должно быть числом",
    "bool_parsing": "должно быть true или false",
    "bool_type": "должно быть true или false",
    "string_type": "должно быть строкой",
    "string_too_long": "слишком длинное значение",
    "greater_than_equal": "должно быть не меньше {ge}",
    "less_than_equal": "должно быть не больше {le}",
    "greater_than": "должно быть больше {gt}",
    "less_than": "должно быть меньше {lt}",
    "extra_forbidden": "неизвестное поле",
    "json_invalid": "некорректный JSON",
    "dict_type": "должно быть объектом",
    "model_type": "должно быть объектом",
    "model_attributes_type": "должно быть объектом",
    "list_type": "должно быть списком",
}


def _ru_error(err: dict) -> str:
    loc = ".".join(str(x) for x in err.get("loc", ()) if x not in ("body", "query", "path", "header"))
    tpl = _RU.get(err.get("type", ""), "некорректное значение")
    try:
        msg = tpl.format(**(err.get("ctx") or {}))
    except (KeyError, IndexError, ValueError):
        msg = tpl
    return f"«{loc}» {msg}" if loc else msg


class SelectiveGZip:
    """GZip for JSON / text, but not for the binary clouds and zip downloads."""

    def __init__(self, app, minimum_size: int = 1024):
        self.app = app
        self.gzip = GZipMiddleware(app, minimum_size=minimum_size, compresslevel=5)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and NO_GZIP.match(scope.get("path", "")):
            await self.app(scope, receive, send)
        else:
            await self.gzip(scope, receive, send)


def _install_handlers(app: FastAPI) -> None:
    async def _domain(_r: Request, exc) -> JSONResponse:
        return JSONResponse({"detail": exc.message}, status_code=exc.status)

    for cls in (UploadError, BrowseError, PresetError, JobError):
        app.add_exception_handler(cls, _domain)

    @app.exception_handler(ProbeError)
    async def _probe(_r: Request, exc: ProbeError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=422)

    @app.exception_handler(RequestValidationError)
    async def _validation(_r: Request, exc: RequestValidationError) -> JSONResponse:
        errs = exc.errors()
        text = "; ".join(_ru_error(e) for e in errs[:3]) or "некорректные данные"
        return JSONResponse({"detail": f"Некорректный запрос: {text}"}, status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_r: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail
        if exc.status_code == 404 and detail in ("Not Found", None, ""):
            detail = "Не найдено"
        elif exc.status_code == 405 and detail in ("Method Not Allowed", None, ""):
            detail = "Метод не поддерживается"
        return JSONResponse({"detail": detail}, status_code=exc.status_code, headers=getattr(exc, "headers", None))

    @app.exception_handler(Exception)
    async def _crash(_r: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error", exc_info=exc)
        return JSONResponse({"detail": "Внутренняя ошибка сервера"}, status_code=500)


def _mount_frontend(app: FastAPI, settings: Settings) -> None:
    dist = settings.frontend_dist

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(404, "Не найдено")
        index = dist / "index.html"
        if not index.is_file():
            return HTMLResponse(NOT_BUILT, status_code=200)
        if full_path:
            candidate = (dist / full_path).resolve()
            if is_within(candidate, dist.resolve()) and candidate.is_file():
                cache = "public, max-age=31536000, immutable" if full_path.startswith("assets/") else "no-cache"
                return FileResponse(candidate, headers={"Cache-Control": cache})
            if full_path.startswith("assets/"):     # a stale chunk after a rebuild: 404, not index.html
                raise HTTPException(404, "Не найдено")
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


def create_app(settings: Settings | None = None, *, start_jobs: bool = True,
               worker_command: Callable[[str], list[str]] | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        settings.ensure_dirs()
        db = Database(settings.db_path)
        jobs = JobManager(settings, db)
        if worker_command is not None:
            jobs.worker_command = worker_command
        uploads = UploadStore(settings)
        uploads.cleanup_stale()
        app.state.ctx = Context(settings=settings, db=db, jobs=jobs, uploads=uploads, started=time.time())
        if start_jobs:
            jobs.start()
        try:
            yield
        finally:
            jobs.stop()
            db.close()

    app = FastAPI(title="ReSense web", version=resense_web.__version__, lifespan=lifespan,
                  docs_url="/api/docs", redoc_url=None, openapi_url="/api/openapi.json")
    app.add_middleware(SelectiveGZip, minimum_size=1024)
    app.add_middleware(CORSMiddleware, allow_origins=DEV_ORIGINS, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])
    _install_handlers(app)
    for module in (system_api, recordings_api, jobs_api, runs_api, presets_api):
        app.include_router(module.router, prefix="/api")
    app.include_router(live_router)          # declares the full path /api/live/sim
    _mount_frontend(app, settings)
    return app
