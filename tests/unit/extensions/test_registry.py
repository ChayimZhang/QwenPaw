from qwenpaw.extensions import (
    BuiltinChannelSpec,
    ExtensionSpec,
    ExtensionRegistry,
    FeaturePolicy,
    get_extension_registry,
    use_extension_registry,
)


def test_registry_defaults_to_extension_surfaces():
    registry = ExtensionRegistry()

    assert registry.features.disabled_features == set()
    assert registry.features.disabled_channels == set()
    assert registry.channels.builtin_specs == {}
    assert registry.extensions == {}


def test_use_extension_registry_is_scoped():
    outer = get_extension_registry()
    inner = ExtensionRegistry()
    inner.configure_features(FeaturePolicy(disabled_features={"builtin_qa_agent"}))

    with use_extension_registry(inner):
        assert get_extension_registry().features.is_feature_enabled(
            "builtin_qa_agent"
        ) is False

    assert get_extension_registry() is outer


def test_builder_configures_features_and_channels():
    registry = ExtensionRegistry()

    (
        registry.extension("my_product")
        .disable_features("builtin_qa_agent")
        .disable_channels("wechat")
    )

    assert registry.features.is_feature_enabled("builtin_qa_agent") is False
    assert registry.features.is_channel_enabled("wechat") is False


def test_configure_features_merges_disabled_sets():
    registry = ExtensionRegistry()
    registry.configure_features(FeaturePolicy(disabled_features={"builtin_qa_agent"}))
    registry.configure_features(FeaturePolicy(disabled_channels={"wechat"}))

    assert registry.features.is_feature_enabled("builtin_qa_agent") is False
    assert registry.features.is_channel_enabled("wechat") is False


def test_extension_builder_rejects_empty_name():
    registry = ExtensionRegistry()

    try:
        registry.extension("")
    except ValueError as exc:
        assert "extension name is required" in str(exc)
    else:
        raise AssertionError("empty extension name should fail")


def test_registry_context_fixture(extension_registry):
    extension_registry.configure_features(
        FeaturePolicy(disabled_features={"builtin_qa_agent"})
    )

    assert get_extension_registry().features.is_feature_enabled(
        "builtin_qa_agent"
    ) is False


class SpecChannel:
    pass


def test_registry_apply_extension_spec_wires_remaining_surfaces():
    registry = ExtensionRegistry()
    spec = ExtensionSpec(
        name="my_product",
        features=FeaturePolicy(
            disabled_features={"builtin_qa_agent"},
            disabled_channels={"wechat"},
        ),
        builtin_channels=(
            BuiltinChannelSpec(key="spec-channel", factory=SpecChannel),
        ),
    )

    registry.apply_spec(spec)

    assert registry.extensions["my_product"] is spec
    assert registry.features.is_feature_enabled("builtin_qa_agent") is False
    assert registry.features.is_channel_enabled("wechat") is False
    assert registry.channels.builtin_specs["spec-channel"].factory is SpecChannel
