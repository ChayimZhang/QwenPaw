from qwenpaw.config.config import AgentProfileConfig, AgentsConfig
from qwenpaw.extensions import ExtensionRegistry, ProductSpec, use_extension_registry


def test_agent_prompt_file_defaults_use_product_spec():
    registry = ExtensionRegistry()
    registry.configure_product(
        ProductSpec(agent_prompt_files=("BRAND.md", "VOICE.md"))
    )

    with use_extension_registry(registry):
        agent_config = AgentProfileConfig(
            id="example",
            name="Example",
            description="",
            workspace_dir="/tmp/example",
        )
        root_agents = AgentsConfig()

    assert agent_config.system_prompt_files == ["BRAND.md", "VOICE.md"]
    assert root_agents.system_prompt_files == ["BRAND.md", "VOICE.md"]
