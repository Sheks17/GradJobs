from dataclasses import asdict
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from collectors.locking import write_lock
from collectors.providers import PROVIDERS, make_collector
from collectors.runner import sync_source
from collectors.sync_all import sync_all
from services.api.app.api.routes import Database
from services.api.app.core.config import get_settings
from services.api.app.models.job import JobSource, SourceSync
from services.api.app.schemas.jobs import SourceOut
from services.api.app.schemas.sources import SourceCreate, SourcePatch, SyncOut
from services.api.app.services.sources import register_source

router = APIRouter()


def development_admin() -> None:
    settings = get_settings()
    if settings.app_env != "development" or not settings.enable_admin_api:
        raise HTTPException(
            403, "Source mutations require development mode and ENABLE_ADMIN_API=true"
        )


Admin = Annotated[None, Depends(development_admin)]


def require_source(db, source_id):
    source = db.get(JobSource, source_id)
    if not source:
        raise HTTPException(404, "Source not found")
    return source


@router.get("/sources/{source_id}", response_model=SourceOut)
def source_detail(source_id: UUID, db: Database):
    return require_source(db, source_id)


@router.get("/sources/{source_id}/history", response_model=list[SyncOut])
def source_history(
    source_id: UUID,
    db: Database,
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    require_source(db, source_id)
    return db.scalars(
        select(SourceSync)
        .where(SourceSync.source_id == source_id)
        .order_by(SourceSync.started_at.desc(), SourceSync.id)
        .offset(offset)
        .limit(limit)
    ).all()


@router.post("/sources", response_model=SourceOut, status_code=201)
def create_source(data: SourceCreate, db: Database, admin: Admin):
    collector = make_collector(
        data.provider, data.board_token, data.company_name, data.provider_config
    )
    try:
        rows = collector.fetch()
        if not rows or not collector.snapshot_complete:
            raise ValueError("Registration requires a complete nonempty snapshot")
        for row in rows:
            collector.normalize(row)
    except Exception:
        raise HTTPException(
            422, "Could not verify this public board; check provider and token"
        ) from None
    finally:
        collector.close()
    write_lock(db)
    source, created = register_source(db, data)
    if not created:
        db.rollback()
        raise HTTPException(409, "Provider and board already registered")
    db.commit()
    return source


@router.patch("/sources/{source_id}", response_model=SourceOut)
def patch_source(source_id: UUID, data: SourcePatch, db: Database, admin: Admin):
    write_lock(db)
    source = require_source(db, source_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        if value is None and key != "careers_url":
            raise HTTPException(422, f"{key} cannot be null")
        setattr(source, key, value)
    source.name = f"{source.company_name} · {source.source_type}"
    db.commit()
    return source


@router.post("/sources/{source_id}/sync")
def sync_registered_source(source_id: UUID, db: Database, admin: Admin):
    source = require_source(db, source_id)
    if source.source_type not in PROVIDERS:
        raise HTTPException(422, "This source has no automated collector")
    collector = make_collector(
        source.source_type,
        source.board_identifier,
        source.company_name or source.name,
        source.provider_config,
    )
    try:
        result = sync_source(db, collector)
    finally:
        collector.close()
    if result.status in {"busy", "disabled"}:
        raise HTTPException(409, f"Source is {result.status}")
    return asdict(result)


@router.post("/sync")
def sync_every_source(admin: Admin):
    # Synchronous development operation. Schedulers use the CLI, not a web request.
    return sync_all()
