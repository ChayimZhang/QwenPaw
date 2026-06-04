# -*- coding: utf-8 -*-
"""Skill metadata reporting for ClawMgt."""

from __future__ import annotations

from typing import Any

from qwenpaw.agents.skill_system import SkillPoolService

from .client import ClawMgtClient


class SkillMetadataReporter:
    """Collect local skill metadata and submit it via the report API."""

    def __init__(
        self,
        client: ClawMgtClient,
        pool_service: Any | None = None,
    ) -> None:
        self.client = client
        self.pool_service = pool_service or SkillPoolService()

    async def report_once(self) -> list[dict[str, Any]]:
        skills = self.collect()
        await self.client.report_skill_metadata(skills)
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
