"""Request schemas for the evaluation-config endpoints.

An evaluation config is a reusable, org-wide judge recipe (model + optional
custom rubric prompt + metric set) used to re-grade a frozen ``eval_results``
run. Validation of metric names / threshold ranges / custom-prompt rules lives
in ``EvaluationConfigService`` so the same rules apply to every entry point;
these schemas only shape the wire contract.
"""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EvaluationConfigCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    judge_model: str = Field(min_length=1, max_length=120)
    judge_engine: str = Field(default="deepeval", max_length=32)
    judge_prompt: Optional[str] = None
    description: Optional[str] = None
    metrics_enabled: Optional[List[str]] = None
    metric_threshold: Optional[float] = None
    metric_thresholds: Optional[dict] = None
    is_default: bool = False


class EvaluationConfigUpdateRequest(BaseModel):
    """Partial update — only sent fields are applied (via exclude_unset)."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    judge_model: Optional[str] = Field(default=None, min_length=1, max_length=120)
    judge_engine: Optional[str] = Field(default=None, max_length=32)
    judge_prompt: Optional[str] = None
    description: Optional[str] = None
    metrics_enabled: Optional[List[str]] = None
    metric_threshold: Optional[float] = None
    metric_thresholds: Optional[dict] = None
    is_default: Optional[bool] = None


class RunEvaluationConfigRequest(BaseModel):
    source_run_id: UUID
    evaluation_config_id: UUID


class EvaluationConfigResultsListRequest(BaseModel):
    source_run_id: UUID
    config_run_ids: Optional[List[UUID]] = None
