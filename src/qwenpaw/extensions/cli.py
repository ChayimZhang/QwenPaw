"""Click command patching helpers for extensions."""

from __future__ import annotations

from dataclasses import dataclass, field

LazyCommand = tuple[str, str, str]
LazyCommandMap = dict[str, LazyCommand]


@dataclass
class CliRegistry:
    """Registry for extension-provided Click command patches."""

    added: LazyCommandMap = field(default_factory=dict)
    replaced: LazyCommandMap = field(default_factory=dict)
    disabled: set[str] = field(default_factory=set)
    aliases: dict[str, str] = field(default_factory=dict)

    def add_command(
        self,
        name: str,
        module: str,
        attribute: str,
        label: str | None = None,
    ) -> None:
        self.added[name] = (module, attribute, label or f".{name}")

    def disable_command(self, name: str) -> None:
        self.disabled.add(name)

    def replace_command(
        self,
        name: str,
        module: str,
        attribute: str,
        label: str | None = None,
    ) -> None:
        self.replaced[name] = (module, attribute, label or f".{name}")

    def alias_command(self, existing: str, alias: str) -> None:
        self.aliases[alias] = existing

    def build_lazy_subcommands(self, defaults: LazyCommandMap) -> LazyCommandMap:
        commands = dict(defaults)
        for name in self.disabled:
            commands.pop(name, None)
        commands.update(self.replaced)
        commands.update(self.added)
        for alias, existing in self.aliases.items():
            if existing in commands:
                commands[alias] = commands[existing]
        return commands
