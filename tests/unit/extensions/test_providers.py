from qwenpaw.extensions import FeaturePolicy
from qwenpaw.extensions.providers import ProviderExtensionRegistry
from qwenpaw.providers.openai_provider import OpenAIProvider
from qwenpaw.providers.provider import ModelInfo
from qwenpaw.providers.provider_manager import ProviderManager


class ExampleProvider:
    id = "example"


class ReplacementProvider:
    id = "openai"


def _openai_provider(provider_id: str, name: str) -> OpenAIProvider:
    return OpenAIProvider(
        id=provider_id,
        name=name,
        base_url="https://example.invalid/v1",
        models=[ModelInfo(id=f"{provider_id}-model", name=f"{name} Model")],
    )


def test_provider_registry_filters_disabled_provider():
    registry = ProviderExtensionRegistry()
    defaults = {"openai": object, "openrouter": object}

    result = registry.apply_policy(
        defaults,
        FeaturePolicy(disabled_providers={"openrouter"}),
    )

    assert set(result) == {"openai"}


def test_provider_registry_adds_and_replaces_provider():
    registry = ProviderExtensionRegistry()
    registry.register_provider("example", ExampleProvider)
    registry.replace_provider("openai", ReplacementProvider)

    result = registry.apply_policy({"openai": object}, FeaturePolicy())

    assert result["example"] is ExampleProvider
    assert result["openai"] is ReplacementProvider


def test_provider_registry_policy_applies_to_added_and_replaced_provider():
    registry = ProviderExtensionRegistry()
    registry.register_provider("example", ExampleProvider)
    registry.replace_provider("openai", ReplacementProvider)

    result = registry.apply_policy(
        {"openai": object},
        FeaturePolicy(disabled_providers={"example", "openai"}),
    )

    assert result == {}


def test_provider_manager_applies_extension_provider_policy(
    extension_registry,
):
    product_provider = _openai_provider("product-openai", "Product OpenAI")
    replacement_provider = _openai_provider("openai", "Replacement OpenAI")
    extension_registry.configure_features(
        FeaturePolicy(disabled_providers={"openrouter"})
    )
    extension_registry.providers.register_provider(
        "product-openai",
        product_provider,
    )
    extension_registry.providers.replace_provider("openai", replacement_provider)

    manager = ProviderManager()

    assert manager.get_provider("openrouter") is None
    assert manager.get_provider("product-openai") is product_provider
    assert manager.get_provider("openai") is replacement_provider
