from qwenpaw.extensions import EnvResolver, ProductSpec


def test_env_resolver_prefers_downstream_prefix(monkeypatch):
    monkeypatch.setenv("MYPRODUCT_WORKING_DIR", "/tmp/myproduct")
    monkeypatch.setenv("QWENPAW_WORKING_DIR", "/tmp/qwenpaw")
    resolver = EnvResolver(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )

    assert resolver.get("WORKING_DIR") == "/tmp/myproduct"


def test_env_resolver_falls_back_to_qwenpaw(monkeypatch):
    monkeypatch.delenv("MYPRODUCT_WORKING_DIR", raising=False)
    monkeypatch.setenv("QWENPAW_WORKING_DIR", "/tmp/qwenpaw")
    resolver = EnvResolver(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )

    assert resolver.get("WORKING_DIR") == "/tmp/qwenpaw"


def test_env_resolver_accepts_legacy_literal_key(monkeypatch):
    monkeypatch.setenv("MYPRODUCT_AUTH_ENABLED", "false")
    resolver = EnvResolver(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )

    assert resolver.get("QWENPAW_AUTH_ENABLED") == "false"


def test_env_resolver_bool_int_and_float(monkeypatch):
    monkeypatch.setenv("MYPRODUCT_AUTH_ENABLED", "true")
    monkeypatch.setenv("MYPRODUCT_LLM_RATE_LIMIT_REQUESTS", "7")
    monkeypatch.setenv("MYPRODUCT_PROVIDER_TIMEOUT", "3.5")
    resolver = EnvResolver(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )

    assert resolver.get_bool("AUTH_ENABLED") is True
    assert resolver.get_int("LLM_RATE_LIMIT_REQUESTS") == 7
    assert resolver.get_float("PROVIDER_TIMEOUT") == 3.5


def test_env_resolver_key_returns_highest_priority_name():
    resolver = EnvResolver(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )

    assert resolver.key("WORKING_DIR") == "MYPRODUCT_WORKING_DIR"


def test_env_resolver_lists_candidate_names():
    resolver = EnvResolver(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )

    assert resolver.names("QWENPAW_WORKING_DIR") == (
        "MYPRODUCT_WORKING_DIR",
        "QWENPAW_WORKING_DIR",
        "COPAW_WORKING_DIR",
    )


def test_all_known_qwenpaw_env_suffixes_support_downstream_prefix(monkeypatch):
    suffixes = [
        "WORKING_DIR",
        "SECRET_DIR",
        "CONSOLE_STATIC_DIR",
        "AUTH_ENABLED",
        "AUTH_PASSWORD",
        "CORS_ORIGINS",
        "OPENAPI_DOCS",
        "BROWSER_USE_DEFAULT",
        "TOOL_GUARD_ENABLED",
        "SKILL_SCAN_MODE",
        "SKILLS_HUB_BASE_URL",
        "LLM_MAX_RETRIES",
        "LOG_LEVEL",
        "BACKUP_DIR",
        "RESTORE_LOCK_TIMEOUT_SECONDS",
        "SKILL_CONFIG_POLICY_CHECK",
    ]
    resolver = EnvResolver(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )
    for suffix in suffixes:
        monkeypatch.setenv(f"MYPRODUCT_{suffix}", f"business-{suffix}")
        monkeypatch.setenv(f"QWENPAW_{suffix}", f"qwenpaw-{suffix}")
        assert resolver.get(suffix) == f"business-{suffix}"
