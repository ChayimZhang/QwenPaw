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
  env_prefixes: [MYPRODUCT, QWENPAW, COPAW]
  console_static_dir: ./console
logging:
  file_path: ./logs/runtime.log
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
    assert registry.logging.file_path == package / "logs" / "runtime.log"


def test_config_path_overrides_package_manifest_entry_point(tmp_path, monkeypatch):
    package = tmp_path / "my_product"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "manifest.yaml").write_text(
        """
product:
  name: PackagedProduct
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

    load_extensions(registry=registry, config_path=override)

    assert registry.product.product_name == "OverrideProduct"


def test_load_extensions_from_yaml_manifest(tmp_path):
    manifest = tmp_path / "extension.yaml"
    manifest.write_text(
        """
product:
  name: MyProduct
  version: 2.0.0
  module_alias: my_product
  cli_name: myproduct
  env_prefixes: [MYPRODUCT, QWENPAW, COPAW]
  working_dir: ~/.myproduct
  secret_dir: ~/.myproduct.secret
  console_static_dir: /opt/myproduct/console
  agent_prompt_files:
    - MY_PRODUCT.md
    - AGENTS.md
logging:
  namespace: myproduct
  file_path: /var/log/myproduct/runtime.log
  format: "%(levelname)s %(message)s"
  level: DEBUG
features:
  disabled_features:
    - builtin_qa_agent
  disabled_channels:
    - wechat
plugins:
  extra_search_paths:
    - /opt/myproduct/plugins
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
    assert registry.product.env_prefixes == ("MYPRODUCT", "QWENPAW", "COPAW")
    assert registry.product.agent_prompt_files == ("MY_PRODUCT.md", "AGENTS.md")
    assert registry.logging.namespace == "myproduct"
    assert registry.logging.file_path.as_posix().endswith(
        "/var/log/myproduct/runtime.log"
    )
    assert registry.logging.format == "%(levelname)s %(message)s"
    assert registry.logging.level == "DEBUG"
    assert registry.features.is_feature_enabled("builtin_qa_agent") is False
    assert registry.features.is_channel_enabled("wechat") is False
    assert registry.plugins.extra_search_paths[0].as_posix().endswith(
        "/opt/myproduct/plugins"
    )


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
  env_prefixes: [MYPRODUCT, QWENPAW, COPAW]
  working_dir: ./.runtime
  console_static_dir: ./console
logging:
  file_path: ./logs/runtime.log
plugins:
  extra_search_paths:
    - ./plugins
""".strip(),
        encoding="utf-8",
    )
    registry = ExtensionRegistry()
    monkeypatch.chdir(nested)

    load_extensions(registry=registry, include_entry_points=False)

    assert registry.product.product_name == "MyProduct"
    assert registry.product.working_dir == project / ".runtime"
    assert registry.product.console_static_dir == project / "console"
    assert registry.logging.file_path == project / "logs" / "runtime.log"
    assert registry.plugins.extra_search_paths == (project / "plugins",)


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


def test_load_extensions_config_path_uses_registry_env_prefixes(tmp_path, monkeypatch):
    product_manifest = tmp_path / "product.yaml"
    qwenpaw_manifest = tmp_path / "qwenpaw.yaml"
    product_manifest.write_text(
        """
product:
  name: MyProduct
  env_prefixes: [MYPRODUCT, QWENPAW, COPAW]
""".strip(),
        encoding="utf-8",
    )
    qwenpaw_manifest.write_text(
        """
product:
  name: QwenPawFallback
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("MYPRODUCT_EXTENSION_CONFIG", str(product_manifest))
    monkeypatch.setenv("QWENPAW_EXTENSION_CONFIG", str(qwenpaw_manifest))
    registry = ExtensionRegistry()
    registry.configure_product(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )

    load_extensions(registry=registry, include_entry_points=False)

    assert registry.product.product_name == "MyProduct"


def test_load_extensions_bootstrap_discovers_business_prefixed_config(
    tmp_path,
    monkeypatch,
):
    manifest = tmp_path / "extension.yaml"
    manifest.write_text(
        """
product:
  name: MyProduct
  env_prefixes: [MYPRODUCT, QWENPAW, COPAW]
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("MYPRODUCT_EXTENSION_CONFIG", str(manifest))
    registry = ExtensionRegistry()

    load_extensions(registry=registry, include_entry_points=False)

    assert registry.product.product_name == "MyProduct"
    assert registry.product.env_prefixes == ("MYPRODUCT", "QWENPAW", "COPAW")


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
