from fastapi import APIRouter

from qwenpaw.app.channels.command_registry import CommandRegistry
from qwenpaw.app.runner.control_commands import (
    BaseControlCommandHandler,
    is_control_command,
    unregister_command,
)
from qwenpaw.extensions import BuiltinChannelSpec, ExtensionRegistry
from qwenpaw.extensions.adapters import ExtensionAdapters
from qwenpaw.plugins.api import PluginApi


class ExampleProvider:
    pass


class ExampleChannel:
    pass


def test_adapters_register_router_provider_channel_and_command():
    registry = ExtensionRegistry()
    adapters = ExtensionAdapters(registry)
    router = APIRouter()

    adapters.router(router, prefix="/api/product", tags=["product"])
    adapters.provider("example", ExampleProvider)
    adapters.builtin_channel(BuiltinChannelSpec(key="example", factory=ExampleChannel))
    adapters.cli_command("diagnose", "my_product.cli", "diagnose")

    assert registry.app.routers[0].prefix == "/api/product"
    assert registry.app.routers[0].tags == ["product"]
    assert registry.providers.added["example"] is ExampleProvider
    assert registry.channels.builtin_specs["example"].factory is ExampleChannel
    assert registry.cli.added["diagnose"] == (
        "my_product.cli",
        "diagnose",
        ".diagnose",
    )


def test_adapters_expose_feature_and_plugin_policy_helpers(tmp_path):
    registry = ExtensionRegistry()
    adapters = ExtensionAdapters(registry)

    adapters.disable_feature("builtin_qa_agent")
    adapters.disable_channel("wechat")
    adapters.disable_provider("openrouter")
    adapters.disable_plugin("qwenpaw-pet")
    adapters.plugin_search_path(tmp_path / "plugins")

    assert registry.features.is_feature_enabled("builtin_qa_agent") is False
    assert registry.features.is_channel_enabled("wechat") is False
    assert registry.features.is_provider_enabled("openrouter") is False
    assert registry.features.is_plugin_enabled("qwenpaw-pet") is False
    assert registry.plugins.extra_search_paths == (tmp_path / "plugins",)


def test_adapters_update_product_fields_without_resetting_logging(tmp_path):
    registry = ExtensionRegistry()
    registry.configure_logging(
        type(registry.logging)(namespace="custom", file_path=tmp_path / "app.log")
    )
    adapters = ExtensionAdapters(registry)

    adapters.product_version("2.0.0")

    assert registry.product.product_version == "2.0.0"
    assert registry.logging.namespace == "custom"
    assert registry.logging.file_path == tmp_path / "app.log"

    adapters.product(module_alias="custom_product")
    adapters.logging(level="WARNING")

    assert registry.product.module_alias == "custom_product"
    assert registry.logging.namespace == "custom"
    assert registry.logging.level == "WARNING"


def test_registry_and_plugin_api_expose_adapters():
    registry = ExtensionRegistry()
    api = PluginApi("example", {})

    assert isinstance(registry.adapters, ExtensionAdapters)
    assert isinstance(api.extensions, ExtensionAdapters)


class ExampleControlCommand(BaseControlCommandHandler):
    command_name = "/example"

    async def handle(self, context):
        return "ok"


def test_adapters_expose_skill_control_and_agent_template_helpers(tmp_path):
    registry = ExtensionRegistry()
    adapters = ExtensionAdapters(registry)
    priority_registry = CommandRegistry()

    try:
        adapters.agent_prompt_files("MY_PRODUCT.md", "AGENTS.md")
        skill_service = adapters.skill_service(tmp_path / "workspace")
        pool_service = adapters.skill_pool_service()
        adapters.control_command(
            ExampleControlCommand(),
            priority="high",
            priority_registry=priority_registry,
        )

        assert registry.product.agent_prompt_files == ("MY_PRODUCT.md", "AGENTS.md")
        assert skill_service.workspace_dir == tmp_path / "workspace"
        assert pool_service is not None
        assert is_control_command("/example now") is True
        assert priority_registry.get_priority_level("/example now") == 10
    finally:
        unregister_command("/example")
