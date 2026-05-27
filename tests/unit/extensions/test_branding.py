from pathlib import Path

from qwenpaw.extensions import (
    ExtensionRegistry,
    ProductSpec,
    legacy_restore_artifact_names,
    restore_artifact_name,
    use_extension_registry,
)


def test_restore_artifact_name_uses_product_spec(tmp_path: Path) -> None:
    registry = ExtensionRegistry()
    registry.configure_product(
        ProductSpec(
            product_name="MyProduct",
            module_alias="myproduct",
            cli_name="myproduct",
            working_dir=tmp_path / ".myproduct",
        )
    )

    with use_extension_registry(registry):
        assert restore_artifact_name(".lock") == ".myproduct_restore.lock"


def test_legacy_restore_artifact_names_keep_qwenpaw_compatibility() -> None:
    assert legacy_restore_artifact_names(".lock") == (".qwenpaw_restore.lock",)
