from qwenpaw.extensions import (
    ExtensionRegistry,
    ExtensionSpec,
    ProductSpec,
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
        target.extension("my_product").product(name="MyProduct", cli_name="myproduct")

    entry_point = _EntryPointStub(register)
    monkeypatch.setattr(
        "qwenpaw.extensions.loader.entry_points",
        lambda group=None: [entry_point]
        if group == "qwenpaw.extensions"
        else [],
    )

    load_extensions(registry=registry)

    assert registry.product.product_name == "MyProduct"


def test_load_extensions_applies_entry_point_extension_spec(monkeypatch):
    registry = ExtensionRegistry()
    spec = ExtensionSpec(
        name="my_product",
        product=ProductSpec(product_name="MyProduct", cli_name="myproduct"),
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
    assert registry.product.product_name == "MyProduct"


def test_load_extensions_from_package_manifest_entry_point(tmp_path, monkeypatch):
    package = tmp_path / "my_product"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "manifest.yaml").write_text(
        """
product:
  name: MyProduct
  cli_name: myproduct
  console_static_dir: ./console
""".strip(),
        encoding="utf-8",
    )
    (package / "console").mkdir()
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

    assert registry.product.product_name == "MyProduct"
    assert registry.product.console_static_dir == package / "console"


def test_config_path_overrides_package_manifest_entry_point(tmp_path, monkeypatch):
    package = tmp_path / "override_product"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "manifest.yaml").write_text(
        """
product:
  name: PackagedProduct
  cli_name: packaged
""".strip(),
        encoding="utf-8",
    )
    override = tmp_path / "override.yaml"
    override.write_text(
        """
product:
  name: OverrideProduct
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

    assert registry.product.product_name == "OverrideProduct"
    assert registry.product.cli_name == "packaged"


def test_manifest_product_working_dir_recomputes_default_child_paths(tmp_path):
    manifest = tmp_path / "extension.yaml"
    manifest.write_text(
        """
product:
  working_dir: ./work
""".strip(),
        encoding="utf-8",
    )
    registry = ExtensionRegistry()

    load_extensions(registry=registry, config_path=manifest, include_entry_points=False)

    assert registry.product.working_dir == tmp_path / "work"
    assert registry.product.backup_dir == tmp_path / "work" / "backups"
    assert registry.product.plugins_dir == tmp_path / "work" / "plugins"


def test_load_extensions_from_yaml_manifest(tmp_path):
    manifest = tmp_path / "extension.yaml"
    manifest.write_text(
        """
product:
  name: MyProduct
  version: 2.0.0
  module_alias: my_product
  cli_name: myproduct
  working_dir: ~/.myproduct
  secret_dir: ~/.myproduct.secret
  console_static_dir: /opt/myproduct/console
  agent_prompt_files:
    - MY_PRODUCT.md
    - AGENTS.md
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

    assert registry.product.product_name == "MyProduct"
    assert registry.product.module_alias == "my_product"
    assert registry.product.cli_name == "myproduct"
    assert registry.product.agent_prompt_files == ("MY_PRODUCT.md", "AGENTS.md")
    assert registry.features.is_feature_enabled("builtin_qa_agent") is False
    assert registry.features.is_channel_enabled("wechat") is False


def test_load_extensions_discovers_project_manifest(tmp_path, monkeypatch):
    project = tmp_path / "project"
    nested = project / "dist"
    nested.mkdir(parents=True)
    manifest = project / "manifest.yaml"
    manifest.write_text(
        """
product:
  name: MyProduct
  cli_name: myproduct
  working_dir: ./.runtime
  console_static_dir: ./console
""".strip(),
        encoding="utf-8",
    )
    registry = ExtensionRegistry()
    monkeypatch.chdir(nested)

    load_extensions(registry=registry, include_entry_points=False)

    assert registry.product.product_name == "MyProduct"
    assert registry.product.working_dir == project / ".runtime"
    assert registry.product.console_static_dir == project / "console"


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
product:
  name: MyProduct
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
product:
  name: QwenPawFallback
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("QWENPAW_EXTENSION_CONFIG", str(qwenpaw_manifest))
    registry = ExtensionRegistry()

    load_extensions(registry=registry, include_entry_points=False)

    assert registry.product.product_name == "QwenPawFallback"


def test_load_extensions_ignores_business_prefixed_config(tmp_path, monkeypatch):
    manifest = tmp_path / "extension.yaml"
    manifest.write_text(
        """
product:
  name: MyProduct
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("MYPRODUCT_EXTENSION_CONFIG", str(manifest))
    registry = ExtensionRegistry()

    load_extensions(registry=registry, include_entry_points=False)

    assert registry.product.product_name == "QwenPaw"


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
