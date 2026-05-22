import json

from qwenpaw.extensions import ExtensionRegistry, FeaturePolicy, PluginPolicy
from qwenpaw.extensions.features import (
    iter_plugin_search_paths,
    should_create_builtin_qa_agent,
    should_load_plugin,
)
from qwenpaw.plugins.loader import PluginLoader


def test_builtin_qa_agent_policy_defaults_to_enabled():
    registry = ExtensionRegistry()

    assert should_create_builtin_qa_agent(registry) is True


def test_builtin_qa_agent_can_be_disabled():
    registry = ExtensionRegistry()
    registry.configure_features(
        FeaturePolicy(disabled_features={"builtin_qa_agent"})
    )

    assert should_create_builtin_qa_agent(registry) is False


def test_plugin_policy_disabled_name_wins():
    registry = ExtensionRegistry()
    registry.configure_features(FeaturePolicy(disabled_plugins={"qwenpaw-pet"}))

    assert should_load_plugin(registry, "qwenpaw-pet") is False


def test_plugin_policy_allowed_list_blocks_others():
    registry = ExtensionRegistry()
    registry.configure_features(FeaturePolicy(allowed_plugins={"core-plugin"}))

    assert should_load_plugin(registry, "core-plugin") is True
    assert should_load_plugin(registry, "other-plugin") is False


def test_plugin_policy_exposes_extra_search_paths(tmp_path):
    registry = ExtensionRegistry()
    registry.configure_plugins(
        PluginPolicy(extra_search_paths=(tmp_path / "plugins",))
    )

    assert list(iter_plugin_search_paths(registry)) == [tmp_path / "plugins"]


def test_plugin_loader_includes_extra_search_paths(tmp_path, extension_registry):
    extra_dir = tmp_path / "extension_plugins"
    extension_registry.configure_plugins(PluginPolicy(extra_search_paths=(extra_dir,)))

    loader = PluginLoader([])

    assert loader.plugin_dirs == [extra_dir]


def test_plugin_loader_skips_disabled_plugins(tmp_path, extension_registry):
    plugin_root = tmp_path / "plugins"
    plugin_dir = plugin_root / "blocked-plugin"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.json").write_text(
        json.dumps(
            {
                "id": "blocked-plugin",
                "name": "Blocked Plugin",
                "version": "1.0.0",
                "entry": {"frontend": "index.js"},
            }
        ),
        encoding="utf-8",
    )
    extension_registry.configure_features(
        FeaturePolicy(disabled_plugins={"blocked-plugin"})
    )
    loader = PluginLoader([plugin_root])

    assert loader.discover_plugins() == []
