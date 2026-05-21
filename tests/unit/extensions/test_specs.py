from pathlib import Path

import pytest

from qwenpaw.extensions import (
    AppPatch,
    BuiltinChannelSpec,
    CliCommandPatch,
    CliPatch,
    ExtensionSpec,
    FeaturePolicy,
    LoggingSpec,
    ProductSpec,
    ProviderPatch,
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
    assert spec.local_provider_dir == spec.working_dir / "local_models"
    assert spec.product_version is None
    assert spec.skill_cli_name is None
    assert spec.console_static_dir is None
    assert spec.agent_prompt_files == ("AGENTS.md", "SOUL.md", "PROFILE.md")


def test_product_spec_normalizes_explicit_console_static_dir():
    spec = ProductSpec(console_static_dir="~/myproduct/console")

    assert spec.console_static_dir == Path("~/myproduct/console").expanduser()


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


def test_logging_spec_defaults():
    logging = LoggingSpec()

    assert logging.namespace == "qwenpaw"
    assert logging.file_path is None
    assert logging.format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    assert logging.level == "INFO"
    assert logging.handler_factory is None


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


def test_cli_command_patch_success_shape():
    patch = CliCommandPatch(
        name="diagnose",
        module="my_product.cli",
        attribute="diagnose",
    )

    assert patch.name == "diagnose"
    assert patch.module == "my_product.cli"
    assert patch.attribute == "diagnose"


def test_cli_patch_success_shape():
    patch = CliCommandPatch(
        name="diagnose",
        module="my_product.cli",
        attribute="diagnose",
    )
    spec = CliPatch(
        add={"diagnose": patch},
        replace={"models": patch},
        disable=frozenset({"doctor"}),
        aliases={"llms": "models"},
    )

    assert spec.add == {"diagnose": patch}
    assert spec.replace == {"models": patch}
    assert spec.disable == frozenset({"doctor"})
    assert spec.aliases == {"llms": "models"}


def test_app_patch_defaults():
    spec = AppPatch()

    assert spec.routers == ()
    assert spec.startup_hooks == ()
    assert spec.shutdown_hooks == ()
    assert spec.middleware_hooks == ()
    assert spec.before_include_routers == ()
    assert spec.after_include_routers == ()


def test_provider_patch_success_shape():
    spec = ProviderPatch(provider_id="example", provider_cls=object, replace=True)

    assert spec.provider_id == "example"
    assert spec.provider_cls is object
    assert spec.replace is True


def test_extension_spec_minimal_shape():
    spec = ExtensionSpec(name="my_product")

    assert spec.name == "my_product"
    assert spec.product is None
    assert spec.logging is None
    assert isinstance(spec.features, FeaturePolicy)
