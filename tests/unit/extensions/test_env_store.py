def test_env_store_protects_qwenpaw_bootstrap_keys_only():
    from qwenpaw.envs import store

    assert "QWENPAW_WORKING_DIR" in store._PROTECTED_BOOTSTRAP_KEYS
    assert "QWENPAW_SECRET_DIR" in store._PROTECTED_BOOTSTRAP_KEYS
    assert "COPAW_SECRET_DIR" not in store._PROTECTED_BOOTSTRAP_KEYS
    assert "MYPRODUCT_WORKING_DIR" not in store._PROTECTED_BOOTSTRAP_KEYS
    assert "QWENPAW_AUTH_ENABLED" not in store._PROTECTED_BOOTSTRAP_KEYS
