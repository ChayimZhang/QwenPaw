"""Public extension SDK exports."""

from qwenpaw.extensions.adapters import ExtensionAdapters
from qwenpaw.extensions.branding import (
    brand_click_command,
    brand_text,
    branding_replacements,
    cli_invocation,
    friendly_path,
    install_click_output_branding,
    legacy_restore_artifact_names,
    product_cli_name,
    product_local_provider_name,
    restore_artifact_name,
)
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
    ProductSpec,
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
    "brand_click_command",
    "brand_text",
    "branding_replacements",
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
    "ProductSpec",
    "RunnerExtensionRegistry",
    "RunnerQueryContext",
    "RunnerPatch",
    "extension_registry",
    "cli_invocation",
    "discover_extension_manifest",
    "friendly_path",
    "get_extension_registry",
    "install_click_output_branding",
    "is_feature_enabled",
    "legacy_restore_artifact_names",
    "load_extensions",
    "product_cli_name",
    "product_local_provider_name",
    "restore_artifact_name",
    "should_create_builtin_qa_agent",
    "should_load_builtin_channel",
    "should_load_custom_channels",
    "qwenpaw_extension",
    "use_extension_registry",
]
