from qwenpaw.agents.skill_system import registry as skill_registry
from qwenpaw.extensions import ExtensionRegistry, ProductSpec, use_extension_registry


def test_skill_config_env_var_name_uses_product_prefix():
    registry = ExtensionRegistry()
    registry.configure_product(
        ProductSpec(env_prefixes=("MYPRODUCT", "QWENPAW", "COPAW"))
    )

    with use_extension_registry(registry):
        name = skill_registry._skill_config_env_var_name("policy check")

    assert name == "MYPRODUCT_SKILL_CONFIG_POLICY_CHECK"
