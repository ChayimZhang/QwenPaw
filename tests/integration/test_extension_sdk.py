from qwenpaw.extensions import (
    BuiltinChannelSpec,
    ExtensionRegistry,
    FeaturePolicy,
    qwenpaw_extension,
    use_extension_registry,
)


class WorkChatChannel:
    pass


class DiscordChannel:
    pass


def test_extension_sdk_smoke_registers_remaining_runtime_surfaces(tmp_path):
    extension = qwenpaw_extension("my_product")
    channel_dir = tmp_path / "channels"

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
        channels = registry.channels.apply_policy(registry.features)
        assert channels["workchat"].factory is WorkChatChannel
        assert "discord" not in channels
        assert registry.channels.custom_sources == [channel_dir]
        assert registry.features.is_feature_enabled("builtin_qa_agent") is False
