# -*- coding: utf-8 -*-
"""Managers for ClawMgt task execution and periodic reporting."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Any

from .client import ClawMgtClient
from .config import ClawMgtSettings
from .engine import TaskEngine
from .handlers import (
    EnvUpdateHandler,
    ParamUpdateHandler,
    SkillInstallHandler,
    SkillRemoveHandler,
    SkillUpgradeHandler,
)
from .models import TaskExecutionContext
from .reporter import DataReporter
from .reporter import SkillMetadataReporter

logger = logging.getLogger(__name__)


async def _should_stop_after_wait(
    stop_event: asyncio.Event,
    timeout: int,
) -> bool:
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        return False
    return True


class ReporterManager:
    """Owns ClawMgt data reporters and their periodic lifecycle."""

    def __init__(
        self,
        settings: ClawMgtSettings,
        client: ClawMgtClient | Any | None = None,
        reporter: DataReporter | None = None,
        reporters: list[DataReporter] | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or ClawMgtClient(settings)
        registered_reporters = list(reporters or [])
        if reporter is not None:
            registered_reporters.append(reporter)
        if not registered_reporters:
            registered_reporters.append(SkillMetadataReporter(self.client))
        self.reporters = registered_reporters
        self._tasks: list[asyncio.Task] = []
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if not self.settings.enabled:
            return
        if self.settings.node_id is None and self.settings.auto_register:
            self.settings.node_id = await self.client.register_node()
        await self.report_all_once()
        self._tasks = self.start_periodic(self._stop_event)

    async def stop(self) -> None:
        self._stop_event.set()
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with suppress(asyncio.CancelledError):
                await task
        await self.client.close()

    async def report_all_once(self) -> None:
        for reporter in self.reporters:
            await reporter.report_once()

    def start_periodic(self, stop_event: asyncio.Event) -> list[asyncio.Task]:
        return [
            asyncio.create_task(self._run_reporter_loop(reporter, stop_event))
            for reporter in self.reporters
        ]

    def interval_for(self, reporter: DataReporter) -> int:
        return self.settings.report_interval_for(reporter.report_type)

    async def _run_reporter_loop(
        self,
        reporter: DataReporter,
        stop_event: asyncio.Event,
    ) -> None:
        interval = self.interval_for(reporter)
        while not stop_event.is_set():
            if await _should_stop_after_wait(stop_event, interval):
                return
            try:
                await reporter.report_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "ClawMgt %s report failed",
                    reporter.report_type,
                )


class JobExecutionManager:
    """Owns ClawMgt node registration, heartbeat, and job execution."""

    def __init__(
        self,
        settings: ClawMgtSettings,
        client: ClawMgtClient | Any | None = None,
        engine: TaskEngine | Any | None = None,
        context: TaskExecutionContext | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or ClawMgtClient(settings)
        handlers = [
            SkillInstallHandler(),
            SkillUpgradeHandler(),
            SkillRemoveHandler(),
            ParamUpdateHandler(),
            EnvUpdateHandler(),
        ]
        self.engine = engine or TaskEngine(
            client=self.client,
            handlers=handlers,
            context=context,
            pull_limit=settings.pull_limit,
        )
        self._tasks: list[asyncio.Task] = []
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if not self.settings.enabled:
            return
        if self.settings.node_id is None and self.settings.auto_register:
            self.settings.node_id = await self.client.register_node()
        await self.client.heartbeat()
        await self.run_once()
        self._tasks = [
            asyncio.create_task(self._heartbeat_loop()),
            *self.start_periodic(self._stop_event),
        ]

    async def stop(self) -> None:
        self._stop_event.set()
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with suppress(asyncio.CancelledError):
                await task
        await self.client.close()

    async def run_once(self) -> Any:
        return await self.engine.run_once()

    def start_periodic(self, stop_event: asyncio.Event) -> list[asyncio.Task]:
        return [
            asyncio.create_task(self._task_loop(stop_event)),
        ]

    async def _heartbeat_loop(self) -> None:
        while not self._stop_event.is_set():
            if await _should_stop_after_wait(
                self._stop_event,
                self.settings.heartbeat_interval_sec,
            ):
                return
            try:
                await self.client.heartbeat()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("ClawMgt heartbeat failed")

    async def _task_loop(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            if await _should_stop_after_wait(
                stop_event,
                self.settings.task_poll_interval_sec,
            ):
                return
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("ClawMgt task polling failed")
