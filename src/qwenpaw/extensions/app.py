"""Console static resource resolution for extensions."""

from __future__ import annotations

from pathlib import Path


def resolve_console_static_dir() -> Path | None:
    from qwenpaw.extensions.registry import get_extension_registry

    return get_extension_registry().product.console_static_dir
