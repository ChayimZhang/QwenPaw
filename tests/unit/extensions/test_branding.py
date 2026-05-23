from pathlib import Path

import click
from click.testing import CliRunner

from qwenpaw.extensions import (
    ExtensionRegistry,
    ProductSpec,
    brand_click_command,
    brand_text,
    cli_invocation,
    product_local_provider_name,
    restore_artifact_name,
    use_extension_registry,
)


def test_brand_text_uses_product_spec(tmp_path: Path) -> None:
    registry = ExtensionRegistry()
    registry.configure_product(
        ProductSpec(
            product_name="MyProduct",
            module_alias="myproduct",
            cli_name="myproduct",
            env_prefixes=("MYPRODUCT", "QWENPAW"),
            working_dir=tmp_path / ".myproduct",
        )
    )

    with use_extension_registry(registry):
        assert (
            brand_text("QwenPaw uses qwenpaw and QWENPAW under ~/.qwenpaw")
            == "MyProduct uses myproduct and MYPRODUCT under ~/.myproduct"
        )
        assert cli_invocation("models", "config") == "myproduct models config"
        assert product_local_provider_name() == "MyProduct Local"
        assert restore_artifact_name(".lock") == ".myproduct_restore.lock"


def test_brand_click_command_updates_help_text() -> None:
    registry = ExtensionRegistry()
    registry.configure_product(
        ProductSpec(
            product_name="MyProduct",
            module_alias="myproduct",
            cli_name="myproduct",
            working_dir="~/.myproduct",
        )
    )

    @click.command(help="Run QwenPaw from ~/.qwenpaw")
    @click.option("--flag", help="Use qwenpaw mode")
    def command(flag: str | None = None) -> None:
        click.echo(flag or "ok")

    with use_extension_registry(registry):
        brand_click_command(command)
        result = CliRunner().invoke(command, ["--help"])

    assert result.exit_code == 0
    assert "Run MyProduct from ~/.myproduct" in result.output
    assert "Use myproduct mode" in result.output
