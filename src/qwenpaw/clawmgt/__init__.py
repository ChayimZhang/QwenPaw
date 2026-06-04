# -*- coding: utf-8 -*-
"""ClawMgt edge-node task management integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .client import ClawMgtClient
    from .config import ClawMgtSettings
    from .engine import TaskEngine
    from .service import ClawMgtEdgeService

__all__ = [
    "ClawMgtClient",
    "ClawMgtEdgeService",
    "ClawMgtSettings",
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
    if name == "TaskEngine":
        from .engine import TaskEngine

        return TaskEngine
    raise AttributeError(name)
