"""Interactive Rich TUI Application for xbot with pipe prompt, multi-line, and sessions."""

from __future__ import annotations

import asyncio
import sys
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.status import Status
from rich.text import Text

from xbot.agent import (
    AgentError,
    AgentManager,
    AgentReasoningDelta,
    AgentTextDelta,
    AgentToolEnd,
    AgentToolResult,
    AgentToolStart,
)
from xbot.commands import SlashCompleter, get_default_registry
from xbot.config import get_config
from xbot.tui.components import (
    create_banner,
    create_config_table,
    create_help_table,
    create_session_list_panel,
    create_tool_call_panel,
    create_tool_result_panel,
    create_tools_table,
)
from xbot.tui.formatting import format_markdown

COMMANDS = ["/help", "/resume", "/history", "/new", "/clear", "/config", "/tools", "/exit", "/quit"]


class XBotTUI:
    """Rich-based Terminal User Interface for xbot agent."""

    def __init__(self, agent_manager: Optional[AgentManager] = None) -> None:
        self.console = Console()
        self.agent_manager = agent_manager or AgentManager()
        self.command_registry = get_default_registry()
        self.completer = SlashCompleter(self.command_registry)

        # Keybindings: Enter submits, Alt+Enter inserts newline, Escape cancels completion menu
        self.kb = KeyBindings()

        @self.kb.add("enter")
        def _handle_enter(event):
            event.current_buffer.validate_and_handle()

        @self.kb.add("escape", "enter")
        def _handle_alt_enter(event):
            event.current_buffer.insert_text("\n")

        @self.kb.add("escape")
        def _handle_escape(event):
            if event.current_buffer.complete_state:
                event.current_buffer.cancel_completion()

        self.style = Style.from_dict({
            "frame.border": "#00aaaa",
            "completion-menu": "bg:#111111 #ffffff",
            "completion-menu.completion": "bg:#222222 #ffffff",
            "completion-menu.completion.current": "bg:#00aaaa #000000 bold",
            "completion-menu.meta.completion": "bg:#1e1e1e #888888",
            "completion-menu.meta.completion.current": "bg:#007777 #ffffff",
            "scrollbar.background": "bg:#222222",
            "scrollbar.button": "bg:#00aaaa",
        })

        self.session: PromptSession[str] = PromptSession(
            history=InMemoryHistory(),
            completer=self.completer,
            complete_while_typing=True,
            key_bindings=self.kb,
            multiline=True,
            show_frame=True,
            style=self.style,
            prompt_continuation=self._prompt_continuation,
        )

    def _prompt_continuation(self, width: int, line_number: int, is_soft_wrap: bool) -> HTML:
        """Continuation prompt for multi-line inputs: maintains the vertical pipe."""
        return HTML(" <ansicyan><b>| </b></ansicyan>")

    def print_banner(self) -> None:
        """Display startup banner with active session title."""
        curr_title = (
            self.agent_manager.current_session.title
            if self.agent_manager.current_session
            else "New Session"
        )
        self.console.print(create_banner(self.agent_manager.config, session_title=curr_title))
        self.console.print()

    async def handle_history(self, all_projects: bool = False) -> None:
        """Backwards-compatible delegation to the /resume slash command."""
        cmd = "/resume all" if all_projects else "/resume"
        await self.handle_command(cmd)

    async def handle_command(self, cmd: str) -> bool:
        """Handle slash command via the CommandRegistry. Returns True to continue, False to exit."""
        result = await self.command_registry.dispatch(
            cmd,
            console=self.console,
            agent_manager=self.agent_manager,
            tui=self,
        )
        return not result.should_exit

    async def run_turn(self, user_input: str) -> None:
        """Execute one conversational turn with streaming output, Markdown rendering, and tool cards."""
        self.console.print()
        self.console.print("[bold cyan]🤖 xbot[/bold cyan] [dim]thinking...[/dim]")

        accumulated_text = ""
        accumulated_reasoning = ""
        status: Optional[Status] = None
        live_markdown: Optional[Live] = None

        def stop_status():
            nonlocal status
            if status and status._live.is_started:
                status.stop()
                status = None

        def stop_live():
            nonlocal live_markdown
            if live_markdown and live_markdown.is_started:
                live_markdown.stop()
                live_markdown = None

        try:
            status = self.console.status("[bold cyan]Connecting to model...[/bold cyan]", spinner="dots")
            status.start()

            async for event in self.agent_manager.stream_turn(user_input):
                if isinstance(event, AgentReasoningDelta):
                    accumulated_reasoning += event.chunk
                    if status and status._live.is_started:
                        preview = accumulated_reasoning[-40:].replace("\n", " ")
                        status.update(f"[bold magenta]Reasoning: [dim]{preview}[/dim][/bold magenta]")

                elif isinstance(event, AgentTextDelta):
                    stop_status()
                    accumulated_text += event.chunk

                    # Start or update Rich Live Markdown renderer
                    if live_markdown is None:
                        live_markdown = Live(
                            format_markdown(accumulated_text),
                            console=self.console,
                            refresh_per_second=15,
                        )
                        live_markdown.start()
                    else:
                        live_markdown.update(format_markdown(accumulated_text))

                elif isinstance(event, AgentToolStart):
                    stop_live()
                    stop_status()

                    status = self.console.status(
                        f"[bold yellow]Invoking {event.tool_name}...[/bold yellow]",
                        spinner="bouncingBar",
                    )
                    status.start()

                elif isinstance(event, AgentToolEnd):
                    stop_live()
                    stop_status()
                    self.console.print(create_tool_call_panel(event.tool_name, event.args))
                    status = self.console.status(
                        f"[bold yellow]Running {event.tool_name}...[/bold yellow]",
                        spinner="dots",
                    )
                    status.start()

                elif isinstance(event, AgentToolResult):
                    stop_live()
                    stop_status()
                    self.console.print(
                        create_tool_result_panel(
                            event.tool_name, event.result, is_error=event.is_error
                        )
                    )
                    # Reset text accumulator for post-tool synthesis
                    accumulated_text = ""
                    status = self.console.status("[bold cyan]Synthesizing response...[/bold cyan]", spinner="dots")
                    status.start()

                elif isinstance(event, AgentError):
                    stop_live()
                    stop_status()
                    self.console.print()
                    self.console.print(
                        Panel(
                            Text(event.error_message, style="bold red"),
                            title="[bold red]Error[/bold red]",
                            border_style="red",
                        )
                    )

            stop_status()
            stop_live()

        except Exception as exc:
            stop_status()
            stop_live()
            self.console.print(f"\n[bold red]Execution error:[/bold red] {exc}\n")

        self.console.print()

    async def start(self) -> None:
        """Start the interactive REPL loop with responsive container borders."""
        self.print_banner()

        while True:
            try:
                # Input prompt inside a tight, responsive border box with pipe prefix |
                user_input = await self.session.prompt_async(
                    HTML(" <ansicyan><b>| </b></ansicyan>")
                )

                user_input = user_input.strip()
                if not user_input:
                    continue

                # Handle slash commands
                if user_input.startswith("/"):
                    should_continue = await self.handle_command(user_input)
                    if not should_continue:
                        break
                    continue

                # Run agent turn
                await self.run_turn(user_input)

            except (KeyboardInterrupt, asyncio.CancelledError):
                self.console.print("\n[dim]Action cancelled.[/dim]\n")
                continue
            except EOFError:
                self.console.print("\n[bold yellow]👋 Exiting xbot.[/bold yellow]\n")
                break


def run_tui() -> None:
    """Synchronous launcher for the TUI."""
    tui = XBotTUI()
    try:
        asyncio.run(tui.start())
    except KeyboardInterrupt:
        pass
