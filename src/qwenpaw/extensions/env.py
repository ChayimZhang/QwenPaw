"""Environment variable resolution for extension-aware prefixes."""

from __future__ import annotations

import os
from collections.abc import Mapping

from qwenpaw.extensions.specs import ProductSpec


class EnvResolver:
    """Resolve canonical env suffixes across product-specific prefixes."""

    def __init__(
        self,
        product: ProductSpec,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        self.product = product
        self.environ = os.environ if environ is None else environ

    def suffix(self, key: str) -> str:
        normalized = key.strip().upper()
        for prefix in self.product.env_prefixes:
            marker = f"{prefix}_"
            if normalized.startswith(marker):
                return normalized[len(marker) :]
        return normalized

    def names(self, key: str) -> tuple[str, ...]:
        suffix = self.suffix(key)
        return tuple(f"{prefix}_{suffix}" for prefix in self.product.env_prefixes)

    def key(self, key: str) -> str:
        return self.names(key)[0]

    def get(self, key: str, default: str | None = None) -> str | None:
        for name in self.names(key):
            value = self.environ.get(name)
            if value is not None:
                return value
        return default

    def get_bool(self, key: str, default: bool = False) -> bool:
        value = self.get(key)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    def get_int(self, key: str, default: int = 0) -> int:
        value = self.get(key)
        if value is None or value == "":
            return default
        return int(value)

    def get_float(self, key: str, default: float = 0.0) -> float:
        value = self.get(key)
        if value is None or value == "":
            return default
        return float(value)
