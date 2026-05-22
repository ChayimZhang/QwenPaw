"""Channel extension registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from qwenpaw.extensions.specs import BuiltinChannelSpec, FeaturePolicy


@dataclass
class ChannelExtensionRegistry:
    builtin_specs: dict[str, BuiltinChannelSpec] = field(default_factory=dict)
    custom_sources: list[Path] = field(default_factory=list)

    def register_builtin(self, spec: BuiltinChannelSpec) -> None:
        self.builtin_specs[spec.key] = spec

    def replace_builtin(self, spec: BuiltinChannelSpec) -> None:
        self.builtin_specs[spec.key] = spec

    def disable_builtin(self, key: str) -> None:
        self.builtin_specs.pop(key, None)

    def add_custom_source(self, path: str | Path) -> None:
        self.custom_sources.append(Path(path).expanduser())

    def apply_policy(
        self,
        policy: FeaturePolicy,
    ) -> dict[str, BuiltinChannelSpec]:
        result: dict[str, BuiltinChannelSpec] = {}
        for key, spec in self.builtin_specs.items():
            if spec.required or (
                policy.is_feature_enabled("builtin_channels")
                and policy.is_channel_enabled(key)
            ):
                result[key] = spec
        return result
