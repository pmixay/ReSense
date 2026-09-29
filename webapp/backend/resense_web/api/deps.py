"""Shared state of the running app, reachable from every route."""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request

from resense_web.db import Database
from resense_web.jobs import JobManager
from resense_web.settings import Settings
from resense_web.uploads import UploadStore


@dataclass
class Context:
    settings: Settings
    db: Database
    jobs: JobManager
    uploads: UploadStore
    started: float


def get_ctx(request: Request) -> Context:
    return request.app.state.ctx


def not_found(message: str) -> HTTPException:
    return HTTPException(status_code=404, detail=message)
