# -*- coding: utf-8 -*-
"""Helpers for applying ClawMgt-delivered QwenPaw configuration changes."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from qwenpaw.agents.skill_system.store import (
    default_pool_manifest,
    default_workspace_manifest,
    get_pool_skill_manifest_path,
    get_workspace_skill_manifest_path,
    mutate_json,
)
from qwenpaw.envs import load_envs, save_envs


def upsert_pool_skill_config(
    skill_name: str,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    return _mutate_skill_config(
        get_pool_skill_manifest_path(),
        default_pool_manifest(),
        skill_name,
        dict(config),
        delete=False,
        label="Pool skill",
    )


def delete_pool_skill_config(skill_name: str) -> dict[str, Any]:
    return _mutate_skill_config(
        get_pool_skill_manifest_path(),
        default_pool_manifest(),
        skill_name,
        {},
        delete=True,
        label="Pool skill",
    )


def upsert_workspace_skill_config(
    workspace_dir: str | Path,
    skill_name: str,
    config: Mapping[str, Any],
) -> dict[str, Any]:
    return _mutate_skill_config(
        get_workspace_skill_manifest_path(Path(workspace_dir)),
        default_workspace_manifest(),
        skill_name,
        dict(config),
        delete=False,
        label="Workspace skill",
    )


def delete_workspace_skill_config(
    workspace_dir: str | Path,
    skill_name: str,
) -> dict[str, Any]:
    return _mutate_skill_config(
        get_workspace_skill_manifest_path(Path(workspace_dir)),
        default_workspace_manifest(),
        skill_name,
        {},
        delete=True,
        label="Workspace skill",
    )


def upsert_qwenpaw_env_vars(
    variables: Mapping[str, str],
) -> dict[str, str]:
    cleaned = _clean_env_mapping(variables)
    if not cleaned:
        raise ValueError("variables must contain at least one item")
    envs = load_envs()
    envs.update(cleaned)
    save_envs(envs)
    return envs


def delete_qwenpaw_env_vars(
    keys: Sequence[str],
) -> dict[str, str]:
    cleaned = _clean_key_list(keys, "keys")
    if not cleaned:
        raise ValueError("keys must contain at least one item")
    envs = load_envs()
    for key in cleaned:
        envs.pop(key, None)
    save_envs(envs)
    return envs


def apply_qwenpaw_env_update(
    variables: Mapping[str, str] | None = None,
    delete_keys: Sequence[str] | None = None,
) -> dict[str, str]:
    cleaned_variables = _clean_env_mapping(variables or {})
    cleaned_delete_keys = _clean_key_list(delete_keys or [], "deleteKeys")
    if not cleaned_variables and not cleaned_delete_keys:
        raise ValueError("variables or deleteKeys must contain at least one item")
    envs = load_envs()
    envs.update(cleaned_variables)
    for key in cleaned_delete_keys:
        envs.pop(key, None)
    save_envs(envs)
    return envs


def _mutate_skill_config(
    manifest_path: Path,
    default_payload: dict[str, Any],
    skill_name: str,
    config: dict[str, Any],
    *,
    delete: bool,
    label: str,
) -> dict[str, Any]:
    normalized_name = _require_text(skill_name, "skillName")
    if config is None:
        raise ValueError("config cannot be null")

    next_config = dict(config)

    def _update(payload: dict[str, Any]) -> bool:
        entry = payload.get("skills", {}).get(normalized_name)
        if entry is None:
            return False
        if delete:
            entry.pop("config", None)
        else:
            entry["config"] = next_config
        return True

    updated = mutate_json(manifest_path, default_payload, _update)
    if not updated:
        raise ValueError(f"{label} not found: {normalized_name}")
    return {
        "skillName": normalized_name,
        "config": next_config,
        "deleted": delete,
    }


def _clean_env_mapping(variables: Mapping[str, str]) -> dict[str, str]:
    if variables is None:
        raise ValueError("variables cannot be null")
    cleaned: dict[str, str] = {}
    for key, value in variables.items():
        cleaned[_require_text(key, "env key")] = _require_env_value(value)
    return cleaned


def _clean_key_list(keys: Sequence[str], field: str) -> list[str]:
    if keys is None:
        raise ValueError(f"{field} cannot be null")
    return [_require_text(key, field) for key in keys]


def _require_text(value: str, field: str) -> str:
    if value is None or not str(value).strip():
        raise ValueError(f"{field} cannot be blank")
    return str(value).strip()


def _require_env_value(value: str) -> str:
    if value is None:
        raise ValueError("env value cannot be null")
    return str(value)

