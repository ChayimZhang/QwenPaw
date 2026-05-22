"""Logging resolution for extension-aware runtime setup."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from qwenpaw.extensions.env import EnvResolver
from qwenpaw.extensions.registry import get_extension_registry
from qwenpaw.extensions.specs import LoggingSpec


@dataclass(frozen=True)
class ResolvedLoggingSpec(LoggingSpec):
    """LoggingSpec with handler creation helpers."""

    def create_handlers(self) -> list[logging.Handler]:
        if self.handler_factory is not None:
            return self.handler_factory(
                self.namespace,
                self.file_path,
                self.format,
                self.level,
            )

        handlers: list[logging.Handler] = [logging.StreamHandler()]
        if self.file_path is not None:
            Path(self.file_path).parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(self.file_path, encoding="utf-8"))

        formatter = logging.Formatter(self.format)
        level = _coerce_level(self.level)
        for handler in handlers:
            handler.setFormatter(formatter)
            handler.setLevel(level)
        return handlers


def _coerce_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    return logging.getLevelName(level.upper())


def resolve_logging_spec() -> ResolvedLoggingSpec:
    spec = get_extension_registry().logging
    return ResolvedLoggingSpec(
        namespace=spec.namespace,
        file_path=spec.file_path,
        format=spec.format,
        level=spec.level,
        handler_factory=spec.handler_factory,
    )


def resolve_log_level(default: str = "info") -> str:
    """Resolve runtime log level using product env prefixes with fallback."""
    value = EnvResolver(get_extension_registry().product).get("LOG_LEVEL")
    return value if value is not None and value.strip() else default
