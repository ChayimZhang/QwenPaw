from pathlib import Path

import pytest

from qwenpaw.extensions import (
    BuiltinChannelSpec,
    FeaturePolicy,
    LoggingSpec,
    ProductSpec,
)


def test_product_spec_defaults_expand_paths_under_working_dir():
    spec = ProductSpec()

    assert spec.product_name == "QwenPaw"
    assert spec.module_alias == "qwenpaw"
    assert spec.cli_name == "qwenpaw"
    assert spec.env_prefixes == ("QWENPAW", "COPAW")
    assert spec.working_dir == Path("~/.qwenpaw").expanduser()
    assert spec.secret_dir == Path("~/.qwenpaw.secret").expanduser()
    assert spec.backup_dir == spec.working_dir / "backups"
    assert spec.plugins_dir == spec.working_dir / "plugins"
    assert spec.custom_channels_dir == spec.working_dir / "custom_channels"
    assert spec.media_dir == spec.working_dir / "media"
    assert spec.local_provider_dir == spec.working_dir / "local_providers"


def test_product_spec_preserves_downstream_env_prefix_priority():
    spec = ProductSpec(product_name="MyProduct", env_prefixes=("MYPRODUCT", "QWENPAW"))

    assert spec.env_prefixes == ("MYPRODUCT", "QWENPAW")


@pytest.mark.parametrize("env_prefixes", [(), ("",), ("myproduct",), (123,)])
def test_product_spec_rejects_invalid_env_prefixes(env_prefixes):
    with pytest.raises(ValueError):
        ProductSpec(product_name="MyProduct", env_prefixes=env_prefixes)


def test_feature_policy_normalizes_sets_and_checks_enabled_state():
    policy = FeaturePolicy(
        disabled_features=["voice"],
        disabled_channels=("discord",),
        disabled_providers={"openai"},
        disabled_plugins=["legacy"],
        allowed_plugins=["approved"],
    )

    assert policy.disabled_features == {"voice"}
    assert policy.disabled_channels == {"discord"}
    assert policy.disabled_providers == {"openai"}
    assert policy.disabled_plugins == {"legacy"}
    assert policy.allowed_plugins == {"approved"}
    assert not policy.is_feature_enabled("voice")
    assert policy.is_feature_enabled("chat")
    assert not policy.is_channel_enabled("discord")
    assert policy.is_channel_enabled("console")
    assert not policy.is_provider_enabled("openai")
    assert policy.is_provider_enabled("local")
    assert not policy.is_plugin_enabled("legacy")
    assert policy.is_plugin_enabled("approved")
    assert not policy.is_plugin_enabled("other")


def test_logging_spec_from_product_uses_product_namespace_and_working_dir():
    product = ProductSpec(product_name="My Product", working_dir="~/myproduct")

    logging = LoggingSpec.from_product(product)

    assert logging.namespace == "myproduct"
    assert logging.file_path == product.working_dir / "myproduct.log"


def test_builtin_channel_spec_requires_key():
    with pytest.raises(ValueError, match="key is required"):
        BuiltinChannelSpec(key="")

    spec = BuiltinChannelSpec(key="console")
    assert spec.key == "console"
