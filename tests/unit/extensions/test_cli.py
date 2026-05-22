import importlib

from click.testing import CliRunner

from qwenpaw.extensions import ExtensionRegistry, ProductSpec, use_extension_registry
from qwenpaw.extensions.cli import CliRegistry


def test_cli_registry_add_disable_replace_and_alias():
    cli = CliRegistry()
    defaults = {
        "doctor": ("qwenpaw.cli.doctor_cmd", "doctor_group", ".doctor_cmd"),
        "models": ("qwenpaw.cli.models_cmd", "models_group", ".models_cmd"),
    }

    cli.disable_command("doctor")
    cli.replace_command("models", "my_product.cli.models", "models_group")
    cli.add_command("diagnose", "my_product.cli.diagnose", "diagnose_command")
    cli.alias_command("models", "llms")

    patched = cli.build_lazy_subcommands(defaults)

    assert "doctor" not in patched
    assert patched["models"] == ("my_product.cli.models", "models_group", ".models")
    assert patched["diagnose"] == (
        "my_product.cli.diagnose",
        "diagnose_command",
        ".diagnose",
    )
    assert patched["llms"] == ("my_product.cli.models", "models_group", ".models")


def test_builder_registers_cli_command():
    registry = ExtensionRegistry()

    registry.extension("my_product").cli_command(
        "diagnose",
        "my_product.cli.diagnose",
        "diagnose_command",
    )

    assert registry.cli.added["diagnose"] == (
        "my_product.cli.diagnose",
        "diagnose_command",
        ".diagnose",
    )


def test_root_click_uses_product_name_for_help(monkeypatch):
    registry = ExtensionRegistry()
    registry.configure_product(ProductSpec(product_name="MyProduct", cli_name="myproduct"))

    import qwenpaw.cli.main as cli_main
    try:
        with use_extension_registry(registry):
            cli = importlib.reload(cli_main).cli
        result = CliRunner().invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Usage: myproduct" in result.output
    finally:
        with use_extension_registry(ExtensionRegistry()):
            importlib.reload(cli_main)


def test_root_click_uses_product_name_for_version():
    registry = ExtensionRegistry()
    registry.configure_product(
        ProductSpec(
            product_name="MyProduct",
            product_version="9.9.9",
            cli_name="myproduct",
        )
    )

    import qwenpaw.cli.main as cli_main
    try:
        with use_extension_registry(registry):
            cli = importlib.reload(cli_main).cli
        result = CliRunner().invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "MyProduct" in result.output
        assert "9.9.9" in result.output
    finally:
        with use_extension_registry(ExtensionRegistry()):
            importlib.reload(cli_main)


def test_root_click_adds_product_skill_cli_alias():
    registry = ExtensionRegistry()
    registry.configure_product(
        ProductSpec(
            product_name="MyProduct",
            skill_cli_name="abilities",
        )
    )

    import qwenpaw.cli.main as cli_main
    try:
        with use_extension_registry(registry):
            cli = importlib.reload(cli_main).cli

        assert "abilities" in cli.lazy_subcommands
        assert cli.lazy_subcommands["abilities"] == cli.lazy_subcommands["skills"]
    finally:
        with use_extension_registry(ExtensionRegistry()):
            importlib.reload(cli_main)
