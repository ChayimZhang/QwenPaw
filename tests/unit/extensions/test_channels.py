from types import SimpleNamespace

from qwenpaw.app.channels.base import BaseChannel
from qwenpaw.extensions import BuiltinChannelSpec, ExtensionRegistry, FeaturePolicy
from qwenpaw.extensions.channels import ChannelExtensionRegistry


class ExampleChannel:
    pass


class ProductBuiltinChannel(BaseChannel):
    channel = "product_builtin"

    async def start(self) -> None:
        pass

    async def stop(self) -> None:
        pass

    async def send(self, to_handle: str, text: str, meta=None) -> None:
        pass


def test_builtin_channel_registration_is_separate_from_custom_sources(tmp_path):
    registry = ChannelExtensionRegistry()
    registry.register_builtin(
        BuiltinChannelSpec(
            key="example",
            factory=ExampleChannel,
            required=False,
            default_enabled=True,
            display_name="Example",
        )
    )
    registry.add_custom_source(tmp_path / "custom_channels")

    assert "example" in registry.builtin_specs
    assert registry.custom_sources == [tmp_path / "custom_channels"]


def test_channel_policy_filters_non_required_builtin():
    registry = ChannelExtensionRegistry()
    registry.register_builtin(
        BuiltinChannelSpec(key="console", factory=ExampleChannel, required=True)
    )
    registry.register_builtin(BuiltinChannelSpec(key="wechat", factory=ExampleChannel))

    filtered = registry.apply_policy(
        FeaturePolicy(disabled_channels={"console", "wechat"})
    )

    assert "console" in filtered
    assert "wechat" not in filtered


def test_extension_registry_registers_builtin_channel():
    registry = ExtensionRegistry()
    registry.channels.register_builtin(
        BuiltinChannelSpec(key="example", factory=ExampleChannel)
    )

    assert "example" in registry.channels.builtin_specs


def test_registered_builtin_channel_is_visible_to_runtime_registry(
    extension_registry,
):
    from qwenpaw.app.channels.registry import (
        BUILTIN_CHANNEL_KEYS,
        clear_builtin_channel_cache,
        get_builtin_channel_specs,
        get_channel_registry,
    )

    extension_registry.channels.register_builtin(
        BuiltinChannelSpec(
            key="product_builtin",
            factory=ProductBuiltinChannel,
            display_name="Product Builtin",
        )
    )
    clear_builtin_channel_cache()

    try:
        registry = get_channel_registry()
        specs = get_builtin_channel_specs()

        assert registry["product_builtin"] is ProductBuiltinChannel
        assert "product_builtin" in BUILTIN_CHANNEL_KEYS
        assert specs["product_builtin"].display_name == "Product Builtin"
    finally:
        clear_builtin_channel_cache()


def test_builtin_channel_spec_preserves_metadata_for_runtime(extension_registry):
    from qwenpaw.app.channels.registry import get_builtin_channel_specs

    class ProductChannelConfig:
        pass

    extension_registry.channels.register_builtin(
        BuiltinChannelSpec(
            key="product_builtin",
            factory=ProductBuiltinChannel,
            config_model=ProductChannelConfig,
            default_enabled=True,
            display_name="Product Builtin",
            metadata={"category": "business"},
        )
    )

    spec = get_builtin_channel_specs()["product_builtin"]

    assert spec.config_model is ProductChannelConfig
    assert spec.default_enabled is True
    assert spec.display_name == "Product Builtin"
    assert spec.metadata == {"category": "business"}


def test_custom_channel_sources_include_extension_directories(
    tmp_path,
    extension_registry,
):
    from qwenpaw.app.channels.registry import get_channel_registry

    source_dir = tmp_path / "product_channels"
    source_dir.mkdir()
    (source_dir / "product_file_channel.py").write_text(
        "\n".join(
            [
                "from qwenpaw.app.channels.base import BaseChannel",
                "",
                "class ProductFileChannel(BaseChannel):",
                "    channel = 'product_file'",
                "    async def start(self): pass",
                "    async def stop(self): pass",
                "    async def send(self, to_handle, text, meta=None): pass",
            ]
        ),
        encoding="utf-8",
    )
    extension_registry.channels.add_custom_source(source_dir)

    registry = get_channel_registry()

    assert registry["product_file"].__name__ == "ProductFileChannel"


def test_builtin_channel_route_hook_is_called(extension_registry):
    from qwenpaw.app.channels.registry import register_custom_channel_routes

    calls = []

    def register_routes(app):
        calls.append(app)

    extension_registry.channels.register_builtin(
        BuiltinChannelSpec(
            key="with_routes",
            factory=ProductBuiltinChannel,
            route_hook=register_routes,
        )
    )
    app = SimpleNamespace(routes=[])

    register_custom_channel_routes(app)

    assert calls == [app]
