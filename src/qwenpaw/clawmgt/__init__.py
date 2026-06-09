# -*- coding: utf-8 -*-
"""ClawMgt edge-node task management integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .client import ClawMgtClient
    from .config import ClawMgtSettings
    from .configuration import (
        apply_qwenpaw_env_update,
        delete_pool_skill_config,
        delete_qwenpaw_env_vars,
        delete_workspace_skill_config,
        get_pool_skill_config,
        get_qwenpaw_env_var,
        get_qwenpaw_env_vars,
        get_workspace_skill_config,
        upsert_pool_skill_config,
        upsert_qwenpaw_env_vars,
        upsert_workspace_skill_config,
    )
    from .engine import TaskEngine
    from .managers import JobExecutionManager, ReporterManager
    from .reporter import DataReporter, SkillMetadataReporter

__all__ = [
    "ClawMgtClient",
    "ClawMgtSettings",
    "DataReporter",
    "JobExecutionManager",
    "ReporterManager",
    "SkillMetadataReporter",
    "TaskEngine",
    "apply_qwenpaw_env_update",
    "delete_pool_skill_config",
    "delete_qwenpaw_env_vars",
    "delete_workspace_skill_config",
    "get_pool_skill_config",
    "get_qwenpaw_env_var",
    "get_qwenpaw_env_vars",
    "get_workspace_skill_config",
    "upsert_pool_skill_config",
    "upsert_qwenpaw_env_vars",
    "upsert_workspace_skill_config",
]


def __getattr__(name: str) -> Any:
    if name == "ClawMgtClient":
        from .client import ClawMgtClient

        return ClawMgtClient
    if name == "ClawMgtSettings":
        from .config import ClawMgtSettings

        return ClawMgtSettings
    if name == "DataReporter":
        from .reporter import DataReporter

        return DataReporter
    if name == "apply_qwenpaw_env_update":
        from .configuration import apply_qwenpaw_env_update

        return apply_qwenpaw_env_update
    if name == "delete_pool_skill_config":
        from .configuration import delete_pool_skill_config

        return delete_pool_skill_config
    if name == "delete_qwenpaw_env_vars":
        from .configuration import delete_qwenpaw_env_vars

        return delete_qwenpaw_env_vars
    if name == "delete_workspace_skill_config":
        from .configuration import delete_workspace_skill_config

        return delete_workspace_skill_config
    if name == "get_pool_skill_config":
        from .configuration import get_pool_skill_config

        return get_pool_skill_config
    if name == "get_qwenpaw_env_var":
        from .configuration import get_qwenpaw_env_var

        return get_qwenpaw_env_var
    if name == "get_qwenpaw_env_vars":
        from .configuration import get_qwenpaw_env_vars

        return get_qwenpaw_env_vars
    if name == "get_workspace_skill_config":
        from .configuration import get_workspace_skill_config

        return get_workspace_skill_config
    if name == "JobExecutionManager":
        from .managers import JobExecutionManager

        return JobExecutionManager
    if name == "ReporterManager":
        from .managers import ReporterManager

        return ReporterManager
    if name == "SkillMetadataReporter":
        from .reporter import SkillMetadataReporter

        return SkillMetadataReporter
    if name == "TaskEngine":
        from .engine import TaskEngine

        return TaskEngine
    if name == "upsert_pool_skill_config":
        from .configuration import upsert_pool_skill_config

        return upsert_pool_skill_config
    if name == "upsert_qwenpaw_env_vars":
        from .configuration import upsert_qwenpaw_env_vars

        return upsert_qwenpaw_env_vars
    if name == "upsert_workspace_skill_config":
        from .configuration import upsert_workspace_skill_config

        return upsert_workspace_skill_config
    raise AttributeError(name)
