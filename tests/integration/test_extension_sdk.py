from qwenpaw.extensions import (
    BuiltinChannelSpec,
    ExtensionRegistry,
    FeaturePolicy,
    ProductSpec,
    qwenpaw_extension,
    use_extension_registry,
)
from qwenpaw.extensions.app import resolve_console_static_dir


class WorkChatChannel:
    pass


class DiscordChannel:
    pass


def test_extension_sdk_smoke_registers_remaining_runtime_surfaces(tmp_path):
    extension = qwenpaw_extension("my_product")
    console_dir = tmp_path / "console"
    channel_dir = tmp_path / "channels"

    @extension.product
    def product_spec():
        return ProductSpec(
            product_name="MyProduct",
            product_version="2.0.0",
            module_alias="my_product",
            cli_name="myproduct",
            skill_cli_name="myproduct-skills",
            working_dir=tmp_path / "work",
            secret_dir=tmp_path / "secret",
            console_static_dir=console_dir,
            agent_prompt_files=("MY_PRODUCT.md", "AGENTS.md"),
        )

    @extension.features
    def feature_policy():
        return FeaturePolicy(disabled_features={"builtin_qa_agent"})

    @extension.configure
    def configure(context):
        api = context.adapters
        api.builtin_channel(
            BuiltinChannelSpec(
                key="workchat",
                factory=WorkChatChannel,
                default_enabled=True,
            )
        )
        api.builtin_channel(BuiltinChannelSpec(key="discord", factory=DiscordChannel))
        api.disable_channel("discord")
        api.custom_channel_source(channel_dir)

    registry = ExtensionRegistry()
    extension(registry)

    with use_extension_registry(registry):
        assert registry.product.product_name == "MyProduct"
        assert registry.product.product_version == "2.0.0"
        assert registry.product.module_alias == "my_product"
        assert registry.product.agent_prompt_files == ("MY_PRODUCT.md", "AGENTS.md")
        assert resolve_console_static_dir() == console_dir

        channels = registry.channels.apply_policy(registry.features)
        assert channels["workchat"].factory is WorkChatChannel
        assert "discord" not in channels
        assert registry.channels.custom_sources == [channel_dir]
        assert registry.features.is_feature_enabled("builtin_qa_agent") is False
