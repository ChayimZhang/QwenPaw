from types import SimpleNamespace

import pytest

from qwenpaw.extensions import (
    ExtensionSpec,
    ExtensionRegistry,
    RunnerQueryContext,
    RunnerPatch,
    use_extension_registry,
    qwenpaw_extension,
)
from qwenpaw.extensions.adapters import ExtensionAdapters


def test_runner_query_stream_hooks_register_from_adapters_and_decorators():
    registry = ExtensionRegistry()
    adapters = ExtensionAdapters(registry)

    def adapter_start(context):
        context.state["adapter"] = True

    def adapter_message(context, msg, last):
        context.state["adapter_message"] = (msg, last)

    def adapter_finish(context, error):
        context.state["adapter_error"] = error

    adapters.before_query_stream_hook(adapter_start)
    adapters.query_stream_message_hook(adapter_message)
    adapters.after_query_stream_hook(adapter_finish)

    extension = qwenpaw_extension("runner_lifecycle")

    @extension.before_query_stream_hook
    def decorator_start(context):
        context.state["decorator"] = True

    @extension.query_stream_message_hook
    def decorator_message(context, msg, last):
        context.state["decorator_message"] = (msg, last)

    @extension.after_query_stream_hook
    def decorator_finish(context, error):
        context.state["decorator_error"] = error

    extension(registry)

    spec_start = lambda context: None
    spec_message = lambda context, msg, last: None
    spec_finish = lambda context, error: None
    registry.apply_spec(
        ExtensionSpec(
            name="spec_lifecycle",
            runner_patch=RunnerPatch(
                before_query_stream_hooks=(spec_start,),
                query_stream_message_hooks=(spec_message,),
                after_query_stream_hooks=(spec_finish,),
            ),
        )
    )

    assert registry.runner.before_query_stream_hooks == [
        adapter_start,
        decorator_start,
        spec_start,
    ]
    assert registry.runner.query_stream_message_hooks == [
        adapter_message,
        decorator_message,
        spec_message,
    ]
    assert registry.runner.after_query_stream_hooks == [
        adapter_finish,
        decorator_finish,
        spec_finish,
    ]


def test_runner_query_handler_hooks_register_from_adapters_and_decorators():
    registry = ExtensionRegistry()
    adapters = ExtensionAdapters(registry)

    def adapter_handler(context):
        return None

    adapters.query_handler_hook(adapter_handler)

    extension = qwenpaw_extension("runner_handler")

    @extension.query_handler_hook
    def decorator_handler(context):
        return None

    extension(registry)

    spec_handler = lambda context: None
    registry.apply_spec(
        ExtensionSpec(
            name="spec_handler",
            runner_patch=RunnerPatch(query_handler_hooks=(spec_handler,)),
        )
    )

    assert registry.runner.query_handler_hooks == [
        adapter_handler,
        decorator_handler,
        spec_handler,
    ]


@pytest.mark.asyncio
async def test_runner_query_handler_hook_can_delegate_entire_query_handler():
    registry = ExtensionRegistry()
    request = SimpleNamespace(session_id="s1", user_id="u1", channel="console")
    runner = object()
    workspace = object()
    seen = []

    async def handler(context: RunnerQueryContext):
        seen.append(
            (
                context.request.session_id,
                context.runner,
                context.workspace,
                context.msgs,
                context.kwargs["extra"],
            )
        )
        yield "business-msg", False
        yield "business-last", True

    registry.runner.add_query_handler_hook(handler)

    result = await registry.runner.get_query_handler_result(
        request=request,
        runner=runner,
        workspace=workspace,
        msgs=["hello"],
        kwargs={"extra": "value"},
    )
    items = [
        item
        async for item in registry.runner.iter_query_handler_result(result)
    ]

    assert items == [("business-msg", False), ("business-last", True)]
    assert seen == [("s1", runner, workspace, ["hello"], "value")]


@pytest.mark.asyncio
async def test_runner_query_stream_hooks_share_state_and_observe_messages():
    registry = ExtensionRegistry()
    events = []
    request = object()
    runner = object()
    agent = object()
    workspace = object()

    async def start(context: RunnerQueryContext):
        context.state["tracker"] = "tracker-1"
        events.append(("start", context.request, context.agent))

    async def message(context: RunnerQueryContext, msg, last):
        events.append(("message", context.state["tracker"], msg, last))

    async def finish(context: RunnerQueryContext, error):
        events.append(("finish", context.workspace, error))

    registry.runner.add_before_query_stream_hook(start)
    registry.runner.add_query_stream_message_hook(message)
    registry.runner.add_after_query_stream_hook(finish)

    async with registry.runner.query_stream_lifecycle(
        request=request,
        runner=runner,
        agent=agent,
        workspace=workspace,
        msgs=["hello"],
        kwargs={"stream": True},
    ) as lifecycle:
        await lifecycle.observe_message("msg-1", False)
        await lifecycle.observe_message("msg-2", True)

    assert events == [
        ("start", request, agent),
        ("message", "tracker-1", "msg-1", False),
        ("message", "tracker-1", "msg-2", True),
        ("finish", workspace, None),
    ]


@pytest.mark.asyncio
async def test_runner_query_stream_finish_receives_query_error():
    registry = ExtensionRegistry()
    events = []

    def start(context):
        events.append("start")

    def finish(context, error):
        events.append(("finish", type(error).__name__))

    registry.runner.add_before_query_stream_hook(start)
    registry.runner.add_after_query_stream_hook(finish)

    with pytest.raises(RuntimeError, match="query failed"):
        async with registry.runner.query_stream_lifecycle(
            request=None,
            runner=None,
            agent=None,
            workspace=None,
        ):
            raise RuntimeError("query failed")

    assert events == ["start", ("finish", "RuntimeError")]


@pytest.mark.asyncio
async def test_runner_query_stream_message_failure_does_not_interrupt_query():
    registry = ExtensionRegistry()
    events = []

    def message(context, msg, last):
        events.append(("message", msg, last))
        raise RuntimeError("audit sink unavailable")

    registry.runner.add_query_stream_message_hook(message)

    async with registry.runner.query_stream_lifecycle(
        request=None,
        runner=None,
        agent=None,
        workspace=None,
    ) as lifecycle:
        await lifecycle.observe_message("ok", True)

    assert events == [("message", "ok", True)]


@pytest.mark.asyncio
async def test_agent_runner_query_handler_can_be_fully_delegated():
    from qwenpaw.app.runner.runner import AgentRunner

    registry = ExtensionRegistry()
    events = []
    request = SimpleNamespace(session_id="s1", user_id="u1", channel="console")

    async def handler(context: RunnerQueryContext):
        events.append(("handler", context.runner.agent_id, context.msgs))
        yield "custom", False
        yield "done", True

    def message(context, msg, last):
        events.append(("message", msg, last))

    registry.runner.add_query_handler_hook(handler)
    registry.runner.add_query_stream_message_hook(message)
    runner = AgentRunner(agent_id="business-agent")

    with use_extension_registry(registry):
        result = [
            item
            async for item in runner.query_handler(
                ["hello"],
                request=request,
                extra="value",
            )
        ]

    assert result == [("custom", False), ("done", True)]
    assert events == [
        ("handler", "business-agent", ["hello"]),
    ]
