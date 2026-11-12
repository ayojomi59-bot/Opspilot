from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    message: str = Field(min_length=3, max_length=4000)


class ActionResult(BaseModel):
    tool: str
    status: Literal["completed", "awaiting_approval", "rejected", "failed"]
    output: dict[str, Any] = Field(default_factory=dict)
    approval_id: str | None = None


class RunResponse(BaseModel):
    run_id: str
    status: str
    plan: list[str]
    results: list[ActionResult]
    created_at: datetime


class ApprovalDecision(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class ApprovalResponse(BaseModel):
    approval_id: str
    status: Literal["approved", "rejected", "already_decided"]
    result: dict[str, Any] = Field(default_factory=dict)
