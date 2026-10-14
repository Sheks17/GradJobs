import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from services.api.app.db.session import Base
from services.api.app.models.job import JobSource


@pytest.fixture(autouse=True)
def isolated_public_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("COLLECTOR_CACHE_DIR", str(tmp_path / "public-cache"))


@pytest.fixture
def db():
    url = os.environ.get("TEST_DATABASE_URL")
    schema = "test_" + uuid4().hex
    if url:
        engine = create_engine(url)
        with engine.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine.dispose()
        engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    if url:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    engine.dispose()


@pytest.fixture
def source(db):
    source = JobSource(name="Demo", source_type="manual", board_identifier="test")
    db.add(source)
    db.flush()
    return source
