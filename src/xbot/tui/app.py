"""Interactive Rich TUI Application for xbot."""

from __future__ import annotations

import asyncio
import sys
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console
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
from xbot.config import get_config
from xbot.tui.components import (
    create_banner,
    create_config_table,
    create_help_table,
    create_tool_call_panel,
    create_tool_result_panel,
    create_tools_table,
)
from xbot.tui.formatting import format_markdown

COMMANDS = ["/help", "/clear", "/config", "/tools", "/history", "/reset", "/exit", "/quit"]


class XBotTUI:
    """Rich-based Terminal User Interface for xbot agent."""

    def __init__(self, agent_manager: Optional[AgentManager] = None) -> None:
        self.console = Console()
        self.agent_manager = agent_manager or AgentManager()
        self.completer = WordCompleter(COMMANDS, ignore_case=True)
        self.session: PromptSession[str] = PromptSession(
            history=InMemoryHistory(),
            completer=self.completer,
        )

    def print_banner(self) -> None:
        """Display startup banner."""
        self.console.print(create_banner(self.agent_manager.config))
        self.console.print()

    def handle_command(self, cmd: str) -> bool:
        """Handle slash command. Returns True to continue, False to exit."""
        cmd = cmd.strip().lower()

        if cmd in ("/exit", "/quit"):
            self.console.print("\n[bold yellow]👋 Farewell from xbot![/bold yellow]\n")
            return False

        if cmd == "/help":
            self.console.print(create_help_table())
            self.console.print()
            return True

        if cmd == "/clear":
            self.console.clear()
            self.print_banner()
            return True

        if cmd == "/config":
            self.console.print(create_config_table(self.agent_manager.config))
            self.console.print()
            return True

        if cmd == "/tools":
            self.console.print(create_tools_table())
            self.console.print()
            return True

        if cmd == "/history":
            total_turns = self.agent_manager.turn_count
            total_msgs = len(self.agent_manager.messages)
            summary = Panel(
                f"[bold cyan]User Turns:[/bold cyan] {total_turns}\n"
                f"[bold cyan]Total Trace Messages:[/bold cyan] {total_msgs}\n"
                f"[bold cyan]Workspace:[/bold cyan] {self.agent_manager.config.workspace_dir}",
                title="[bold yellow]Conversation Statistics[/bold yellow]",
                border_style="yellow",
            )
            self.console.print(summary)
            self.console.print()
            return True

        if cmd == "/reset":
            self.agent_manager.reset()
            self.console.print("[bold green]✓ Conversation memory reset to initial state.[/bold green]\n")
            return True

        self.console.print(f"[bold red]Unknown command:[/bold red] {cmd}. Type [cyan]/help[/cyan] for assistance.\n")
        return True

    async def run_turn(self, user_input: str) -> None:
        """Execute one conversational turn with streaming output and tool visualization."""
        self.console.print()
        # Visual divider before response
        self.console.print("[bold cyan]🤖 xbot[/bold cyan] [dim]thinking...[/dim]")

        accumulated_text = ""
        accumulated_reasoning = ""
        status: Optional[Status] = None
        has_printed_text = False

        try:
            status = self.console.status("[bold cyan]Connecting to model...[/bold cyan]", spinner="dots")
            status.start()

            async for event in self.agent_manager.stream_turn(user_input):
                if isinstance(event, AgentReasoningDelta):
                    accumulated_reasoning += event.chunk
                    # Keep spinner updated with reasoning preview
                    if status and status._live.is_started:
                        preview = accumulated_reasoning[-40:].replace("\n", " ")
                        status.update(f"[bold magenta]Reasoning: [dim]{preview}[/dim][/bold magenta]")

                elif isinstance(event, AgentTextDelta):
                    if status and status._live.is_started:
                        status.stop()

                    if not has_printed_text:
                        has_printed_text = True

                    accumulated_text += event.chunk
                    # Print token stream directly to console
                    self.console.print(event.chunk, end="", highlight=False)
                    sys.stdout.flush()

                elif isinstance(event, AgentToolStart):
                    if status and status._live.is_started:
                        status.stop()
                    # Ensure newline if text was streaming
                    if has_printed_text:
                        self.console.print()
                        has_printed_text = False

                    status = self.console.status(
                        f"[bold yellow]Invoking {event.tool_name}...[/bold yellow]",
                        spinner="bouncingBar",
                    )
                    status.start()

                elif isinstance(event, AgentToolEnd):
                    if status and status._live.is_started:
                        status.stop()
                    self.console.print(create_tool_call_panel(event.tool_name, event.args))
                    status = self.console.status(
                        f"[bold yellow]Running {event.tool_name}...[/bold yellow]",
                        spinner="dots",
                    )
                    status.start()

                elif isinstance(event, AgentToolResult):
                    if status and status._live.is_started:
                        status.stop()
                    self.console.print(
                        create_tool_result_panel(
                            event.tool_name, event.result, is_error=event.is_error
                        )
                    )
                    # Resume status for next turn / processing
                    status = self.console.status("[bold cyan]Analyzing results...[/bold cyan]", spinner="dots")
                    status.start()

                elif isinstance(event, AgentError):
                    if status and status._live.is_started:
                        status.stop()
                    self.console.print()
                    self.console.print(
                        Panel(
                            Text(event.error_message, style="bold red"),
                            title="[bold red]Error[/bold red]",
                            border_style="red",
                        )
                    )

            if status and status._live.is_started:
                status.stop()

            # Final newline if text was output
            if has_printed_text:
                self.console.print()

        except Exception as exc:
            if status and status._live.is_started:
                status.stop()
            self.console.print(f"\n[bold red]Execution error:[/bold red] {exc}\n")

        self.console.print()

    async def start(self) -> None:
        """Start the interactive REPL loop."""
        self.print_banner()

        while True:
            try:
                # Use prompt_toolkit for interactive input with history & auto-complete
                user_input = await self.session.prompt_async(
                    HTML("<b><ansicyan>xbot</ansicyan></b><ansigreen>❯</ansigreen> ")
                )
                user_input = user_input.strip()

                if not user_input:
                    continue

                # Handle slash commands
                if user_input.startswith("/"):
                    should_continue = self.handle_command(user_input)
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
