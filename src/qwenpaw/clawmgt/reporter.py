# -*- coding: utf-8 -*-
"""Extensible data reporting for ClawMgt."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from qwenpaw.agents.skill_system import SkillPoolService

from .client import ClawMgtClient
from .config import ClawMgtSettings

logger = logging.getLogger(__name__)


class DataReporter:
    """Base class for periodic data reporters."""

    report_type: str

    async def report_once(self) -> Any:
        raise NotImplementedError


class ReportScheduler:
    """Runs registered reporters with per-report-type intervals."""

    def __init__(
        self,
        settings: ClawMgtSettings,
        reporters: list[DataReporter],
    ) -> None:
        self.settings = settings
        self.reporters = reporters

    async def report_all_once(self) -> None:
        for reporter in self.reporters:
            await reporter.report_once()

    def start(self, stop_event: asyncio.Event) -> list[asyncio.Task]:
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
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
                return
            except asyncio.TimeoutError:
                pass
            try:
                await reporter.report_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "ClawMgt %s report failed",
                    reporter.report_type,
                )


class SkillMetadataReporter(DataReporter):
    """Collect local skill metadata and submit it via the report API."""

    report_type = "skill_metadata"

    def __init__(
        self,
        client: ClawMgtClient,
        pool_service: Any | None = None,
    ) -> None:
        self.client = client
        self.pool_service = pool_service or SkillPoolService()

    async def report_once(self) -> list[dict[str, Any]]:
        skills = self.collect()
        await self.client.report_data(
            self.report_type,
            {
                "skills": skills,
            },
        )
        return skills

    def collect(self) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for skill in self.pool_service.list_all_skills():
            payload.append(
                {
                    "skillName": skill.name,
                    "version": skill.version_text or "0.0.0",
                },
            )
        return payload
