import io

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from services.api.app.core.config import get_settings


def test_migration_upgrade_and_downgrade(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'migration.db').as_posix()}"
    monkeypatch.setenv("DATABASE_URL", url)
    get_settings.cache_clear()
    try:
        config = Config("alembic.ini")
        command.upgrade(config, "head")
        engine = create_engine(url)
        assert {"jobs", "job_sources", "alembic_version"} <= set(inspect(engine).get_table_names())
        assert len(inspect(engine).get_check_constraints("jobs")) == 4
        with engine.connect() as connection:
            from sqlalchemy import text

            definition = connection.scalar(text("SELECT sql FROM sqlite_master WHERE name='jobs'"))
            assert "classification_conflict BOOLEAN DEFAULT 0 NOT NULL" in definition
            assert (
                connection.scalar(
                    text("SELECT count(*) FROM sqlite_master WHERE name='ix_jobs_active_freshness'")
                )
                == 1
            )
        engine.dispose()
        command.check(config)
        command.downgrade(config, "base")
        engine = create_engine(url)
        assert "jobs" not in inspect(engine).get_table_names()
        engine.dispose()
    finally:
        get_settings.cache_clear()


def test_postgresql_migration_uses_jsonb(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused:unused@localhost/unused")
    get_settings.cache_clear()
    try:
        output = io.StringIO()
        config = Config("alembic.ini", output_buffer=output)
        command.upgrade(config, "head", sql=True)
        assert "raw_data JSONB" in output.getvalue()
        assert "TIMESTAMP WITH TIME ZONE" in output.getvalue()
        assert "ix_jobs_active_freshness" in output.getvalue()
        assert "jsonb_array_length(conflict_reasons)" in output.getvalue()
    finally:
        get_settings.cache_clear()
