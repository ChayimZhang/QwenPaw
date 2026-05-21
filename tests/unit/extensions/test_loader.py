from qwenpaw.extensions import ExtensionRegistry, ProductSpec, load_extensions


class _EntryPointStub:
    def __init__(self, register):
        self._register = register

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
    assert registry.features.is_feature_enabled("builtin_qa_agent") is False
    assert registry.features.is_channel_enabled("wechat") is False
    assert registry.plugins.extra_search_paths[0].as_posix().endswith(
        "/opt/myproduct/plugins"
    )


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
