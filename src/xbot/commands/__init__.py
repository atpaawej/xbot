"""Production slash commands system for xbot."""

from __future__ import annotations

from xbot.commands.base import BaseCommand, CommandContext, CommandResult
from xbot.commands.completer import SlashCompleter
from xbot.commands.registry import CommandRegistry


def get_default_registry() -> CommandRegistry:
    """Create and initialize a CommandRegistry pre-populated with all built-in commands."""
    from xbot.commands.builtin import register_builtins

    registry = CommandRegistry()
    register_builtins(registry)
    return registry


__all__ = [
    "BaseCommand",
    "CommandContext",
    "CommandResult",
    "CommandRegistry",
    "SlashCompleter",
    "get_default_registry",
]
