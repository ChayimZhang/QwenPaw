"""Product-aware artifact naming helpers."""

from __future__ import annotations

from qwenpaw.extensions.registry import get_extension_registry
from qwenpaw.extensions.specs import ProductSpec


def restore_artifact_name(kind: str, product: ProductSpec | None = None) -> str:
    product = product or get_extension_registry().product
    return f".{product.module_alias}_restore{kind}"


def legacy_restore_artifact_names(kind: str) -> tuple[str, ...]:
    return (f".qwenpaw_restore{kind}",)
