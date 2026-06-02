from qwenpaw.extensions import (
    ExtensionRegistry,
    ExtensionSpec,
    FeaturePolicy,
    discover_extension_manifest,
    load_extensions,
)


class _EntryPointStub:
    def __init__(self, register=None, *, module="", attr=""):
        self._register = register
        self.module = module
        self.attr = attr

    def load(self):
        return self._register


def test_load_extensions_from_entry_point(monkeypatch):
    registry = ExtensionRegistry()

    def register(target):
        target.extension("my_product").disable_features("builtin_qa_agent")

    entry_point = _EntryPointStub(register)
    monkeypatch.setattr(
        "qwenpaw.extensions.loader.entry_points",
        lambda group=None: [entry_point]
        if group == "qwenpaw.extensions"
        else [],
    )

    load_extensions(registry=registry)

    assert registry.features.is_feature_enabled("builtin_qa_agent") is False


def test_load_extensions_applies_entry_point_extension_spec(monkeypatch):
    registry = ExtensionRegistry()
    spec = ExtensionSpec(
        name="my_product",
        features=FeaturePolicy(disabled_features={"builtin_qa_agent"}),
    )
    entry_point = _EntryPointStub(spec)
    monkeypatch.setattr(
        "qwenpaw.extensions.loader.entry_points",
        lambda group=None: [entry_point]
        if group == "qwenpaw.extensions"
        else [],
    )

    load_extensions(registry=registry)

    assert registry.extensions["my_product"] is spec
    assert registry.features.is_feature_enabled("builtin_qa_agent") is False


def test_load_extensions_from_package_manifest_entry_point(tmp_path, monkeypatch):
    package = tmp_path / "my_product"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "manifest.yaml").write_text(
        """
features:
  disabled_features:
    - builtin_qa_agent
""".strip(),
        encoding="utf-8",
    )
    registry = ExtensionRegistry()
    manifest_entry_point = _EntryPointStub(
        module="my_product",
        attr="manifest.yaml",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(
        "qwenpaw.extensions.loader.entry_points",
        lambda group=None: [manifest_entry_point]
        if group == "qwenpaw.extension_manifests"
        else [],
    )

    load_extensions(registry=registry)

    assert registry.features.is_feature_enabled("builtin_qa_agent") is False


def test_config_path_overrides_package_manifest_entry_point(tmp_path, monkeypatch):
    package = tmp_path / "override_product"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "manifest.yaml").write_text(
        """
features:
  disabled_features:
    - packaged_feature
""".strip(),
        encoding="utf-8",
    )
    override = tmp_path / "override.yaml"
    override.write_text(
        """
features:
  disabled_features:
    - override_feature
""".strip(),
        encoding="utf-8",
    )
    registry = ExtensionRegistry()
    manifest_entry_point = _EntryPointStub(
        module="override_product",
        attr="manifest.yaml",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setattr(
        "qwenpaw.extensions.loader.entry_points",
        lambda group=None: [manifest_entry_point]
        if group == "qwenpaw.extension_manifests"
        else [],
    )

    load_extensions(registry=registry, config_path=override)

    assert registry.features.is_feature_enabled("packaged_feature") is False
    assert registry.features.is_feature_enabled("override_feature") is False


def test_load_extensions_from_yaml_manifest(tmp_path):
    manifest = tmp_path / "extension.yaml"
    manifest.write_text(
        """
features:
  disabled_features:
    - builtin_qa_agent
  disabled_channels:
    - wechat
""".strip(),
        encoding="utf-8",
    )
    registry = ExtensionRegistry()

    load_extensions(
        registry=registry,
        config_path=manifest,
        include_entry_points=False,
    )

    assert registry.features.is_feature_enabled("builtin_qa_agent") is False
    assert registry.features.is_channel_enabled("wechat") is False


def test_load_extensions_discovers_project_manifest(tmp_path, monkeypatch):
    project = tmp_path / "project"
    nested = project / "dist"
    nested.mkdir(parents=True)
    manifest = project / "manifest.yaml"
    manifest.write_text(
        """
features:
  disabled_features:
    - builtin_qa_agent
""".strip(),
        encoding="utf-8",
    )
    registry = ExtensionRegistry()
    monkeypatch.chdir(nested)

    load_extensions(registry=registry, include_entry_points=False)

    assert registry.features.is_feature_enabled("builtin_qa_agent") is False


def test_discover_extension_manifest_ignores_unrelated_manifest(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "manifest.yaml").write_text(
        """
services:
  web:
    image: example
""".strip(),
        encoding="utf-8",
    )

    assert discover_extension_manifest([project]) is None


def test_discover_extension_manifest_ignores_product_only_manifest(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "manifest.yaml").write_text(
        """
product:
  name: MyProduct
""".strip(),
        encoding="utf-8",
    )

    assert discover_extension_manifest([project]) is None


def test_discover_extension_manifest_checks_executable_path(
    tmp_path,
    monkeypatch,
):
    project = tmp_path / "project"
    dist = project / "dist"
    dist.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    (project / "manifest.yaml").write_text(
        """
features:
  disabled_features:
    - builtin_qa_agent
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.chdir(outside)
    monkeypatch.setattr(
        "qwenpaw.extensions.loader.sys.argv",
        [str(dist / "myproduct.exe")],
    )

    assert discover_extension_manifest() == project / "manifest.yaml"


def test_load_extensions_config_path_uses_qwenpaw_env(tmp_path, monkeypatch):
    qwenpaw_manifest = tmp_path / "qwenpaw.yaml"
    qwenpaw_manifest.write_text(
        """
features:
  disabled_features:
    - builtin_qa_agent
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("QWENPAW_EXTENSION_CONFIG", str(qwenpaw_manifest))
    registry = ExtensionRegistry()

    load_extensions(registry=registry, include_entry_points=False)

    assert registry.features.is_feature_enabled("builtin_qa_agent") is False


def test_load_extensions_ignores_business_prefixed_config(tmp_path, monkeypatch):
    manifest = tmp_path / "extension.yaml"
    manifest.write_text(
        """
features:
  disabled_features:
    - builtin_qa_agent
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("MYPRODUCT_EXTENSION_CONFIG", str(manifest))
    registry = ExtensionRegistry()

    load_extensions(registry=registry, include_entry_points=False)

    assert registry.features.is_feature_enabled("builtin_qa_agent") is True


def test_load_extensions_is_idempotent(monkeypatch):
    registry = ExtensionRegistry()
    calls = []

    def register(target):
        calls.append(target)

    entry_point = _EntryPointStub(register)
    monkeypatch.setattr(
        "qwenpaw.extensions.loader.entry_points",
        lambda group=None: [entry_point]
        if group == "qwenpaw.extensions"
        else [],
    )

    load_extensions(registry=registry)
    load_extensions(registry=registry)
    load_extensions(registry=registry, force=True)

    assert calls == [registry, registry]
