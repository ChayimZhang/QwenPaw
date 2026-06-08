# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio

import pytest

from qwenpaw.clawmgt.config import ClawMgtSettings
from qwenpaw.clawmgt.managers import JobExecutionManager, ReporterManager


class _Reporter:
    def __init__(self, report_type: str) -> None:
        self.report_type = report_type
        self.calls = 0

    async def report_once(self):
        self.calls += 1


class _Engine:
    def __init__(self) -> None:
        self.calls = 0

    async def run_once(self):
        self.calls += 1


class _Client:
    def __init__(self) -> None:
        self.registers = 0
        self.heartbeats = 0
        self.closed = 0

    async def register_node(self):
        self.registers += 1
        return 42

    async def heartbeat(self):
        self.heartbeats += 1

    async def close(self):
        self.closed += 1


@pytest.mark.asyncio
async def test_reporter_manager_reports_registered_reporters_and_resolves_intervals():
    skill = _Reporter("skill_metadata")
    runtime = _Reporter("runtime_metadata")
    settings = ClawMgtSettings(
        report_interval_sec=300,
        report_intervals_sec={"runtime_metadata": 60},
    )
    manager = ReporterManager(settings=settings, reporters=[skill, runtime])

    await manager.report_all_once()

    assert skill.calls == 1
    assert runtime.calls == 1
    assert manager.interval_for(skill) == 300
    assert manager.interval_for(runtime) == 60


@pytest.mark.asyncio
async def test_job_execution_manager_starts_registration_heartbeat_and_jobs():
    engine = _Engine()
    client = _Client()
    manager = JobExecutionManager(
        settings=ClawMgtSettings(
            enabled=True,
            task_poll_interval_sec=1,
            heartbeat_interval_sec=5,
        ),
        client=client,
        engine=engine,
    )

    await manager.start()
    await manager.stop()

    assert manager.settings.node_id == 42
    assert client.registers == 1
    assert client.heartbeats == 1
    assert engine.calls == 1
    assert client.closed == 1


@pytest.mark.asyncio
async def test_reporter_manager_is_independent_from_job_execution_manager():
    reporter = _Reporter("skill_metadata")
    client = _Client()
    manager = ReporterManager(
        settings=ClawMgtSettings(enabled=True, report_interval_sec=30),
        client=client,
        reporters=[reporter],
    )

    await manager.start()
    await manager.stop()

    assert manager.settings.node_id == 42
    assert reporter.calls == 1
    assert client.closed == 1


@pytest.mark.asyncio
async def test_managers_start_periodic_tasks():
    reporter = _Reporter("skill_metadata")
    reporter_manager = ReporterManager(
        settings=ClawMgtSettings(report_interval_sec=30),
        reporters=[reporter],
    )
    job_manager = JobExecutionManager(
        settings=ClawMgtSettings(task_poll_interval_sec=1),
        client=_Client(),
        engine=_Engine(),
    )
    stop_event = asyncio.Event()

    tasks = [
        *reporter_manager.start_periodic(stop_event),
        *job_manager.start_periodic(stop_event),
    ]
    stop_event.set()
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)

    assert len(tasks) == 2
