"""Product branding helpers for extension-aware runtime text and files."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from qwenpaw.extensions.registry import get_extension_registry
from qwenpaw.extensions.specs import ProductSpec


def friendly_path(path: str | Path) -> str:
    resolved = Path(path).expanduser()
    try:
        return "~/" + resolved.resolve().relative_to(Path.home().resolve()).as_posix()
    except (OSError, ValueError):
        return str(resolved)


def branding_replacements(product: ProductSpec | None = None) -> tuple[tuple[str, str], ...]:
    product = product or get_extension_registry().product
    return (
        ("QwenPaw", product.product_name),
        ("qwenpaw", product.module_alias),
        ("~/.qwenpaw", friendly_path(product.working_dir)),
    )


def brand_text(
    text: str | None,
    *,
    product: ProductSpec | None = None,
    replacements: Iterable[tuple[str, str]] | None = None,
) -> str | None:
    if text is None:
        return None
    result = text
    for source, target in replacements or branding_replacements(product):
        result = result.replace(source, target)
    return result


def product_cli_name(product: ProductSpec | None = None) -> str:
    product = product or get_extension_registry().product
    return product.cli_name


def cli_invocation(*parts: str, product: ProductSpec | None = None) -> str:
    items = [product_cli_name(product), *[part for part in parts if part]]
    return " ".join(items)


def product_local_provider_name(product: ProductSpec | None = None) -> str:
    product = product or get_extension_registry().product
    return f"{product.product_name} Local"


def restore_artifact_name(kind: str, product: ProductSpec | None = None) -> str:
    product = product or get_extension_registry().product
    return f".{product.module_alias}_restore{kind}"


def legacy_restore_artifact_names(kind: str) -> tuple[str, ...]:
    return (f".qwenpaw_restore{kind}",)


def brand_click_command(command, *, product: ProductSpec | None = None) -> None:
    if getattr(command, "_qwenpaw_branding_applied", False):
        return
    replacements = branding_replacements(product)
    command.help = brand_text(command.help, replacements=replacements)
    command.short_help = brand_text(command.short_help, replacements=replacements)
    command.epilog = brand_text(command.epilog, replacements=replacements)
    for param in getattr(command, "params", ()):
        if hasattr(param, "help"):
            param.help = brand_text(param.help, replacements=replacements)
    command._qwenpaw_branding_applied = True


def install_click_output_branding(*, product: ProductSpec | None = None) -> None:
    import click

    if getattr(click, "_qwenpaw_branding_installed", False):
        return

    original_echo = click.echo
    original_secho = click.secho

    def echo(message=None, *args, **kwargs):
        if isinstance(message, str):
            message = brand_text(message, product=product)
        return original_echo(message, *args, **kwargs)

    def secho(message=None, *args, **kwargs):
        if isinstance(message, str):
            message = brand_text(message, product=product)
        return original_secho(message, *args, **kwargs)

    click.echo = echo
    click.secho = secho
    click._qwenpaw_branding_installed = True
