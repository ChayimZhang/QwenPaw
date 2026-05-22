# -*- coding: utf-8 -*-
import logging
import time

_bootstrap_err: Exception | None = None
try:
    # Load persisted env vars before importing modules that read env-backed
    # constants at import time (e.g., WORKING_DIR).
    from .envs import load_envs_into_environ

    load_envs_into_environ()
except Exception as exc:
    # Best effort: package import should not fail if env bootstrap fails.
    _bootstrap_err = exc

try:
    from .extensions.logging import resolve_log_level
except Exception:
    def resolve_log_level(default: str = "info") -> str:
        return default

from .utils.logging import setup_logger

_t0 = time.perf_counter()
setup_logger(resolve_log_level("info"))
if _bootstrap_err is not None:
    logging.getLogger(__name__).warning(
        "qwenpaw: failed to load persisted envs on init: %s",
        _bootstrap_err,
    )
logging.getLogger(__name__).debug(
    "%.3fs package init",
    time.perf_counter() - _t0,
)
