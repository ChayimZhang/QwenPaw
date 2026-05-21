"""Public extension SDK exports."""

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
    "ExtensionRegistry",
    "ExtensionSpec",
    "FeaturePolicy",
    "LoggingSpec",
    "PluginPolicy",
    "ProductSpec",
    "ProviderPatch",
    "get_extension_registry",
    "use_extension_registry",
]
