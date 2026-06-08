# -*- coding: utf-8 -*-
"""Extensible data reporters for ClawMgt."""

from __future__ import annotations

from typing import Any

from qwenpaw.agents.skill_system import SkillPoolService

from .client import ClawMgtClient


class DataReporter:
    """Base class for periodic data reporters."""

    report_type: str

    async def report_once(self) -> Any:
        raise NotImplementedError


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
