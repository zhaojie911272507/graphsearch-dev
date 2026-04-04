"""Temporal API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TemporalQueryRequest(BaseModel):
    entity_id: UUID | None = None
    source_id: UUID | None = None
    target_id: UUID | None = None
    query_type: str
    from_time: datetime | None = None
    to_time: datetime | None = None
    timestamp: datetime | None = None


class TemporalQueryResponse(BaseModel):
    query_type: str
    results: list[dict]
    metadata: dict


class SummaryRequest(BaseModel):
    level: str
    entity_id: UUID | None = None
    entity_name: str | None = None
    entity_type: str | None = None
    source_id: UUID | None = None
    target_id: UUID | None = None
    source_name: str | None = None
    target_name: str | None = None
    relation_type: str | None = None
    time_range: tuple[datetime, datetime] | None = None


class SummaryResponse(BaseModel):
    level: str
    content: dict
    generated_at: datetime


class TemporalStatusResponse(BaseModel):
    running: bool
    pending_count: int
    last_merge_time: datetime | None
    interval_minutes: int


class MergeResponse(BaseModel):
    success: bool
    status: TemporalStatusResponse