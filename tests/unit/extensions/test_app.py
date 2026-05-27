from qwenpaw.extensions import ExtensionRegistry, ProductSpec, use_extension_registry
from qwenpaw.extensions.app import resolve_console_static_dir


def test_console_static_dir_resolves_from_product(tmp_path):
    registry = ExtensionRegistry()
    registry.configure_product(ProductSpec(console_static_dir=tmp_path / "console"))

    with use_extension_registry(registry):
        assert resolve_console_static_dir() == tmp_path / "console"
