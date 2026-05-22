"""FastAPI extension hooks and console static resolution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from fastapi import FastAPI


@dataclass
class RouterRegistration:
    router: Any
    prefix: str = ""
    tags: list[str] | None = None


@dataclass
class AppExtensionRegistry:
    routers: list[RouterRegistration] = field(default_factory=list)
    startup_hooks: list[Callable[..., Any]] = field(default_factory=list)
    shutdown_hooks: list[Callable[..., Any]] = field(default_factory=list)
    middleware_hooks: list[Callable[[FastAPI], Any]] = field(default_factory=list)
    before_include_routers: list[Callable[[FastAPI], Any]] = field(default_factory=list)
    after_include_routers: list[Callable[[FastAPI], Any]] = field(default_factory=list)

    def add_router(
        self,
        router: Any,
        prefix: str = "",
        tags: list[str] | None = None,
    ) -> None:
        self.routers.append(RouterRegistration(router=router, prefix=prefix, tags=tags))

    def add_startup_hook(self, hook: Callable[..., Any]) -> None:
        self.startup_hooks.append(hook)

    def add_shutdown_hook(self, hook: Callable[..., Any]) -> None:
        self.shutdown_hooks.append(hook)

    def add_middleware_hook(self, hook: Callable[[FastAPI], Any]) -> None:
        self.middleware_hooks.append(hook)

    def add_before_include_routers_hook(self, hook: Callable[[FastAPI], Any]) -> None:
        self.before_include_routers.append(hook)

    def add_after_include_routers_hook(self, hook: Callable[[FastAPI], Any]) -> None:
        self.after_include_routers.append(hook)

    def apply_middleware(self, app: FastAPI) -> None:
        for hook in self.middleware_hooks:
            hook(app)

    def apply_routers(self, app: FastAPI) -> None:
        for item in self.routers:
            app.include_router(item.router, prefix=item.prefix, tags=item.tags)

    def run_startup_hooks(self) -> None:
        for hook in self.startup_hooks:
            hook()

    def run_shutdown_hooks(self) -> None:
        for hook in self.shutdown_hooks:
            hook()


def resolve_console_static_dir() -> Path | None:
    from qwenpaw.extensions.registry import get_extension_registry

    return get_extension_registry().product.console_static_dir
