"""Interactive terminal prompt helpers using InquirerPy with Escape-cancellation support."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from InquirerPy.utils import InquirerPyStyle, get_style

XBOT_PROMPT_STYLE: InquirerPyStyle = get_style(
    {
        "questionmark": "#00aaaa",
        "answermark": "#00ff00",
        "answer": "#00ff00 bold",
        "input": "#ffffff",
        "question": "#00ffff bold",
        "instruction": "#777777 italic",
        "pointer": "#00ffff bold",
        "selected": "#00ff00",
        "fuzzy_border": "#00aaaa",
        "fuzzy_match": "#00ffff bold",
    },
    style_override=False,
)

# Standard keybindings that allow Esc to cancel without raising unhandled KeyboardInterrupt
DEFAULT_ESCAPE_KEYBINDINGS: dict[str, list[dict[str, str]]] = {
    "skip": [{"key": "escape"}],
}


async def fuzzy_select_async(
    message: str,
    choices: Sequence[Any],
    default: Any = None,
    instruction: str = "(↑/↓ or type to search, Enter to select, Esc to cancel)",
    max_height: str | int = "70%",
    pointer: str = "❯ ",
) -> Optional[Any]:
    """Interactive fuzzy search selector with arrow navigation, real-time typing filter, and Esc abort."""
    try:
        result = await inquirer.fuzzy(
            message=message,
            choices=choices,
            default=default,
            instruction=instruction,
            style=XBOT_PROMPT_STYLE,
            pointer=pointer,
            max_height=max_height,
            keybindings=DEFAULT_ESCAPE_KEYBINDINGS,
            raise_keyboard_interrupt=False,
        ).execute_async()
        return result
    except (KeyboardInterrupt, EOFError):
        return None


async def select_async(
    message: str,
    choices: Sequence[Any],
    default: Any = None,
    instruction: str = "(Use ↑/↓ arrow keys, Enter to select, Esc to cancel)",
    max_height: str | int = "70%",
    pointer: str = "❯ ",
) -> Optional[Any]:
    """Interactive arrow-key selector with Esc abort."""
    try:
        result = await inquirer.select(
            message=message,
            choices=choices,
            default=default,
            instruction=instruction,
            style=XBOT_PROMPT_STYLE,
            pointer=pointer,
            max_height=max_height,
            keybindings=DEFAULT_ESCAPE_KEYBINDINGS,
            raise_keyboard_interrupt=False,
        ).execute_async()
        return result
    except (KeyboardInterrupt, EOFError):
        return None


async def confirm_async(
    message: str,
    default: bool = True,
    instruction: str = "(Y/n, Esc to cancel)",
) -> Optional[bool]:
    """Interactive confirmation prompt with Esc abort."""
    try:
        result = await inquirer.confirm(
            message=message,
            default=default,
            instruction=instruction,
            style=XBOT_PROMPT_STYLE,
            keybindings=DEFAULT_ESCAPE_KEYBINDINGS,
            raise_keyboard_interrupt=False,
        ).execute_async()
        return result
    except (KeyboardInterrupt, EOFError):
        return None


async def ask_async(
    message: str,
    default: str = "",
    instruction: str = "(Enter to submit, Esc to cancel)",
) -> Optional[str]:
    """Interactive text input prompt with Esc abort."""
    try:
        result = await inquirer.text(
            message=message,
            default=default,
            instruction=instruction,
            style=XBOT_PROMPT_STYLE,
            keybindings=DEFAULT_ESCAPE_KEYBINDINGS,
            raise_keyboard_interrupt=False,
        ).execute_async()
        return result
    except (KeyboardInterrupt, EOFError):
        return None
