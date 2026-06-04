# -*- coding: utf-8 -*-
"""Typed ClawMgt transport and execution models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskExecutionStatus(str, Enum):
    """Statuses accepted by ClawMgt task item finish/event APIs."""

    RUNNING = "RUNNING"
    PARTIAL_SUCCEEDED = "PARTIAL_SUCCEEDED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ClawTaskItem(BaseModel):
    """One task item pulled from ClawMgt."""

    id: int
    task_id: int | None = Field(default=None, alias="taskId")
    channel_id: int | None = Field(default=None, alias="channelId")
    node_id: int | None = Field(default=None, alias="nodeId")
    type: str
    status: str = ""
    dispatch_payload: str = Field(default="{}", alias="dispatchPayload")

    model_config = {"populate_by_name": True}

    @property
    def normalized_type(self) -> str:
        return self.type.strip().upper()


class TaskExecutionContext(BaseModel):
    """Context passed to task handlers."""

    workspace_dir: str | None = None
    agent_id: str | None = None


class TaskExecutionResult(BaseModel):
    """Task handler result converted into ClawMgt finish payloads."""

    status: TaskExecutionStatus
    result: dict[str, Any] = Field(default_factory=dict)
    details: list[dict[str, Any]] = Field(default_factory=list)
    error_message: str | None = None

    @classmethod
    def succeeded(
        cls,
        *,
        result: dict[str, Any] | None = None,
        details: list[dict[str, Any]] | None = None,
    ) -> "TaskExecutionResult":
        return cls(
            status=TaskExecutionStatus.SUCCEEDED,
            result=result or {},
            details=details or [],
        )

    @classmethod
    def failed(cls, message: str) -> "TaskExecutionResult":
        return cls(
            status=TaskExecutionStatus.FAILED,
            error_message=message,
        )
