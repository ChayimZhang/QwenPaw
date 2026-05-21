from pathlib import Path

from qwenpaw.extensions import (
    ExtensionRegistry,
    FeaturePolicy,
    PluginPolicy,
    ProductSpec,
    get_extension_registry,
    use_extension_registry,
)


def test_registry_default_product_is_qwenpaw():
    registry = ExtensionRegistry()

    assert registry.product.product_name == "QwenPaw"
    assert registry.product.cli_name == "qwenpaw"


def test_registry_configure_product_replaces_default(tmp_path):
    registry = ExtensionRegistry()
    spec = ProductSpec(
        product_name="MyProduct",
        cli_name="myproduct",
        env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"),
        working_dir=tmp_path / "work",
    )

    registry.configure_product(spec)

    assert registry.product.product_name == "MyProduct"
    assert registry.product.working_dir == tmp_path / "work"
    assert registry.logging.namespace == "myproduct"


def test_use_extension_registry_is_scoped():
    outer = get_extension_registry()
    inner = ExtensionRegistry()
    inner.configure_product(ProductSpec(product_name="ScopedProduct"))

    with use_extension_registry(inner):
        assert get_extension_registry().product.product_name == "ScopedProduct"

    assert get_extension_registry() is outer


def test_builder_configures_product_and_features(tmp_path):
    registry = ExtensionRegistry()

    (
        registry.extension("my_product")
        .product(name="MyProduct", version="2.0.0", cli_name="myproduct")
        .env_prefix("MYPRODUCT")
        .working_dir(tmp_path / "work")
        .disable_features("builtin_qa_agent")
        .disable_channels("wechat")
        .disable_providers("openrouter")
    )

    assert registry.product.product_name == "MyProduct"
    assert registry.product.product_version == "2.0.0"
    assert registry.product.module_alias == "my_product"
    assert registry.product.cli_name == "myproduct"
    assert registry.product.env_prefixes == ("MYPRODUCT", "QWENPAW", "COPAW")
    assert registry.product.working_dir == tmp_path / "work"
    assert registry.product.backup_dir == tmp_path / "work" / "backups"
    assert registry.product.plugins_dir == tmp_path / "work" / "plugins"
    assert registry.product.custom_channels_dir == tmp_path / "work" / "custom_channels"
    assert registry.features.is_feature_enabled("builtin_qa_agent") is False
    assert registry.features.is_channel_enabled("wechat") is False
    assert registry.features.is_provider_enabled("openrouter") is False


def test_builder_configures_paths(tmp_path):
    registry = ExtensionRegistry()
    console_dir = tmp_path / "console"

    (
        registry.extension("my_product")
        .product(name="MyProduct")
        .working_dir(tmp_path / "work")
        .secret_dir(tmp_path / "secret")
        .console_static_dir(console_dir)
    )

    assert registry.product.working_dir == tmp_path / "work"
    assert registry.product.secret_dir == tmp_path / "secret"
    assert registry.product.console_static_dir == console_dir


def test_configure_features_merges_disabled_sets():
    registry = ExtensionRegistry()
    registry.configure_features(FeaturePolicy(disabled_features={"builtin_qa_agent"}))
    registry.configure_features(FeaturePolicy(disabled_channels={"wechat"}))

    assert registry.features.is_feature_enabled("builtin_qa_agent") is False
    assert registry.features.is_channel_enabled("wechat") is False


def test_configure_plugins_merges_plugin_policy(tmp_path):
    registry = ExtensionRegistry()
    registry.configure_plugins(
        PluginPolicy(
            disabled_plugins={"qwenpaw-pet"},
            extra_search_paths=(tmp_path / "plugins",),
        )
    )

    assert registry.features.is_plugin_enabled("qwenpaw-pet") is False
    assert registry.plugins.extra_search_paths == (tmp_path / "plugins",)


def test_extension_builder_rejects_empty_name():
    registry = ExtensionRegistry()

    try:
        registry.extension("")
    except ValueError as exc:
        assert "extension name is required" in str(exc)
    else:
        raise AssertionError("empty extension name should fail")


def test_registry_context_fixture(extension_registry):
    extension_registry.configure_product(ProductSpec(product_name="FixtureProduct"))

    assert get_extension_registry().product.product_name == "FixtureProduct"
