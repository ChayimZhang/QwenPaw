"""Public extension SDK exports."""

from qwenpaw.extensions.env import EnvResolver
from qwenpaw.extensions.loader import load_extensions
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
    "BuiltinChannelSpec",
    "CliCommandPatch",
    "CliPatch",
    "EnvResolver",
    "ExtensionRegistry",
    "ExtensionSpec",
    "FeaturePolicy",
    "LoggingSpec",
    "PluginPolicy",
    "ProductSpec",
    "ProviderPatch",
    "get_extension_registry",
    "load_extensions",
    "use_extension_registry",
]
