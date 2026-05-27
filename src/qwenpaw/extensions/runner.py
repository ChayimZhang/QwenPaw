"""Agent runner extension hooks."""

from __future__ import annotations

import inspect
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RunnerQueryContext:
    """Read-only context for one AgentRunner.query_handler call."""

    request: Any
    runner: Any
    agent: Any
    workspace: Any
    msgs: Any = ()
    kwargs: MappingProxyType = field(default_factory=lambda: MappingProxyType({}))
    state: dict[str, Any] = field(default_factory=dict)


class _NoopQueryStreamLifecycle:
    async def observe_message(self, msg: Any, last: bool) -> None:
        _ = msg, last


class _QueryStreamLifecycle:
    def __init__(
        self,
        hooks: list[Callable[[RunnerQueryContext, Any, bool], Any]],
        context: RunnerQueryContext,
    ) -> None:
        self._hooks = hooks
        self.context = context

    async def observe_message(self, msg: Any, last: bool) -> None:
        for hook in self._hooks:
            try:
                await _invoke_hook(hook, self.context, msg, last)
            except Exception:
                logger.exception("Extension query message hook failed")


class RunnerExtensionRegistry:
    """Hook registry for AgentRunner extension points."""

    def __init__(self) -> None:
        self.query_handler_hooks: list[Callable[[RunnerQueryContext], Any]] = []
        self.before_query_stream_hooks: list[Callable[[RunnerQueryContext], Any]] = []
        self.query_stream_message_hooks: list[
            Callable[[RunnerQueryContext, Any, bool], Any]
        ] = []
        self.after_query_stream_hooks: list[
            Callable[[RunnerQueryContext, BaseException | None], Any]
        ] = []

    def add_query_handler_hook(
        self,
        hook: Callable[[RunnerQueryContext], Any],
    ) -> None:
        self.query_handler_hooks.append(hook)

    def add_before_query_stream_hook(
        self,
        hook: Callable[[RunnerQueryContext], Any],
    ) -> None:
        self.before_query_stream_hooks.append(hook)

    def add_query_stream_message_hook(
        self,
        hook: Callable[[RunnerQueryContext, Any, bool], Any],
    ) -> None:
        self.query_stream_message_hooks.append(hook)

    def add_after_query_stream_hook(
        self,
        hook: Callable[[RunnerQueryContext, BaseException | None], Any],
    ) -> None:
        self.after_query_stream_hooks.append(hook)

    async def get_query_handler_result(
        self,
        *,
        request: Any,
        runner: Any,
        workspace: Any,
        msgs: Any = None,
        kwargs: dict[str, Any] | None = None,
    ) -> Any | None:
        """Return the first business query handler result, or None."""
        if not self.query_handler_hooks:
            return None

        context = RunnerQueryContext(
            request=request,
            runner=runner,
            agent=None,
            workspace=workspace,
            msgs=() if msgs is None else msgs,
            kwargs=MappingProxyType(dict(kwargs or {})),
        )
        for hook in self.query_handler_hooks:
            try:
                result = hook(context)
                if inspect.isawaitable(result):
                    result = await result
            except Exception:
                logger.exception("Extension query handler hook failed")
                continue
            if result is not None:
                return result
        return None

    async def iter_query_handler_result(self, result: Any):
        """Yield ``(msg, last)`` pairs from a business query handler result."""
        if hasattr(result, "__aiter__"):
            async for item in result:
                yield _normalize_query_item(item)
            return

        if _looks_like_query_item(result):
            yield result
            return

        for item in result:
            yield _normalize_query_item(item)

    @asynccontextmanager
    async def query_stream_lifecycle(
        self,
        *,
        request: Any,
        runner: Any,
        agent: Any,
        workspace: Any,
        msgs: Any = None,
        kwargs: dict[str, Any] | None = None,
    ):
        """Run hooks around native final query stream execution."""
        context = RunnerQueryContext(
            request=request,
            runner=runner,
            agent=agent,
            workspace=workspace,
            msgs=() if msgs is None else msgs,
            kwargs=MappingProxyType(dict(kwargs or {})),
        )
        error: BaseException | None = None
        for hook in self.before_query_stream_hooks:
            try:
                result = await _invoke_hook(hook, context)
                _merge_start_result(context, result)
            except Exception:
                logger.exception("Extension before query stream hook failed")
        lifecycle = (
            _QueryStreamLifecycle(self.query_stream_message_hooks, context)
            if self.query_stream_message_hooks
            else _NoopQueryStreamLifecycle()
        )
        try:
            yield lifecycle
        except BaseException as exc:
            error = exc
            raise
        finally:
            for hook in self.after_query_stream_hooks:
                try:
                    await _invoke_hook(hook, context, error)
                except Exception:
                    logger.exception("Extension after query stream hook failed")


async def _invoke_hook(hook: Callable[..., Any], *args: Any) -> Any:
    result = hook(*args)
    if inspect.isawaitable(result):
        return await result
    return result


def _merge_start_result(context: RunnerQueryContext, result: Any) -> None:
    if result is None:
        return
    if isinstance(result, dict):
        context.state.update(result)
        return
    context.state["value"] = result


def _looks_like_query_item(item: Any) -> bool:
    return isinstance(item, tuple) and len(item) == 2 and isinstance(item[1], bool)


def _normalize_query_item(item: Any) -> tuple[Any, bool]:
    if _looks_like_query_item(item):
        return item
    if isinstance(item, list) and len(item) == 2 and isinstance(item[1], bool):
        return item[0], item[1]
    raise TypeError(
        "query_handler_hook must yield (msg, last) pairs where last is bool"
    )
