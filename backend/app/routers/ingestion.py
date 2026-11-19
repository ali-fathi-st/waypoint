"""
Job collection over HTTP, for scripts and other automations. (The website
doesn't call these; it reads the latest run from GET /settings.)

    POST /api/v1/ingestion/runs            collect every enabled source now
    POST /api/v1/ingestion/runs?source=x   collect one source now
    GET  /api/v1/ingestion/runs            the latest runs, with any errors

A run makes real requests to the job boards and can take a minute.
"""

from datetime import datetime
from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.db import get_db
from app.ingestion.run import run_all, run_source
from app.schemas import CollectedSource

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion"])


class RunError(BaseModel):
    identifier: str | None
    error: str


class IngestionRun(BaseModel):
    id: int
    source: CollectedSource
    started_at: datetime
    finished_at: datetime | None
    status: Literal["running", "succeeded", "partial", "failed"]
    fetched: int
    inserted: int
    updated: int
    skipped: int
    failed: int
    errors: list[RunError]


@router.post("/runs", response_model=list[IngestionRun])
async def start_run(source: CollectedSource | None = None) -> list[IngestionRun]:
    runs = await run_in_threadpool(lambda: [run_source(source)] if source else run_all())
    return [IngestionRun(**r) for r in runs]


@router.get("/runs", response_model=list[IngestionRun])
def list_runs(
    limit: int = Query(default=20, ge=1, le=200), db: psycopg.Connection = Depends(get_db)
) -> list[IngestionRun]:
    rows = db.execute("SELECT * FROM ingestion_runs ORDER BY started_at DESC, id DESC LIMIT %s", (limit,)).fetchall()
    return [IngestionRun(**r) for r in rows]
