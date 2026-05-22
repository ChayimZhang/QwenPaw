"""Public extension SDK exports."""

from qwenpaw.extensions.cli import CliRegistry
from qwenpaw.extensions.env import EnvResolver
from qwenpaw.extensions.adapters import ExtensionAdapters
from qwenpaw.extensions.app import AppExtensionRegistry, RouterRegistration, RouterSpec
from qwenpaw.extensions.channels import ChannelExtensionRegistry
from qwenpaw.extensions.decorators import (
    ExtensionContext,
    ExtensionDecorator,
    qwenpaw_extension,
)
from qwenpaw.extensions.features import (
    EXTENSION_FEATURES,
    ExtensionFeature,
    iter_plugin_search_paths,
    is_feature_enabled,
    should_create_builtin_qa_agent,
    should_include_extension_routers,
    should_load_builtin_channel,
    should_load_custom_channels,
    should_load_plugin,
)
from qwenpaw.extensions.loader import load_extensions
from qwenpaw.extensions.logging import resolve_log_level, resolve_logging_spec
from qwenpaw.extensions.providers import ProviderExtensionRegistry
from qwenpaw.extensions.specs import (
    AppPatch,
    BuiltinChannelSpec,
    CliCommandPatch,
    CliPatch,
    ExtensionSpec,
    FeaturePolicy,
    LoggingSpec,
    PluginPolicy,
    ProductSpec,
    ProviderPatch,
)
from qwenpaw.extensions.registry import (
    ExtensionRegistry,
    extension_registry,
    get_extension_registry,
    use_extension_registry,
)

__all__ = [
    "AppPatch",
    "AppExtensionRegistry",
    "BuiltinChannelSpec",
    "ChannelExtensionRegistry",
    "CliCommandPatch",
    "CliPatch",
    "CliRegistry",
    "EnvResolver",
    "EXTENSION_FEATURES",
    "ExtensionFeature",
    "ExtensionAdapters",
    "ExtensionRegistry",
    "ExtensionContext",
    "ExtensionDecorator",
    "ExtensionSpec",
    "FeaturePolicy",
    "LoggingSpec",
    "PluginPolicy",
    "ProductSpec",
    "ProviderPatch",
    "ProviderExtensionRegistry",
    "RouterRegistration",
    "RouterSpec",
    "extension_registry",
    "get_extension_registry",
    "iter_plugin_search_paths",
    "is_feature_enabled",
    "load_extensions",
    "resolve_log_level",
    "resolve_logging_spec",
    "should_create_builtin_qa_agent",
    "should_include_extension_routers",
    "should_load_builtin_channel",
    "should_load_custom_channels",
    "should_load_plugin",
    "qwenpaw_extension",
    "use_extension_registry",
]
