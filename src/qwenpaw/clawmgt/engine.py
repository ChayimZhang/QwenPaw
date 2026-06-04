# -*- coding: utf-8 -*-
"""ClawMgt task polling and execution engine."""

from __future__ import annotations

import json
import logging

from .client import ClawMgtClient
from .handlers import TaskHandler
from .models import (
    ClawTaskItem,
    TaskExecutionContext,
    TaskExecutionResult,
    TaskExecutionStatus,
)

logger = logging.getLogger(__name__)


class TaskEngine:
    """Poll ClawMgt and dispatch task items to registered handlers."""

    def __init__(
        self,
        client: ClawMgtClient,
        handlers: list[TaskHandler],
        context: TaskExecutionContext | None = None,
        pull_limit: int = 10,
    ) -> None:
        self.client = client
        self.handlers = {handler.task_type: handler for handler in handlers}
        self.context = context or TaskExecutionContext()
        self.pull_limit = pull_limit

    async def run_once(self) -> int:
        items = await self.client.pull_tasks(limit=self.pull_limit)
        for item in items:
            await self.execute_item(item)
        return len(items)

    async def execute_item(self, item: ClawTaskItem) -> TaskExecutionResult:
        handler = self.handlers.get(item.normalized_type)
        if handler is None:
            message = f"No handler registered for task type {item.type}"
            await self.client.finish_task_item(
                item.id,
                TaskExecutionStatus.FAILED.value,
                error_message=message,
            )
            return TaskExecutionResult.failed(message)

        await self.client.record_event(
            item.id,
            "started",
            "Task item execution started",
            TaskExecutionStatus.RUNNING.value,
        )
        try:
            result = await handler.execute(item, self.context)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("ClawMgt task item %s failed", item.id)
            result = TaskExecutionResult.failed(str(exc))
        await self.client.finish_task_item(
            item.id,
            result.status.value,
            result=_json_or_none(
                {
                    "result": result.result,
                    "details": result.details,
                },
            ),
            error_message=result.error_message,
        )
        return result


def _json_or_none(payload: dict) -> str | None:
    if not payload.get("result") and not payload.get("details"):
        return None
    return json.dumps(payload, ensure_ascii=False)
