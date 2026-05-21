"""Extension test fixtures."""

import pytest

from qwenpaw.extensions import ExtensionRegistry, use_extension_registry


@pytest.fixture
def extension_registry():
    registry = ExtensionRegistry()
    with use_extension_registry(registry):
        yield registry
