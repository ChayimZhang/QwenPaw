# -*- coding: utf-8 -*-
"""ClawMgt edge-node task management integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .client import ClawMgtClient
    from .config import ClawMgtSettings
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
    raise AttributeError(name)
