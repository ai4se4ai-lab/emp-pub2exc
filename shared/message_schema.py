"""
shared/message_schema.py
Inter-agent communication types for the research-to-software pipeline.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentName(str, Enum):
    PAPER_ANALYST = "paper_analyst"
    FORMALIZER = "formalizer"
    ARCHITECT_DEVELOPER = "architect_developer"
    AUDITOR_SUPERVISOR = "auditor_supervisor"
    BROADCAST = "broadcast"


class MessageType(str, Enum):
    OUTPUT = "output"
    REQUEST = "request"
    STATUS = "status"
    ERROR = "error"
    HUMAN_REVIEW_REQUEST = "human_review_request"
    HUMAN_APPROVED = "human_approved"
    RETRY = "retry"


class AgentMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    run_id: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    from_agent: AgentName
    to_agent: AgentName
    message_type: MessageType
    payload: dict[str, Any] = Field(default_factory=dict)
    artifact_refs: list[str] = Field(default_factory=list)
    error_detail: str | None = None
    retry_count: int = 0

    class Config:
        use_enum_values = True


class ResearchIntent(BaseModel):
    """Top-level output of the Paper Analyst agent."""
    run_id: str
    paper_title: str
    paper_abstract: str
    research_questions: list[dict[str, Any]]
    domain_concepts: list[dict[str, Any]]
    methods_models: list[dict[str, Any]]
    datasets: list[dict[str, Any]]
    metrics_results: list[dict[str, Any]]
    confidence_overall: float = Field(ge=0.0, le=1.0)


class Assumption(BaseModel):
    """Logged whenever an agent makes an implicit decision."""
    assumption_id: str = Field(default_factory=lambda: str(uuid4()))
    agent: AgentName
    run_id: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    assumption: str
    confidence: float = Field(ge=0.0, le=1.0)
    impact: str  # "low" | "medium" | "high"
    context: str = ""
