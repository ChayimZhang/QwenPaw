# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from qwenpaw.clawmgt.client import ClawMgtClient
from qwenpaw.clawmgt.config import ClawMgtSettings
from qwenpaw.clawmgt.reporter import SkillMetadataReporter


class _FakeAsyncClient:
    def __init__(self):
        self.calls = []

    async def post(self, url, **kwargs):
        self.calls.append(("POST", url, kwargs))
        return _FakeResponse({"success": True, "data": {"id": 42}})

    async def get(self, url, **kwargs):
        self.calls.append(("GET", url, kwargs))
        return _FakeResponse({"success": True, "data": []})


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _PoolService:
    def list_all_skills(self):
        return [
            type(
                "Skill",
                (),
                {
                    "name": "browser",
                    "version_text": "1.2.3",
                    "source": "customized",
                },
            )(),
            type(
                "Skill",
                (),
                {
                    "name": "docx",
                    "version_text": "",
                    "source": "builtin",
                },
            )(),
        ]


@pytest.mark.asyncio
async def test_client_uses_channel_for_pull_and_node_for_report():
    http = _FakeAsyncClient()
    client = ClawMgtClient(
        settings=ClawMgtSettings(
            base_url="http://mgt.test/",
            channel_id=7,
            node_id=11,
        ),
        http_client=http,
    )

    await client.heartbeat()
    await client.report_skill_metadata(
        [{"skillName": "browser", "version": "1.2.3"}],
    )
    await client.pull_tasks(limit=5)

    assert http.calls[0][1] == "http://mgt.test/api/claw/nodes/11/heartbeat"
    assert http.calls[1][1] == "http://mgt.test/api/claw/nodes/11/reports"
    assert http.calls[1][2]["json"] == {
        "type": "skill_metadata",
        "payload": {
            "skills": [{"skillName": "browser", "version": "1.2.3"}],
        },
    }
    assert (
        http.calls[2][1]
        == "http://mgt.test/api/claw/channels/7/tasks/pull"
    )
    assert http.calls[2][2]["params"] == {"nodeId": 11, "limit": 5}


@pytest.mark.asyncio
async def test_reporter_collects_pool_skill_metadata():
    http = _FakeAsyncClient()
    client = ClawMgtClient(
        settings=ClawMgtSettings(
            base_url="http://mgt.test",
            channel_id=7,
            node_id=11,
        ),
        http_client=http,
    )
    reporter = SkillMetadataReporter(client=client, pool_service=_PoolService())

    payload = await reporter.report_once()

    assert payload == [
        {"skillName": "browser", "version": "1.2.3"},
        {"skillName": "docx", "version": "0.0.0"},
    ]
    assert http.calls[0][2]["json"]["type"] == "skill_metadata"
