# -*- coding: utf-8 -*-
"""Channel registry: built-in + custom channels from working dir."""

from __future__ import annotations

import importlib
import logging
import sys
import threading
from pathlib import Path
from typing import TYPE_CHECKING

from ...constant import CUSTOM_CHANNELS_DIR
from ...extensions import (
    BuiltinChannelSpec,
    get_extension_registry,
    load_extensions,
    should_load_custom_channels,
)
from .base import BaseChannel

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_BUILTIN_SPECS: dict[str, tuple[str, str]] = {
    "imessage": (".imessage", "IMessageChannel"),
    "discord": (".discord_", "DiscordChannel"),
    "dingtalk": (".dingtalk", "DingTalkChannel"),
    "feishu": (".feishu", "FeishuChannel"),
    "qq": (".qq", "QQChannel"),
    "telegram": (".telegram", "TelegramChannel"),
    "mattermost": (".mattermost", "MattermostChannel"),
    "mqtt": (".mqtt", "MQTTChannel"),
    "console": (".console", "ConsoleChannel"),
    "matrix": (".matrix", "MatrixChannel"),
    "voice": (".voice", "VoiceChannel"),
    "sip": (".sip", "SIPChannel"),
    "wecom": (".wecom", "WecomChannel"),
    "xiaoyi": (".xiaoyi", "XiaoYiChannel"),
    "wechat": (".wechat", "WeChatChannel"),
    "onebot": (".onebot", "OneBotChannel"),
}

# Required channels must load; failures are raised, not skipped.
_REQUIRED_CHANNEL_KEYS: frozenset[str] = frozenset({"console"})

_BUILTIN_CHANNEL_CACHE: dict[str, type[BaseChannel]] | None = None
_BUILTIN_CHANNEL_CACHE_LOCK = threading.Lock()


def _load_builtin_channels() -> dict[str, type[BaseChannel]]:
    """Load built-in channels safely.

    A single optional dependency failure should not break CLI startup.
    """
    _register_default_builtin_channel_specs()
    extension_registry = get_extension_registry()
    out: dict[str, type[BaseChannel]] = {}
    specs = extension_registry.channels.apply_policy(extension_registry.features)
    for key, spec in specs.items():
        cls = spec.factory
        if not (
            isinstance(cls, type)
            and issubclass(cls, BaseChannel)
            and cls is not BaseChannel
        ):
            if spec.required:
                raise TypeError(f"{key} is not a BaseChannel subtype")
            logger.debug("built-in channel unavailable: %s", key, exc_info=True)
            continue
        out[key] = cls
    return out


def _load_default_builtin_channel_specs() -> dict[str, BuiltinChannelSpec]:
    out: dict[str, BuiltinChannelSpec] = {}
    for key, (module_name, class_name) in _BUILTIN_SPECS.items():
        try:
            mod = importlib.import_module(module_name, package=__package__)
            cls = getattr(mod, class_name)
            if not (
                isinstance(cls, type)
                and issubclass(cls, BaseChannel)
                and cls is not BaseChannel
            ):
                raise TypeError(
                    f"{module_name}.{class_name} is not a BaseChannel subtype",
                )
        except Exception:
            if key in _REQUIRED_CHANNEL_KEYS:
                logger.error(
                    'failed to load required built-in channel "%s"',
                    key,
                    exc_info=True,
                )
                raise
            logger.debug(
                "built-in channel unavailable: %s",
                key,
                exc_info=True,
            )
            continue
        out[key] = BuiltinChannelSpec(
            key=key,
            factory=cls,
            required=key in _REQUIRED_CHANNEL_KEYS,
            default_enabled=key == "console",
            display_name=key,
        )
    return out


def _register_default_builtin_channel_specs() -> None:
    load_extensions()
    extension_registry = get_extension_registry()
    for key, spec in _load_default_builtin_channel_specs().items():
        if key not in extension_registry.channels.builtin_specs:
            extension_registry.channels.register_builtin(spec)


def get_builtin_channel_keys() -> frozenset[str]:
    """Return extension-aware built-in channel keys."""
    _register_default_builtin_channel_specs()
    return frozenset(get_extension_registry().channels.builtin_specs)


def get_builtin_channel_specs() -> dict[str, BuiltinChannelSpec]:
    """Return enabled extension-aware built-in channel specs."""
    _register_default_builtin_channel_specs()
    extension_registry = get_extension_registry()
    return dict(extension_registry.channels.apply_policy(extension_registry.features))


def get_builtin_channel_spec(key: str) -> BuiltinChannelSpec | None:
    return get_builtin_channel_specs().get(key)


def default_channel_config_for(key: str):
    spec = get_builtin_channel_spec(key)
    if spec is None:
        return None
    config_model = spec.config_model
    if config_model is not None:
        try:
            config = config_model()
            if hasattr(config, "model_dump"):
                data = config.model_dump()
            elif hasattr(config, "__dict__"):
                data = dict(vars(config))
            else:
                data = {}
        except Exception:
            data = {}
    else:
        data = {}
    data["enabled"] = spec.default_enabled
    data.setdefault("bot_prefix", "")
    return data


def _get_cached_builtin_channels() -> dict[str, type[BaseChannel]]:
    """Return cached built-in channels (loaded once per process)."""
    global _BUILTIN_CHANNEL_CACHE
    with _BUILTIN_CHANNEL_CACHE_LOCK:
        if _BUILTIN_CHANNEL_CACHE is None:
            _BUILTIN_CHANNEL_CACHE = _load_builtin_channels()
        return dict(_BUILTIN_CHANNEL_CACHE)


def clear_builtin_channel_cache() -> None:
    """Reset built-in channel cache. Primarily for tests."""
    global _BUILTIN_CHANNEL_CACHE
    with _BUILTIN_CHANNEL_CACHE_LOCK:
        _BUILTIN_CHANNEL_CACHE = None


def _discover_custom_channels() -> dict[str, type[BaseChannel]]:
    """Load channel classes from configured custom channel source dirs."""
    out: dict[str, type[BaseChannel]] = {}
    for _source_dir, _path, name in _iter_custom_channel_modules():
        mod = _import_custom_channel_module(name)
        if mod is None:
            continue
        for key, obj in _extract_channel_classes(mod).items():
            out[key] = obj
            logger.debug("custom channel registered: %s", key)
    return out


def _iter_custom_channel_dirs() -> tuple[Path, ...]:
    load_extensions()
    if not should_load_custom_channels():
        return ()
    paths = [
        CUSTOM_CHANNELS_DIR,
        *get_extension_registry().channels.custom_sources,
    ]
    out: list[Path] = []
    seen: set[str] = set()
    for raw_path in paths:
        path = Path(raw_path).expanduser()
        try:
            path = path.resolve()
        except OSError:
            pass
        key = str(path).casefold() if sys.platform == "win32" else str(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return tuple(out)


def _iter_custom_channel_modules():
    for source_dir in _iter_custom_channel_dirs():
        if not source_dir.is_dir():
            continue
        dir_str = str(source_dir)
        if dir_str not in sys.path:
            sys.path.insert(0, dir_str)
        importlib.invalidate_caches()
        for path in sorted(source_dir.iterdir()):
            if path.suffix == ".py" and path.stem != "__init__":
                yield source_dir, path, path.stem
            elif path.is_dir() and (path / "__init__.py").exists():
                yield source_dir, path, path.name


def _import_custom_channel_module(name: str):
    try:
        return importlib.import_module(name)
    except Exception:
        logger.exception("failed to load custom channel: %s", name)
        return None


def _extract_channel_classes(mod) -> dict[str, type[BaseChannel]]:
    out: dict[str, type[BaseChannel]] = {}
    for obj in vars(mod).values():
        if (
            isinstance(obj, type)
            and issubclass(obj, BaseChannel)
            and obj is not BaseChannel
        ):
            key = getattr(obj, "channel", None)
            if key:
                out[key] = obj
    return out


class _BuiltinChannelKeys:
    def __contains__(self, key: object) -> bool:
        return key in get_builtin_channel_keys()

    def __iter__(self):
        return iter(get_builtin_channel_keys())

    def __len__(self) -> int:
        return len(get_builtin_channel_keys())

    def __bool__(self) -> bool:
        return bool(get_builtin_channel_keys())

    def __repr__(self) -> str:
        return repr(get_builtin_channel_keys())


BUILTIN_CHANNEL_KEYS = _BuiltinChannelKeys()


def _route_paths(app) -> set[str]:
    return {
        route.path
        for route in getattr(app, "routes", ())
        if getattr(route, "path", None)
    }


def _call_route_hook(app, name: str, hook) -> None:
    prev_routes = _route_paths(app)
    hook(app)
    new_routes = _route_paths(app) - prev_routes
    non_api = {path for path in new_routes if not path.startswith("/api/")}
    if non_api:
        logger.warning(
            "Channel %s registered routes without /api/ prefix: %s. "
            "These will be swallowed by the SPA catch-all.",
            name,
            non_api,
        )


def _register_builtin_channel_routes(app) -> None:
    _register_default_builtin_channel_specs()
    extension_registry = get_extension_registry()
    specs = extension_registry.channels.apply_policy(extension_registry.features)
    for key, spec in specs.items():
        if callable(spec.route_hook):
            try:
                _call_route_hook(app, key, spec.route_hook)
            except Exception:
                logger.exception("Failed to load built-in channel routes: %s", key)


def register_custom_channel_routes(app) -> None:
    """Let registered channels add HTTP routes on the FastAPI app.

    Custom channel modules may define a module-level callable
    ``register_app_routes(app)``.  If present, it is called so the
    channel can mount its own API endpoints (e.g. QR login pages,
    webhook handlers, etc.).

    Built-in channel specs may define ``route_hook`` for the same purpose.

    Must be called at module level (before the SPA catch-all route)
    to ensure route priority.  Channels that need access to
    ``app.state.multi_agent_manager`` should read it lazily at
    request time.

    **All routes MUST be under the ``/api/`` prefix.** Routes without
    this prefix will be silently swallowed by the SPA catch-all
    (``/{full_path:path}``). A warning is emitted at startup if any
    non-``/api/`` routes are detected.

    Errors in individual channel hooks are logged but never propagated.
    """
    _register_builtin_channel_routes(app)

    for _source_dir, _path, name in _iter_custom_channel_modules():
        try:
            mod = importlib.import_module(name)
            hook = getattr(mod, "register_app_routes", None)
            if not callable(hook):
                continue
            _call_route_hook(app, name, hook)
        except Exception:
            logger.exception("Failed to load custom channel routes: %s", name)


def get_channel_registry() -> dict[str, type[BaseChannel]]:
    """Built-in channel classes + custom channels from custom_channels/."""
    out = _get_cached_builtin_channels()
    out.update(_discover_custom_channels())
    return out
