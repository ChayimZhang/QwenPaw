"""Public extension SDK exports."""

from qwenpaw.extensions.cli import CliRegistry
from qwenpaw.extensions.env import EnvResolver
from qwenpaw.extensions.app import AppExtensionRegistry, RouterRegistration
from qwenpaw.extensions.channels import ChannelExtensionRegistry
from qwenpaw.extensions.features import (
    iter_plugin_search_paths,
    should_create_builtin_qa_agent,
    should_load_plugin,
)
from qwenpaw.extensions.loader import load_extensions
from qwenpaw.extensions.logging import resolve_logging_spec
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
    "ExtensionRegistry",
    "ExtensionSpec",
    "FeaturePolicy",
    "LoggingSpec",
    "PluginPolicy",
    "ProductSpec",
    "ProviderPatch",
    "ProviderExtensionRegistry",
    "RouterRegistration",
    "get_extension_registry",
    "iter_plugin_search_paths",
    "load_extensions",
    "resolve_logging_spec",
    "should_create_builtin_qa_agent",
    "should_load_plugin",
    "use_extension_registry",
]
