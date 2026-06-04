# -*- coding: utf-8 -*-
"""Configuration for ClawMgt edge-node integration."""

from __future__ import annotations

import socket
from typing import Any

from pydantic import BaseModel, Field, field_validator

from qwenpaw.__version__ import __version__


class ClawMgtSettings(BaseModel):
    """Runtime settings for one QwenPaw node registered in ClawMgt."""

    enabled: bool = False
    base_url: str = ""
    channel_id: int | None = None
    node_id: int | None = None
    node_key: str = ""
    hostname: str = ""
    ip_address: str = ""
    auto_register: bool = True
    heartbeat_interval_sec: int = Field(default=30, ge=5, le=3600)
    report_interval_sec: int = Field(default=300, ge=30, le=86400)
    task_poll_interval_sec: int = Field(default=5, ge=1, le=3600)
    pull_limit: int = Field(default=10, ge=1, le=100)
    request_timeout_sec: float = Field(default=15.0, gt=0, le=120)

    @field_validator("base_url")
    @classmethod
    def _trim_base_url(cls, value: str) -> str:
        return value.strip().rstrip("/")

    @field_validator("node_key", "hostname", "ip_address")
    @classmethod
    def _trim_text(cls, value: str) -> str:
        return value.strip()

    def resolved_node_key(self) -> str:
        if self.node_key:
            return self.node_key
        return socket.gethostname()

    def resolved_hostname(self) -> str:
        if self.hostname:
            return self.hostname
        return socket.gethostname()

    def registration_payload(self) -> dict[str, Any]:
        return {
            "nodeKey": self.resolved_node_key(),
            "hostname": self.resolved_hostname(),
            "ipAddress": self.ip_address or None,
            "clawVersion": __version__,
            "metadata": "",
        }
