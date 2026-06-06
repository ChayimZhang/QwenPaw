# -*- coding: utf-8 -*-
"""ClawMgt edge-node task management integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .client import ClawMgtClient
    from .config import ClawMgtSettings
    from .engine import TaskEngine
    from .reporter import DataReporter, ReportScheduler, SkillMetadataReporter
    from .service import ClawMgtEdgeService

__all__ = [
    "ClawMgtClient",
    "ClawMgtEdgeService",
    "ClawMgtSettings",
    "DataReporter",
    "ReportScheduler",
    "SkillMetadataReporter",
    "TaskEngine",
]


def __getattr__(name: str) -> Any:
    if name == "ClawMgtClient":
        from .client import ClawMgtClient

        return ClawMgtClient
    if name == "ClawMgtEdgeService":
        from .service import ClawMgtEdgeService

        return ClawMgtEdgeService
    if name == "ClawMgtSettings":
        from .config import ClawMgtSettings

        return ClawMgtSettings
    if name == "DataReporter":
        from .reporter import DataReporter

        return DataReporter
    if name == "ReportScheduler":
        from .reporter import ReportScheduler

        return ReportScheduler
    if name == "SkillMetadataReporter":
        from .reporter import SkillMetadataReporter

        return SkillMetadataReporter
    if name == "TaskEngine":
        from .engine import TaskEngine

        return TaskEngine
    raise AttributeError(name)
