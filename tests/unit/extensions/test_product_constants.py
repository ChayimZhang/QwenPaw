import importlib

from qwenpaw.extensions import ExtensionRegistry, ProductSpec, use_extension_registry


def _reload_constant_with(registry: ExtensionRegistry):
    import qwenpaw.constant as constant

    with use_extension_registry(registry):
        return importlib.reload(constant)


def _restore_default_constant():
    import qwenpaw.constant as constant

    with use_extension_registry(ExtensionRegistry()):
        importlib.reload(constant)


def test_constant_uses_extension_product_paths(tmp_path):
    registry = ExtensionRegistry()
    registry.configure_product(
        ProductSpec(
            product_name="MyProduct",
            product_version="2.0.0",
            module_alias="my_product",
            env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"),
            working_dir=tmp_path / "work",
            secret_dir=tmp_path / "secret",
        )
        )

    try:
        constant = _reload_constant_with(registry)

        assert constant.MODULE_NAME == "my_product"
        assert constant.PROJECT_NAME == "MyProduct"
        assert constant.PROJECT_VERSION == "2.0.0"
        assert constant.WORKING_DIR == tmp_path / "work"
        assert constant.SECRET_DIR == tmp_path / "secret"
        assert constant.CUSTOM_CHANNELS_DIR == tmp_path / "work" / "custom_channels"
        assert constant.PLUGINS_DIR == tmp_path / "work" / "plugins"
        assert constant.DEFAULT_LOCAL_PROVIDER_DIR == tmp_path / "work" / "local_models"
    finally:
        _restore_default_constant()


def test_constant_env_prefix_priority(tmp_path, monkeypatch):
    monkeypatch.setenv("MYPRODUCT_WORKING_DIR", str(tmp_path / "business"))
    monkeypatch.setenv("QWENPAW_WORKING_DIR", str(tmp_path / "qwenpaw"))
    registry = ExtensionRegistry()
    registry.configure_product(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )

    try:
        constant = _reload_constant_with(registry)

        assert constant.WORKING_DIR == tmp_path / "business"
    finally:
        monkeypatch.delenv("MYPRODUCT_WORKING_DIR", raising=False)
        monkeypatch.delenv("QWENPAW_WORKING_DIR", raising=False)
        _restore_default_constant()


def test_constant_uses_business_prefixed_log_level_env_key():
    registry = ExtensionRegistry()
    registry.configure_product(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )

    try:
        constant = _reload_constant_with(registry)

        assert constant.LOG_LEVEL_ENV == "MYPRODUCT_LOG_LEVEL"
    finally:
        _restore_default_constant()
