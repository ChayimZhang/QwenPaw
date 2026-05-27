from qwenpaw.extensions import ExtensionRegistry, FeaturePolicy
from qwenpaw.extensions.features import (
    EXTENSION_FEATURES,
    is_feature_enabled,
    should_create_builtin_qa_agent,
    should_load_builtin_channel,
    should_load_custom_channels,
)


def test_builtin_qa_agent_policy_defaults_to_enabled():
    registry = ExtensionRegistry()

    assert should_create_builtin_qa_agent(registry) is True


def test_builtin_qa_agent_can_be_disabled():
    registry = ExtensionRegistry()
    registry.configure_features(
        FeaturePolicy(disabled_features={"builtin_qa_agent"})
    )

    assert should_create_builtin_qa_agent(registry) is False


def test_feature_catalog_exposes_known_disable_switches():
    keys = {feature.key for feature in EXTENSION_FEATURES}

    assert "builtin_qa_agent" in keys
    assert "plugins" in keys
    assert "builtin_channels" in keys
    assert "custom_channels" in keys
    assert "fastapi_extension_routers" not in keys


def test_generic_feature_gate_respects_catalog():
    registry = ExtensionRegistry()
    registry.configure_features(FeaturePolicy(disabled_features={"plugins"}))

    assert is_feature_enabled("plugins", registry) is False
    assert is_feature_enabled("builtin_qa_agent", registry) is True


def test_builtin_channel_policy_respects_required_flag():
    registry = ExtensionRegistry()
    registry.configure_features(
        FeaturePolicy(disabled_features={"builtin_channels"})
    )

    assert should_load_builtin_channel(registry, "wechat") is False
    assert should_load_builtin_channel(registry, "console", required=True) is True


def test_custom_channels_can_be_disabled():
    registry = ExtensionRegistry()
    registry.configure_features(
        FeaturePolicy(disabled_features={"custom_channels"})
    )

    assert should_load_custom_channels(registry) is False
