# -*- coding: utf-8 -*-
"""Background service that connects QwenPaw to ClawMgt."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from .client import ClawMgtClient
from .config import ClawMgtSettings
from .engine import TaskEngine
from .handlers import (
    ParamUpdateHandler,
    SkillInstallHandler,
    SkillRemoveHandler,
    SkillUpgradeHandler,
)
from .models import TaskExecutionContext
from .reporter import DataReporter, ReportScheduler, SkillMetadataReporter

logger = logging.getLogger(__name__)


class ClawMgtEdgeService:
    """Owns heartbeat, metadata reporting, and task polling loops."""

    def __init__(
        self,
        settings: ClawMgtSettings,
        client: ClawMgtClient | None = None,
        engine: TaskEngine | None = None,
        reporter: DataReporter | None = None,
        reporters: list[DataReporter] | None = None,
        context: TaskExecutionContext | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or ClawMgtClient(settings)
        handlers = [
            SkillInstallHandler(),
            SkillUpgradeHandler(),
            SkillRemoveHandler(),
            ParamUpdateHandler(),
        ]
        self.engine = engine or TaskEngine(
            client=self.client,
            handlers=handlers,
            context=context,
            pull_limit=settings.pull_limit,
        )
        registered_reporters = list(reporters or [])
        if reporter is not None:
            registered_reporters.append(reporter)
        if not registered_reporters:
            registered_reporters.append(SkillMetadataReporter(self.client))
        self.reporters = registered_reporters
        self.report_scheduler = ReportScheduler(
            settings=settings,
            reporters=self.reporters,
        )
        self._tasks: list[asyncio.Task] = []
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if not self.settings.enabled:
            return
        if self.settings.node_id is None and self.settings.auto_register:
            self.settings.node_id = await self.client.register_node()
        await self.report_scheduler.report_all_once()
        self._tasks = [
            asyncio.create_task(self._heartbeat_loop()),
            *self.report_scheduler.start(self._stop_event),
            asyncio.create_task(self._task_loop()),
        ]

    async def stop(self) -> None:
        self._stop_event.set()
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with suppress(asyncio.CancelledError):
                await task
        await self.client.close()

    async def _heartbeat_loop(self) -> None:
        await self._run_interval(
            self.settings.heartbeat_interval_sec,
            self.client.heartbeat,
            "heartbeat",
        )

    async def _task_loop(self) -> None:
        await self._run_interval(
            self.settings.task_poll_interval_sec,
            self.engine.run_once,
            "task polling",
        )

    async def _run_interval(self, interval: int, callback, label: str) -> None:
        while not self._stop_event.is_set():
            try:
                await callback()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("ClawMgt %s failed", label)
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(),
                    timeout=interval,
                )
            except asyncio.TimeoutError:
                continue
