from qwenpaw.agents.skill_system import registry as skill_registry


def test_skill_config_env_var_name_uses_qwenpaw_prefix():
    name = skill_registry._skill_config_env_var_name("policy check")

    assert name == "QWENPAW_SKILL_CONFIG_POLICY_CHECK"
