from pathlib import Path

import pytest

from qwenpaw.extensions import (
    BuiltinChannelSpec,
    ExtensionSpec,
    FeaturePolicy,
    ProductSpec,
    RunnerPatch,
)


def test_product_spec_defaults_expand_paths_under_working_dir():
    spec = ProductSpec()

    assert spec.product_name == "QwenPaw"
    assert spec.module_alias == "qwenpaw"
    assert spec.cli_name == "qwenpaw"
    assert spec.working_dir == Path("~/.qwenpaw").expanduser()
    assert spec.secret_dir == Path("~/.qwenpaw.secret").expanduser()
    assert spec.backup_dir == spec.working_dir / "backups"
    assert spec.plugins_dir == spec.working_dir / "plugins"
    assert spec.custom_channels_dir == spec.working_dir / "custom_channels"
    assert spec.media_dir == spec.working_dir / "media"
    assert spec.local_provider_dir == spec.working_dir / "local_models"
    assert spec.product_version is None
    assert spec.console_static_dir is None
    assert spec.agent_prompt_files == ("AGENTS.md", "SOUL.md", "PROFILE.md")


def test_product_spec_normalizes_explicit_console_static_dir():
    spec = ProductSpec(console_static_dir="~/myproduct/console")

    assert spec.console_static_dir == Path("~/myproduct/console").expanduser()


def test_product_spec_rejects_unknown_env_prefixes_field():
    with pytest.raises(TypeError):
        ProductSpec(product_name="MyProduct", env_prefixes=("MYPRODUCT", "QWENPAW"))


def test_feature_policy_normalizes_sets_and_checks_enabled_state():
    policy = FeaturePolicy(
        disabled_features=["voice"],
        disabled_channels=("discord",),
    )

    assert policy.disabled_features == {"voice"}
    assert policy.disabled_channels == {"discord"}
    assert not policy.is_feature_enabled("voice")
    assert policy.is_feature_enabled("chat")
    assert not policy.is_channel_enabled("discord")
    assert policy.is_channel_enabled("console")


def test_feature_policy_accepts_none_values():
    policy = FeaturePolicy(
        disabled_features=None,
        disabled_channels=None,
    )

    assert policy.disabled_features == set()
    assert policy.disabled_channels == set()


def test_builtin_channel_spec_requires_key():
    with pytest.raises(ValueError, match="key is required"):
        BuiltinChannelSpec(key="", factory=object)

    spec = BuiltinChannelSpec(key="console", factory=object)
    assert spec.key == "console"
    assert spec.default_enabled is False


def test_builtin_channel_spec_success_shape():
    spec = BuiltinChannelSpec(
        key="console",
        factory=object,
        required=True,
        default_enabled=False,
        display_name="Console",
    )

    assert spec.factory is object
    assert spec.required is True
    assert spec.default_enabled is False
    assert spec.display_name == "Console"


def test_runner_patch_defaults():
    spec = RunnerPatch()

    assert spec.query_handler_hooks == ()
    assert spec.before_query_stream_hooks == ()
    assert spec.query_stream_message_hooks == ()
    assert spec.after_query_stream_hooks == ()


def test_extension_spec_minimal_shape():
    spec = ExtensionSpec(name="my_product")

    assert spec.name == "my_product"
    assert spec.product is None
    assert isinstance(spec.features, FeaturePolicy)
    assert isinstance(spec.runner_patch, RunnerPatch)
