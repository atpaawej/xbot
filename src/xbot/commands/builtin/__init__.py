"""Built-in slash commands registration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from xbot.commands.builtin.info import ConfigCommand, HelpCommand, ToolsCommand
from xbot.commands.builtin.resume import ResumeCommand
from xbot.commands.builtin.session import ClearCommand, NewCommand
from xbot.commands.builtin.system import ExitCommand

if TYPE_CHECKING:
    from xbot.commands.registry import CommandRegistry


def register_builtins(registry: CommandRegistry) -> CommandRegistry:
    """Register all standard built-in slash commands to the provided registry."""
    registry.register(ResumeCommand())
    registry.register(NewCommand())
    registry.register(ClearCommand())
    registry.register(HelpCommand())
    registry.register(ConfigCommand())
    registry.register(ToolsCommand())
    registry.register(ExitCommand())
    return registry


__all__ = [
    "register_builtins",
    "ResumeCommand",
    "NewCommand",
    "ClearCommand",
    "HelpCommand",
    "ConfigCommand",
    "ToolsCommand",
    "ExitCommand",
]
