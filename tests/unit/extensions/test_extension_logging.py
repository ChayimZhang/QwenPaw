import logging
import importlib

from qwenpaw.extensions import (
    ExtensionRegistry,
    LoggingSpec,
    ProductSpec,
    use_extension_registry,
)
from qwenpaw.extensions.logging import resolve_logging_spec


def test_resolve_logging_spec_uses_product_namespace(tmp_path):
    registry = ExtensionRegistry()
    registry.configure_product(ProductSpec(product_name="MyProduct", working_dir=tmp_path))

    with use_extension_registry(registry):
        spec = resolve_logging_spec()

    assert spec.namespace == "myproduct"
    assert spec.file_path == tmp_path / "myproduct.log"


def test_configured_logging_spec_wins(tmp_path):
    registry = ExtensionRegistry()
    registry.configure_logging(
        LoggingSpec(
            namespace="business",
            file_path=tmp_path / "business.log",
            format="%(levelname)s:%(message)s",
            level="DEBUG",
        )
    )

    with use_extension_registry(registry):
        spec = resolve_logging_spec()

    assert spec.namespace == "business"
    assert spec.file_path == tmp_path / "business.log"
    assert spec.format == "%(levelname)s:%(message)s"
    assert spec.level == "DEBUG"


def test_handler_factory_is_used(tmp_path):
    created = []

    def handler_factory(namespace, file_path, fmt, level):
        created.append((namespace, file_path, fmt, level))
        return [logging.NullHandler()]

    registry = ExtensionRegistry()
    registry.configure_logging(
        LoggingSpec(
            namespace="business",
            file_path=tmp_path / "x.log",
            handler_factory=handler_factory,
        )
    )

    with use_extension_registry(registry):
        spec = resolve_logging_spec()
        handlers = spec.create_handlers()

    assert len(handlers) == 1
    assert created == [
        (
            "business",
            tmp_path / "x.log",
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "INFO",
        )
    ]


def test_utils_logging_module_uses_extension_logging_spec(tmp_path):
    import qwenpaw.utils.logging as utils_logging

    registry = ExtensionRegistry()
    registry.configure_logging(
        LoggingSpec(
            namespace="business",
            file_path=tmp_path / "business.log",
            format="%(levelname)s:%(message)s",
        )
    )

    try:
        with use_extension_registry(registry):
            reloaded = importlib.reload(utils_logging)

        assert reloaded.LOG_NAMESPACE == "business"
        assert reloaded.LOG_FILE_BASENAME == "business.log"
        assert reloaded.LOG_FILE_PATH == tmp_path / "business.log"
    finally:
        with use_extension_registry(ExtensionRegistry()):
            importlib.reload(utils_logging)
