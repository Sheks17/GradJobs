from sqlalchemy import select
from sqlalchemy.orm import Session

from collectors.providers import CAREERS, PROVIDERS, make_collector
from services.api.app.models.job import JobSource
from services.api.app.schemas.sources import SourceCreate


def register_source(db: Session, data: SourceCreate) -> tuple[JobSource, bool]:
    source = db.scalar(
        select(JobSource).where(
            JobSource.source_type == data.provider, JobSource.board_identifier == data.board_token
        )
    )
    if source:
        return source, False
    base_url = PROVIDERS[data.provider].endpoint.format(board=data.board_token)
    careers_url = CAREERS[data.provider].format(board=data.board_token)
    if data.provider == "workday":
        collector = make_collector(
            data.provider, data.board_token, data.company_name, data.provider_config
        )
        try:
            base_url, careers_url = collector.endpoint, collector.careers_url
        finally:
            collector.close()
    source = JobSource(
        name=f"{data.company_name} · {data.provider}",
        company_name=data.company_name,
        source_type=data.provider,
        board_identifier=data.board_token,
        enabled=data.enabled,
        provider_config=data.provider_config,
        careers_url=data.careers_url or careers_url,
        base_url=base_url,
    )
    db.add(source)
    db.flush()
    return source, True
