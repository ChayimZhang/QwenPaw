# -*- coding: utf-8 -*-
"""HTTP client for the ClawMgt edge-node API."""

from __future__ import annotations

from typing import Any

import httpx

from .config import ClawMgtSettings
from .models import ClawTaskItem, TaskExecutionStatus


class ClawMgtClient:
    """Small typed wrapper around ClawMgt node endpoints."""

    def __init__(
        self,
        settings: ClawMgtSettings,
        http_client: httpx.AsyncClient | Any | None = None,
    ) -> None:
        self.settings = settings
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            timeout=settings.request_timeout_sec,
        )

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def register_node(self) -> int:
        self._require_channel()
        response = await self._client.post(
            self._url(
                f"/api/claw/channels/{self.settings.channel_id}"
                "/nodes/register",
            ),
            json=self.settings.registration_payload(),
        )
        return int(self._data(response)["id"])

    async def heartbeat(self) -> dict[str, Any]:
        self._require_node()
        response = await self._client.post(
            self._url(f"/api/claw/nodes/{self.settings.node_id}/heartbeat"),
        )
        return dict(self._data(response))

    async def report_skill_metadata(
        self,
        skills: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return await self.report_data(
            "skill_metadata",
            {
                "skills": skills,
            },
        )

    async def report_data(
        self,
        report_type: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._require_node()
        response = await self._client.post(
            self._url(f"/api/claw/nodes/{self.settings.node_id}/reports"),
            json={
                "type": report_type,
                "payload": payload,
            },
        )
        return dict(self._data(response))

    async def pull_tasks(self, limit: int = 10) -> list[ClawTaskItem]:
        self._require_channel()
        self._require_node()
        response = await self._client.get(
            self._url(
                f"/api/claw/channels/{self.settings.channel_id}/tasks/pull",
            ),
            params={
                "nodeId": self.settings.node_id,
                "limit": limit,
            },
        )
        return [
            ClawTaskItem.model_validate(item)
            for item in list(self._data(response) or [])
        ]

    async def record_event(
        self,
        task_item_id: int,
        event_type: str,
        content: str,
        status: str | TaskExecutionStatus,
    ) -> dict[str, Any]:
        status_value = (
            status.value if isinstance(status, TaskExecutionStatus) else status
        )
        response = await self._client.post(
            self._url(f"/api/claw/task-items/{task_item_id}/events"),
            json={
                "eventId": f"{task_item_id}-{event_type}",
                "eventType": event_type,
                "status": status_value,
                "content": content,
            },
        )
        return dict(self._data(response))

    async def finish_task_item(
        self,
        task_item_id: int,
        status: str | TaskExecutionStatus,
        result: str | None = None,
        error_message: str | None = None,
    ) -> dict[str, Any]:
        status_value = (
            status.value if isinstance(status, TaskExecutionStatus) else status
        )
        response = await self._client.post(
            self._url(f"/api/claw/task-items/{task_item_id}/finish"),
            json={
                "status": status_value,
                "result": result,
                "errorMessage": error_message,
            },
        )
        return dict(self._data(response))

    def _url(self, path: str) -> str:
        if not self.settings.base_url:
            raise ValueError("ClawMgt base_url is required")
        return f"{self.settings.base_url}{path}"

    def _require_channel(self) -> None:
        if self.settings.channel_id is None:
            raise ValueError("ClawMgt channel_id is required")

    def _require_node(self) -> None:
        if self.settings.node_id is None:
            raise ValueError("ClawMgt node_id is required")

    @staticmethod
    def _data(response: httpx.Response | Any) -> Any:
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and payload.get("success") is False:
            raise RuntimeError(
                str(payload.get("message") or payload.get("code")),
            )
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload
