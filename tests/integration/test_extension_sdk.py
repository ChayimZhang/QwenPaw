from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from qwenpaw.extensions import (
    BuiltinChannelSpec,
    EnvResolver,
    ExtensionRegistry,
    FeaturePolicy,
    ProductSpec,
    qwenpaw_extension,
    use_extension_registry,
)
from qwenpaw.extensions.app import resolve_console_static_dir


class ProductProvider:
    pass


class WorkChatChannel:
    pass


class DiscordChannel:
    pass


def test_extension_sdk_smoke_registers_product_runtime_surfaces(
    tmp_path,
    monkeypatch,
):
    extension = qwenpaw_extension("my_product")
    console_dir = tmp_path / "console"
    plugin_dir = tmp_path / "plugins"
    channel_dir = tmp_path / "channels"
    calls: list[str] = []

    @extension.product
    def product_spec():
        return ProductSpec(
            product_name="MyProduct",
            product_version="2.0.0",
            module_alias="my_product",
            cli_name="myproduct",
            skill_cli_name="myproduct-skills",
            env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"),
            working_dir=tmp_path / "work",
            secret_dir=tmp_path / "secret",
            console_static_dir=console_dir,
            agent_prompt_files=("MY_PRODUCT.md", "AGENTS.md"),
        )

    @extension.features
    def feature_policy():
        return FeaturePolicy(disabled_features={"builtin_qa_agent"})

    @extension.configure
    def configure(context):
        api = context.adapters
        router = APIRouter()

        @router.get("/health")
        def health():
            return {"ok": True}

        def channel_routes(app):
            route_router = APIRouter()

            @route_router.get("/status")
            def status():
                return {"channel": "workchat"}

            app.include_router(route_router, prefix="/api/workchat")

        api.router(router, prefix="/api/my-product", tags=["my-product"])
        api.startup_hook(lambda: calls.append("startup"))
        api.shutdown_hook(lambda: calls.append("shutdown"))
        api.middleware_hook(lambda app: setattr(app.state, "extension_hook", True))
        api.cli_command("diagnose", "my_product.cli", "diagnose")
        api.replace_cli_command("models", "my_product.cli", "models")
        api.disable_cli_command("update")
        api.cli_alias("diagnose", "check")
        api.builtin_channel(
            BuiltinChannelSpec(
                key="workchat",
                factory=WorkChatChannel,
                default_enabled=True,
                route_hook=channel_routes,
            )
        )
        api.builtin_channel(BuiltinChannelSpec(key="discord", factory=DiscordChannel))
        api.disable_channel("discord")
        api.custom_channel_source(channel_dir)
        api.provider("my-cloud", ProductProvider)
        api.replace_provider("openai", ProductProvider)
        api.disable_provider("ollama")
        api.plugin_search_path(plugin_dir)
        api.allow_plugin("my-product-console")
        api.disable_plugin("community-demo")

    registry = ExtensionRegistry()
    extension(registry)

    monkeypatch.setenv("MYPRODUCT_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("QWENPAW_LOG_LEVEL", "INFO")

    with use_extension_registry(registry):
        assert registry.product.product_name == "MyProduct"
        assert registry.product.product_version == "2.0.0"
        assert registry.product.module_alias == "my_product"
        assert registry.product.agent_prompt_files == ("MY_PRODUCT.md", "AGENTS.md")
        assert EnvResolver(registry.product).get("LOG_LEVEL") == "DEBUG"
        assert resolve_console_static_dir() == console_dir

        commands = registry.cli.build_lazy_subcommands(
            {
                "models": ("qwenpaw.cli.models", "models", ".models"),
                "skills": ("qwenpaw.cli.skills", "skills", ".skills"),
                "update": ("qwenpaw.cli.update", "update", ".update"),
            }
        )
        assert commands["diagnose"] == ("my_product.cli", "diagnose", ".diagnose")
        assert commands["check"] == commands["diagnose"]
        assert commands["models"] == ("my_product.cli", "models", ".models")
        assert "update" not in commands

        channels = registry.channels.apply_policy(registry.features)
        assert channels["workchat"].factory is WorkChatChannel
        assert "discord" not in channels
        assert registry.channels.custom_sources == [channel_dir]

        providers = registry.providers.apply_policy(
            {"openai": object, "ollama": object},
            registry.features,
        )
        assert providers["openai"] is ProductProvider
        assert providers["my-cloud"] is ProductProvider
        assert "ollama" not in providers

        assert registry.plugins.extra_search_paths == (plugin_dir,)
        assert registry.features.is_plugin_enabled("my-product-console") is True
        assert registry.features.is_plugin_enabled("community-demo") is False

        app = FastAPI()
        registry.app.apply_middleware(app)
        registry.app.apply_routers(app)
        channels["workchat"].route_hook(app)
        registry.app.run_startup_hooks()
        registry.app.run_shutdown_hooks()

        assert app.state.extension_hook is True
        assert calls == ["startup", "shutdown"]
        client = TestClient(app)
        assert client.get("/api/my-product/health").json() == {"ok": True}
        assert client.get("/api/workchat/status").json() == {"channel": "workchat"}
