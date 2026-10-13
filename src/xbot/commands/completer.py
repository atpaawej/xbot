"""Context-aware real-time completer for slash commands in prompt_toolkit."""

from __future__ import annotations

from typing import Iterable

from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

from xbot.commands.registry import CommandRegistry


class SlashCompleter(Completer):
    """Real-time completer that triggers only on '/' and yields commands with usage and descriptions."""

    def __init__(self, registry: CommandRegistry) -> None:
        self.registry = registry

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        text = document.text_before_cursor

        # Trigger completion only when the buffer starts with '/' and is still completing the command name
        if not text.startswith("/"):
            return

        # If user has typed a space after the command, do not re-suggest command names
        if " " in text:
            return

        query = text[1:].lower()

        # Collect unique suggestions (prioritizing primary names, then aliases if matching)
        seen_completions: set[str] = set()

        for cmd in self.registry.all_commands():
            cmd_name = cmd.name.lstrip("/").lower()
            aliases = [a.lstrip("/").lower() for a in cmd.aliases]

            # Check if primary name matches query
            if cmd_name.startswith(query) or (query and query in cmd_name):
                comp_text = f"/{cmd_name}"
                if comp_text not in seen_completions:
                    seen_completions.add(comp_text)
                    meta = cmd.description or cmd.usage or ""
                    yield Completion(
                        comp_text,
                        start_position=-len(text),
                        display=comp_text,
                        display_meta=meta,
                    )

            # Check aliases if query is not empty and matches
            if query:
                for alias in aliases:
                    if alias.startswith(query) or query in alias:
                        comp_text = f"/{alias}"
                        if comp_text not in seen_completions:
                            seen_completions.add(comp_text)
                            meta = f"Alias for /{cmd_name} — {cmd.description}"
                            yield Completion(
                                comp_text,
                                start_position=-len(text),
                                display=comp_text,
                                display_meta=meta,
                            )
