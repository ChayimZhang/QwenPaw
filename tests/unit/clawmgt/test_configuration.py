# -*- coding: utf-8 -*-
from __future__ import annotations

import pytest

from qwenpaw.clawmgt import configuration


def test_upsert_and_delete_pool_skill_config(monkeypatch):
    manifest = {"skills": {"browser": {}}}

    def fake_mutate_json(path, default_payload, update):
        _ = path, default_payload
        return update(manifest)

    monkeypatch.setattr(configuration, "mutate_json", fake_mutate_json)

    upserted = configuration.upsert_pool_skill_config(
        "browser",
        {"timeout": 30},
    )
    deleted = configuration.delete_pool_skill_config("browser")

    assert upserted == {
        "skillName": "browser",
        "config": {"timeout": 30},
        "deleted": False,
    }
    assert deleted == {
        "skillName": "browser",
        "config": {},
        "deleted": True,
    }
    assert "config" not in manifest["skills"]["browser"]


def test_workspace_skill_config_raises_when_missing(monkeypatch):
    monkeypatch.setattr(
        configuration,
        "mutate_json",
        lambda path, default_payload, update: False,
    )

    with pytest.raises(ValueError, match="Workspace skill not found"):
        configuration.upsert_workspace_skill_config(
            "D:/tmp/workspace",
            "missing",
            {"timeout": 30},
        )


def test_qwenpaw_env_update_upserts_and_deletes(monkeypatch):
    saved = []

    monkeypatch.setattr(
        configuration,
        "load_envs",
        lambda: {"OLD": "1", "DELETE_ME": "bye"},
    )
    monkeypatch.setattr(configuration, "save_envs", lambda envs: saved.append(envs))

    envs = configuration.apply_qwenpaw_env_update(
        variables={"NEW": "2", "EMPTY": ""},
        delete_keys=["DELETE_ME"],
    )

    assert envs == {"OLD": "1", "NEW": "2", "EMPTY": ""}
    assert saved == [envs]


def test_qwenpaw_env_helpers_validate_empty_changes():
    with pytest.raises(ValueError, match="variables must contain"):
        configuration.upsert_qwenpaw_env_vars({})

    with pytest.raises(ValueError, match="keys must contain"):
        configuration.delete_qwenpaw_env_vars([])

    with pytest.raises(ValueError, match="variables or deleteKeys"):
        configuration.apply_qwenpaw_env_update({}, [])
