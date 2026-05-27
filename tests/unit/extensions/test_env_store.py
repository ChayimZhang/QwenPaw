def test_env_store_protects_qwenpaw_and_legacy_bootstrap_keys():
    from qwenpaw.envs import store

    assert store._is_protected_bootstrap_key("QWENPAW_WORKING_DIR") is True
    assert store._is_protected_bootstrap_key("COPAW_SECRET_DIR") is True
    assert store._is_protected_bootstrap_key("MYPRODUCT_WORKING_DIR") is False
    assert store._is_protected_bootstrap_key("QWENPAW_AUTH_ENABLED") is False
