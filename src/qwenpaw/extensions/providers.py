"""Provider extension registry."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from qwenpaw.extensions.specs import FeaturePolicy


@dataclass
class ProviderExtensionRegistry:
    added: dict[str, Any] = field(default_factory=dict)
    replaced: dict[str, Any] = field(default_factory=dict)

    def register_provider(self, provider_id: str, provider: Any) -> None:
        self.added[provider_id] = provider

    def replace_provider(self, provider_id: str, provider: Any) -> None:
        self.replaced[provider_id] = provider

    def apply_policy(
        self,
        defaults: dict[str, Any],
        policy: FeaturePolicy,
    ) -> dict[str, Any]:
        providers = {
            provider_id: provider
            for provider_id, provider in defaults.items()
            if policy.is_provider_enabled(provider_id)
        }
        providers.update(
            {
                provider_id: provider
                for provider_id, provider in self.replaced.items()
                if policy.is_provider_enabled(provider_id)
            }
        )
        providers.update(
            {
                provider_id: provider
                for provider_id, provider in self.added.items()
                if policy.is_provider_enabled(provider_id)
            }
        )
        return providers
