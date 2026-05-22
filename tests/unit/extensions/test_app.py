from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from qwenpaw.extensions import ExtensionRegistry, ProductSpec, use_extension_registry
from qwenpaw.extensions.app import AppExtensionRegistry, resolve_console_static_dir
from qwenpaw.utils.console_static import resolve_console_static_dir as resolve_static_dir


def test_app_registry_includes_router_before_spa():
    app = FastAPI()
    registry = AppExtensionRegistry()
    router = APIRouter()

    @router.get("/health")
    def health():
        return {"status": "ok"}

    registry.add_router(router, prefix="/api/product", tags=["product"])
    registry.apply_routers(app)

    response = TestClient(app).get("/api/product/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_registry_runs_hooks():
    calls = []
    app = FastAPI()
    registry = AppExtensionRegistry()
    registry.add_middleware_hook(lambda target: calls.append(("middleware", target)))
    registry.add_before_include_routers_hook(lambda target: calls.append(("before", target)))
    registry.add_after_include_routers_hook(lambda target: calls.append(("after", target)))
    registry.add_startup_hook(lambda: calls.append(("startup", None)))
    registry.add_shutdown_hook(lambda: calls.append(("shutdown", None)))

    registry.apply_middleware(app)
    for hook in registry.before_include_routers:
        hook(app)
    for hook in registry.after_include_routers:
        hook(app)
    registry.run_startup_hooks()
    registry.run_shutdown_hooks()

    assert calls == [
        ("middleware", app),
        ("before", app),
        ("after", app),
        ("startup", None),
        ("shutdown", None),
    ]


def test_console_static_dir_prefers_product_spec(tmp_path):
    static_dir = tmp_path / "console"
    registry = ExtensionRegistry()
    registry.configure_product(ProductSpec(console_static_dir=static_dir))

    with use_extension_registry(registry):
        assert resolve_console_static_dir() == static_dir
        assert resolve_static_dir() == str(static_dir)
