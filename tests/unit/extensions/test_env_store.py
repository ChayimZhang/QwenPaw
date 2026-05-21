from qwenpaw.extensions import ExtensionRegistry, ProductSpec, use_extension_registry


def test_env_store_protects_business_prefixed_bootstrap_keys():
    from qwenpaw.envs import store

    registry = ExtensionRegistry()
    registry.configure_product(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )

    with use_extension_registry(registry):
        assert store._is_protected_bootstrap_key("MYPRODUCT_WORKING_DIR") is True
        assert store._is_protected_bootstrap_key("QWENPAW_SECRET_DIR") is True
        assert store._is_protected_bootstrap_key("MYPRODUCT_AUTH_ENABLED") is False
