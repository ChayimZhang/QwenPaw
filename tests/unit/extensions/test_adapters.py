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


def test_adapters_update_product_fields(tmp_path):
    registry = ExtensionRegistry()
    adapters = ExtensionAdapters(registry)

    adapters.product_version("2.0.0")
    adapters.product(module_alias="custom_product", working_dir=tmp_path / "work")
    adapters.agent_prompt_files("MY_PRODUCT.md", "AGENTS.md")

    assert registry.product.product_version == "2.0.0"
    assert registry.product.module_alias == "custom_product"
    assert registry.product.working_dir == tmp_path / "work"
    assert registry.product.agent_prompt_files == ("MY_PRODUCT.md", "AGENTS.md")


def test_registry_exposes_adapters():
    registry = ExtensionRegistry()

    assert isinstance(registry.adapters, ExtensionAdapters)
