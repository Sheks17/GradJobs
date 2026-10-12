"""Validate hosted ingestion configuration without revealing connection strings."""

from services.api.app.core.config import get_settings


def require_postgres():
    if not get_settings().database_url.startswith("postgresql+psycopg://"):
        raise ValueError("Hosted ingestion requires a persistent PostgreSQL database")


if __name__ == "__main__":
    require_postgres()
    print("Production PostgreSQL configuration validated")
