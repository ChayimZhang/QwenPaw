from qwenpaw.extensions import BuiltinChannelSpec, ExtensionRegistry
from qwenpaw.extensions.adapters import ExtensionAdapters


class ExampleChannel:
    pass


def test_adapters_register_channel_and_custom_channel_source(tmp_path):
    registry = ExtensionRegistry()
    adapters = ExtensionAdapters(registry)

    adapters.builtin_channel(BuiltinChannelSpec(key="example", factory=ExampleChannel))
    adapters.custom_channel_source(tmp_path / "channels")

    assert registry.channels.builtin_specs["example"].factory is ExampleChannel
    assert registry.channels.custom_sources == [tmp_path / "channels"]


def test_adapters_expose_feature_and_channel_helpers():
    registry = ExtensionRegistry()
    adapters = ExtensionAdapters(registry)

    adapters.disable_feature("builtin_qa_agent")
    adapters.disable_channel("wechat")

    assert registry.features.is_feature_enabled("builtin_qa_agent") is False
    assert registry.features.is_channel_enabled("wechat") is False


def test_registry_exposes_adapters():
    registry = ExtensionRegistry()

    assert isinstance(registry.adapters, ExtensionAdapters)
