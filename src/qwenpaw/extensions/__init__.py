"""Public extension SDK exports."""

from qwenpaw.extensions.adapters import ExtensionAdapters
from qwenpaw.extensions.channels import ChannelExtensionRegistry
from qwenpaw.extensions.config import (
    apply_manifest,
    apply_manifest_data,
    apply_manifest_resource,
)
from qwenpaw.extensions.decorators import (
    ExtensionContext,
    ExtensionDecorator,
    qwenpaw_extension,
)
from qwenpaw.extensions.features import (
    EXTENSION_FEATURES,
    ExtensionFeature,
    is_feature_enabled,
    should_create_builtin_qa_agent,
    should_load_builtin_channel,
    should_load_custom_channels,
)
from qwenpaw.extensions.loader import discover_extension_manifest, load_extensions
from qwenpaw.extensions.runner import RunnerExtensionRegistry, RunnerQueryContext
from qwenpaw.extensions.specs import (
    BuiltinChannelSpec,
    ExtensionSpec,
    FeaturePolicy,
    RunnerPatch,
)
from qwenpaw.extensions.registry import (
    ExtensionRegistry,
    extension_registry,
    get_extension_registry,
    use_extension_registry,
)

__all__ = [
    "apply_manifest",
    "apply_manifest_data",
    "apply_manifest_resource",
    "BuiltinChannelSpec",
    "ChannelExtensionRegistry",
    "EXTENSION_FEATURES",
    "ExtensionFeature",
    "ExtensionAdapters",
    "ExtensionRegistry",
    "ExtensionContext",
    "ExtensionDecorator",
    "ExtensionSpec",
    "FeaturePolicy",
    "RunnerExtensionRegistry",
    "RunnerQueryContext",
    "RunnerPatch",
    "extension_registry",
    "discover_extension_manifest",
    "get_extension_registry",
    "is_feature_enabled",
    "load_extensions",
    "should_create_builtin_qa_agent",
    "should_load_builtin_channel",
    "should_load_custom_channels",
    "qwenpaw_extension",
    "use_extension_registry",
]
