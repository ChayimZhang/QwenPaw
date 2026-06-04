# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from qwenpaw.clawmgt.engine import TaskEngine
from qwenpaw.clawmgt.handlers import (
    ParamUpdateHandler,
    SkillInstallHandler,
    SkillRemoveHandler,
    SkillUpgradeHandler,
)
from qwenpaw.clawmgt.models import (
    ClawTaskItem,
    TaskExecutionContext,
    TaskExecutionStatus,
)


class _FakeClient:
    def __init__(self, items=None):
        self.items = list(items or [])
        self.events = []
        self.finishes = []

    async def pull_tasks(self, limit=10):
        _ = limit
        items = self.items
        self.items = []
        return items

    async def record_event(self, task_item_id, event_type, content, status):
        self.events.append((task_item_id, event_type, content, status))

    async def finish_task_item(
        self,
        task_item_id,
        status,
        result=None,
        error_message=None,
    ):
        self.finishes.append((task_item_id, status, result, error_message))


class _FakePool:
    def __init__(self):
        self.deleted = []
        self.configs = {}

    def delete_skill(self, name):
        self.deleted.append(name)
        return name != "missing"


@pytest.mark.asyncio
async def test_engine_dispatches_task_items_to_registered_handler(monkeypatch):
    item = ClawTaskItem(
        id=101,
        type="PARAM_UPDATE",
        dispatch_payload='{"skillName":"browser","parameters":{"a":1}}',
    )
    client = _FakeClient([item])
    monkeypatch.setattr(
        "qwenpaw.clawmgt.handlers._set_pool_skill_config",
        lambda skill_name, parameters: None,
    )
    handler = ParamUpdateHandler(pool_service=_FakePool())
    engine = TaskEngine(client=client, handlers=[handler])

    await engine.run_once()

    assert client.events == [
        (101, "started", "Task item execution started", "RUNNING"),
    ]
    assert client.finishes[0][1] == "SUCCEEDED"
    assert '"browser"' in client.finishes[0][2]


@pytest.mark.asyncio
async def test_engine_marks_unknown_task_type_failed():
    item = ClawTaskItem(id=102, type="MODEL_UPDATE", dispatch_payload="{}")
    client = _FakeClient([item])
    engine = TaskEngine(client=client, handlers=[])

    await engine.run_once()

    assert client.finishes == [
        (102, "FAILED", None, "No handler registered for task type MODEL_UPDATE"),
    ]


@pytest.mark.asyncio
async def test_skill_install_handler_imports_each_skill(monkeypatch):
    imported = []

    async def fake_import_pool_skill_from_hub(**kwargs):
        imported.append(kwargs)
        return type("Result", (), {"name": kwargs["target_name"]})()

    monkeypatch.setattr(
        "qwenpaw.clawmgt.handlers.import_pool_skill_from_hub",
        fake_import_pool_skill_from_hub,
    )
    monkeypatch.setattr(
        "qwenpaw.clawmgt.handlers._set_pool_skill_config",
        lambda skill_name, parameters: None,
    )
    handler = SkillInstallHandler()
    item = ClawTaskItem(
        id=201,
        type="SKILL_INSTALL",
        dispatch_payload=(
            '{"skills":[{"skillName":"browser","version":"1.2.0",'
            '"downloadUrl":"https://example.test/browser.zip",'
            '"parameters":{"mode":"fast"}}],"force":true}'
        ),
    )

    result = await handler.execute(item, TaskExecutionContext())

    assert result.status is TaskExecutionStatus.SUCCEEDED
    assert imported == [
        {
            "bundle_url": "https://example.test/browser.zip",
            "version": "1.2.0",
            "target_name": "browser",
        },
    ]
    assert result.details[0]["parameters"] == {"mode": "fast"}


@pytest.mark.asyncio
async def test_skill_upgrade_uses_same_install_flow_with_force():
    handler = SkillUpgradeHandler(
        install_handler=SkillInstallHandler(),
    )
    assert handler.task_type == "SKILL_UPGRADE"


@pytest.mark.asyncio
async def test_skill_remove_deletes_pool_skills():
    pool = _FakePool()
    handler = SkillRemoveHandler(pool_service=pool)
    item = ClawTaskItem(
        id=301,
        type="SKILL_REMOVE",
        dispatch_payload='{"skillNames":["browser","missing"]}',
    )

    result = await handler.execute(item, TaskExecutionContext())

    assert result.status is TaskExecutionStatus.PARTIAL_SUCCEEDED
    assert pool.deleted == ["browser", "missing"]
    assert result.details[1]["status"] == "FAILED"
