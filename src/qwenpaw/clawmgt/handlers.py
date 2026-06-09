# -*- coding: utf-8 -*-
"""Task handlers for ClawMgt task execution."""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from typing import Any

from qwenpaw.agents.skill_system import SkillPoolService
from qwenpaw.agents.skill_system.hub import import_pool_skill_from_hub
from .configuration import (
    apply_qwenpaw_env_update,
    delete_pool_skill_config,
    delete_workspace_skill_config,
    upsert_pool_skill_config,
    upsert_workspace_skill_config,
)

from .models import (
    ClawTaskItem,
    TaskExecutionContext,
    TaskExecutionResult,
    TaskExecutionStatus,
)


class TaskHandler(ABC):
    """Base class for extensible ClawMgt task handlers."""

    task_type: str

    @abstractmethod
    async def execute(
        self,
        item: ClawTaskItem,
        context: TaskExecutionContext,
    ) -> TaskExecutionResult:
        """Execute one task item."""

    def payload(self, item: ClawTaskItem) -> dict[str, Any]:
        try:
            data = json.loads(item.dispatch_payload or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError("Task dispatch payload is not valid JSON") from exc
        if not isinstance(data, dict):
            raise ValueError("Task dispatch payload must be an object")
        return data


class SkillInstallHandler(TaskHandler):
    task_type = "SKILL_INSTALL"

    async def execute(
        self,
        item: ClawTaskItem,
        context: TaskExecutionContext,
    ) -> TaskExecutionResult:
        _ = context
        payload = self.payload(item)
        details: list[dict[str, Any]] = []
        for spec in payload.get("skills") or []:
            skill_name = str(spec.get("skillName") or "").strip()
            version = str(spec.get("version") or "").strip()
            download_url = str(spec.get("downloadUrl") or "").strip()
            parameters = dict(spec.get("parameters") or {})
            try:
                result = await import_pool_skill_from_hub(
                    bundle_url=download_url,
                    version=version,
                    target_name=skill_name,
                )
                if parameters:
                    upsert_pool_skill_config(result.name, parameters)
                details.append(
                    {
                        "skillName": skill_name,
                        "version": version,
                        "status": "SUCCEEDED",
                        "parameters": parameters,
                    },
                )
            except Exception as exc:  # pylint: disable=broad-except
                details.append(
                    {
                        "skillName": skill_name,
                        "version": version,
                        "status": "FAILED",
                        "error": str(exc),
                        "parameters": parameters,
                    },
                )
                if payload.get("force") is not True:
                    break
        return _details_result(details)


class SkillUpgradeHandler(TaskHandler):
    task_type = "SKILL_UPGRADE"

    def __init__(self, install_handler: SkillInstallHandler | None = None):
        self.install_handler = install_handler or SkillInstallHandler()

    async def execute(
        self,
        item: ClawTaskItem,
        context: TaskExecutionContext,
    ) -> TaskExecutionResult:
        return await self.install_handler.execute(item, context)


class SkillRemoveHandler(TaskHandler):
    task_type = "SKILL_REMOVE"

    def __init__(self, pool_service: Any | None = None):
        self.pool_service = pool_service or SkillPoolService()

    async def execute(
        self,
        item: ClawTaskItem,
        context: TaskExecutionContext,
    ) -> TaskExecutionResult:
        _ = context
        payload = self.payload(item)
        details: list[dict[str, Any]] = []
        for skill_name in payload.get("skillNames") or []:
            try:
                deleted = await asyncio.to_thread(
                    self.pool_service.delete_skill,
                    skill_name,
                )
                details.append(
                    {
                        "skillName": skill_name,
                        "status": "SUCCEEDED" if deleted else "FAILED",
                    },
                )
            except Exception as exc:  # pylint: disable=broad-except
                details.append(
                    {
                        "skillName": skill_name,
                        "status": "FAILED",
                        "error": str(exc),
                    },
                )
        return _details_result(details)


class ParamUpdateHandler(TaskHandler):
    task_type = "PARAM_UPDATE"

    def __init__(self, pool_service: Any | None = None):
        self.pool_service = pool_service or SkillPoolService()

    async def execute(
        self,
        item: ClawTaskItem,
        context: TaskExecutionContext,
    ) -> TaskExecutionResult:
        payload = self.payload(item)
        skill_name = str(payload.get("skillName") or "").strip()
        parameters = dict(payload.get("parameters") or {})
        delete = bool(payload.get("delete") or payload.get("deleted"))
        if context.workspace_dir and delete:
            result = delete_workspace_skill_config(context.workspace_dir, skill_name)
        elif context.workspace_dir:
            result = upsert_workspace_skill_config(
                context.workspace_dir,
                skill_name,
                parameters,
            )
        elif delete:
            result = delete_pool_skill_config(skill_name)
        else:
            result = upsert_pool_skill_config(skill_name, parameters)
        return TaskExecutionResult.succeeded(
            result={
                "skillName": skill_name,
                "parameters": parameters,
                "deleted": delete,
            },
            details=[
                {
                    "skillName": skill_name,
                    "status": "SUCCEEDED",
                    "parameters": result["config"],
                    "deleted": delete,
                },
            ],
        )


class EnvUpdateHandler(TaskHandler):
    task_type = "ENV_UPDATE"

    async def execute(
        self,
        item: ClawTaskItem,
        context: TaskExecutionContext,
    ) -> TaskExecutionResult:
        _ = context
        payload = self.payload(item)
        variables = {
            str(key): str(value)
            for key, value in dict(payload.get("variables") or {}).items()
        }
        delete_keys = [str(key) for key in payload.get("deleteKeys") or []]
        envs = apply_qwenpaw_env_update(variables, delete_keys)
        details = [
            {
                "key": key,
                "operation": "UPSERT",
                "status": "SUCCEEDED",
            }
            for key in sorted(variables)
        ]
        details.extend(
            {
                "key": key,
                "operation": "DELETE",
                "status": "SUCCEEDED",
            }
            for key in sorted(delete_keys)
        )
        return TaskExecutionResult.succeeded(
            result={
                "updatedKeys": sorted(variables),
                "deletedKeys": sorted(delete_keys),
                "envCount": len(envs),
            },
            details=details,
        )


def _details_result(details: list[dict[str, Any]]) -> TaskExecutionResult:
    failed = [item for item in details if item.get("status") != "SUCCEEDED"]
    if not details:
        return TaskExecutionResult.failed("Task payload did not contain items")
    if not failed:
        return TaskExecutionResult.succeeded(details=details)
    if len(failed) == len(details):
        return TaskExecutionResult(
            status=TaskExecutionStatus.FAILED,
            details=details,
            error_message="All task details failed",
        )
    return TaskExecutionResult(
        status=TaskExecutionStatus.PARTIAL_SUCCEEDED,
        details=details,
        error_message="Some task details failed",
    )
