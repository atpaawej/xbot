"""Base classes and context interfaces for the slash command system."""

from __future__ import annotations

import shlex
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional, Sequence

from rich.console import Console

from xbot.commands.ui.prompts import (
    ask_async,
    confirm_async,
    fuzzy_select_async,
    select_async,
)

if TYPE_CHECKING:
    from xbot.agent import AgentManager


@dataclass
class CommandResult:
    """Outcome of a slash command execution."""

    should_exit: bool = False
    message: Optional[str] = None
    handled: bool = True


@dataclass
class CommandContext:
    """Execution context and UI interaction helpers provided to slash commands."""

    console: Console
    agent_manager: AgentManager
    raw_args: str = ""
    args: list[str] = field(default_factory=list)
    tui: Optional[Any] = None

    @classmethod
    def create(
        cls,
        console: Console,
        agent_manager: AgentManager,
        raw_args: str = "",
        tui: Optional[Any] = None,
    ) -> CommandContext:
        """Construct context with parsed argument list."""
        parsed_args: list[str] = []
        if raw_args.strip():
            try:
                parsed_args = shlex.split(raw_args.strip())
            except ValueError:
                parsed_args = raw_args.strip().split()

        return cls(
            console=console,
            agent_manager=agent_manager,
            raw_args=raw_args.strip(),
            args=parsed_args,
            tui=tui,
        )

    async def fuzzy_select(
        self,
        message: str,
        choices: Sequence[Any],
        default: Any = None,
        instruction: str = "(↑/↓ or type to search, Enter to select, Esc to cancel)",
        max_height: str | int = "70%",
        pointer: str = "❯ ",
    ) -> Optional[Any]:
        """Interactive fuzzy picker with live search filter and Esc cancel."""
        return await fuzzy_select_async(
            message=message,
            choices=choices,
            default=default,
            instruction=instruction,
            max_height=max_height,
            pointer=pointer,
        )

    async def select(
        self,
        message: str,
        choices: Sequence[Any],
        default: Any = None,
        instruction: str = "(Use ↑/↓ arrow keys, Enter to select, Esc to cancel)",
        max_height: str | int = "70%",
        pointer: str = "❯ ",
    ) -> Optional[Any]:
        """Interactive arrow-key selector with Esc cancel."""
        return await select_async(
            message=message,
            choices=choices,
            default=default,
            instruction=instruction,
            max_height=max_height,
            pointer=pointer,
        )

    async def confirm(
        self,
        message: str,
        default: bool = True,
        instruction: str = "(Y/n, Esc to cancel)",
    ) -> Optional[bool]:
        """Interactive confirm prompt with Esc cancel."""
        return await confirm_async(
            message=message,
            default=default,
            instruction=instruction,
        )

    async def ask(
        self,
        message: str,
        default: str = "",
        instruction: str = "(Enter to submit, Esc to cancel)",
    ) -> Optional[str]:
        """Interactive text input prompt with Esc cancel."""
        return await ask_async(
            message=message,
            default=default,
            instruction=instruction,
        )


class BaseCommand(ABC):
    """Abstract base class for all slash commands."""

    name: str
    aliases: list[str] = []
    description: str = ""
    usage: str = ""
    category: str = "General"

    @abstractmethod
    async def execute(self, context: CommandContext) -> Optional[CommandResult]:
        """Execute the slash command within the provided context."""
        raise NotImplementedError
