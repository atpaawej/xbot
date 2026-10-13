"""Interactive Rich TUI Application for xbot with pipe prompt, multi-line, and sessions."""

from __future__ import annotations

import asyncio
import os
import select
import sys
from typing import Optional

IS_WINDOWS = sys.platform.startswith("win")
if not IS_WINDOWS:
    try:
        import termios
        import tty
    except ImportError:  # pragma: no cover
        termios = None
        tty = None
else:
    try:
        import msvcrt
    except ImportError:  # pragma: no cover
        msvcrt = None


def poll_stdin_escape(fd: int) -> bool:
    """Non-blocking check if Escape was pressed on the given file descriptor."""
    try:
        r, _, _ = select.select([fd], [], [], 0.05)
        if r:
            byte = os.read(fd, 1)
            if byte == b"\x1b":
                # Check if this is part of an escape sequence (like arrow keys \x1b[A)
                more, _, _ = select.select([fd], [], [], 0.03)
                if more:
                    os.read(fd, 32)  # Drain escape sequence
                    return False
                return True
    except Exception:
        pass
    return False


async def listen_for_escape(cancel_event: asyncio.Event) -> None:
    """Listen for the Escape key in terminal raw/cbreak mode during active streaming turns."""
    try:
        if not sys.stdin.isatty():
            return
    except Exception:
        return

    loop = asyncio.get_running_loop()

    if IS_WINDOWS:
        def _check_win_esc() -> bool:
            if msvcrt and msvcrt.kbhit():
                ch = msvcrt.getch()
                return ch == b"\x1b"
            return False

        while not cancel_event.is_set():
            is_esc = await loop.run_in_executor(None, _check_win_esc)
            if is_esc:
                cancel_event.set()
                break
            await asyncio.sleep(0.02)
    else:
        if termios is None or tty is None:
            return

        try:
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
        except Exception:
            return

        try:
            tty.setcbreak(fd)
            while not cancel_event.is_set():
                is_esc = await loop.run_in_executor(None, poll_stdin_escape, fd)
                if is_esc:
                    cancel_event.set()
                    break
                await asyncio.sleep(0.01)
        finally:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
            except Exception:
                pass

import time
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
from xbot.tui.cards import (
    ThinkingDrawer,
    ToolCardState,
    ToolState,
    render_tool_card,
)
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
        self.console.print("[bold cyan]🤖 xbot[/bold cyan] [dim]thinking... (press Esc to cancel)[/dim]")

        accumulated_text = ""
        status: Optional[Status] = None
        live_markdown: Optional[Live] = None
        thinking_drawer: Optional[ThinkingDrawer] = None
        live_thinking: Optional[Live] = None
        active_tool_card: Optional[ToolCardState] = None
        live_tool: Optional[Live] = None

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

        def finalize_thinking():
            nonlocal thinking_drawer, live_thinking
            if live_thinking and live_thinking.is_started:
                live_thinking.stop()
                live_thinking = None
            if thinking_drawer:
                thinking_drawer.finalize()
                self.console.print(thinking_drawer.render_collapsed())
                thinking_drawer = None

        def stop_tool():
            nonlocal active_tool_card, live_tool
            if live_tool and live_tool.is_started:
                live_tool.stop()
                live_tool = None

        cancel_event = asyncio.Event()
        listener_task = asyncio.create_task(listen_for_escape(cancel_event))

        async def _consume_stream():
            nonlocal accumulated_text, status, live_markdown, thinking_drawer, live_thinking, active_tool_card, live_tool
            status = self.console.status("[bold cyan]Connecting to model...[/bold cyan]", spinner="dots")
            status.start()

            async for event in self.agent_manager.stream_turn(user_input):
                if cancel_event.is_set():
                    break

                if isinstance(event, AgentReasoningDelta):
                    stop_status()
                    if thinking_drawer is None:
                        thinking_drawer = ThinkingDrawer()
                        thinking_drawer.append(event.chunk)
                        live_thinking = Live(
                            thinking_drawer.render_live(),
                            console=self.console,
                            refresh_per_second=10,
                            transient=True,
                        )
                        live_thinking.start()
                    else:
                        thinking_drawer.append(event.chunk)
                        if live_thinking and live_thinking.is_started:
                            live_thinking.update(thinking_drawer.render_live())

                elif isinstance(event, AgentTextDelta):
                    finalize_thinking()
                    stop_status()
                    stop_tool()
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
                    finalize_thinking()
                    stop_live()
                    stop_status()
                    stop_tool()

                    active_tool_card = ToolCardState(
                        tool_name=event.tool_name,
                        tool_call_id=event.tool_call_id,
                        state=ToolState.RUNNING,
                    )
                    live_tool = Live(
                        render_tool_card(active_tool_card),
                        console=self.console,
                        refresh_per_second=8,
                        transient=True,
                    )
                    live_tool.start()

                elif isinstance(event, AgentToolEnd):
                    finalize_thinking()
                    stop_live()
                    stop_status()

                    if active_tool_card and active_tool_card.tool_call_id == event.tool_call_id:
                        active_tool_card.args = event.args
                        if live_tool and live_tool.is_started:
                            live_tool.update(render_tool_card(active_tool_card))
                    else:
                        stop_tool()
                        active_tool_card = ToolCardState(
                            tool_name=event.tool_name,
                            tool_call_id=event.tool_call_id,
                            args=event.args,
                            state=ToolState.RUNNING,
                        )
                        live_tool = Live(
                            render_tool_card(active_tool_card),
                            console=self.console,
                            refresh_per_second=8,
                            transient=True,
                        )
                        live_tool.start()

                elif isinstance(event, AgentToolResult):
                    finalize_thinking()
                    stop_live()
                    stop_status()
                    stop_tool()

                    if active_tool_card and active_tool_card.tool_call_id == event.tool_call_id:
                        active_tool_card.end_time = time.time()
                        active_tool_card.state = (
                            ToolState.ERROR if event.is_error else ToolState.SUCCESS
                        )
                        active_tool_card.result = event.result
                        active_tool_card.is_error = event.is_error
                        self.console.print(render_tool_card(active_tool_card))
                        active_tool_card = None
                    else:
                        card = ToolCardState(
                            tool_name=event.tool_name,
                            tool_call_id=event.tool_call_id,
                            state=ToolState.ERROR if event.is_error else ToolState.SUCCESS,
                            result=event.result,
                            is_error=event.is_error,
                            end_time=time.time(),
                        )
                        self.console.print(render_tool_card(card))

                    # Reset text accumulator for post-tool synthesis
                    accumulated_text = ""
                    status = self.console.status("[bold cyan]Synthesizing response...[/bold cyan]", spinner="dots")
                    status.start()

                elif isinstance(event, AgentError):
                    finalize_thinking()
                    stop_live()
                    stop_status()
                    stop_tool()
                    self.console.print()
                    self.console.print(
                        Panel(
                            Text(event.error_message, style="bold red"),
                            title="[bold red]Error[/bold red]",
                            border_style="red",
                        )
                    )

            finalize_thinking()
            stop_status()
            stop_live()
            stop_tool()

        try:
            stream_task = asyncio.create_task(_consume_stream())
            cancel_waiter = asyncio.create_task(cancel_event.wait())

            done, pending = await asyncio.wait(
                [stream_task, cancel_waiter],
                return_when=asyncio.FIRST_COMPLETED,
            )

            if cancel_event.is_set():
                if not stream_task.done():
                    stream_task.cancel()
                    try:
                        await stream_task
                    except (asyncio.CancelledError, Exception):
                        pass

                finalize_thinking()
                stop_status()
                stop_live()
                stop_tool()
                self.console.print("\n[bold yellow]⏹ Interrupted by user (Esc pressed).[/bold yellow]")

                # Retain partial conversation in session history
                from ai import assistant_message
                msg_content = (
                    f"{accumulated_text}\n\n[Interrupted by user]"
                    if accumulated_text
                    else "[Interrupted by user]"
                )
                self.agent_manager.messages.append(assistant_message(msg_content))
                if self.agent_manager.current_session:
                    self.agent_manager.session_manager.save_messages(
                        self.agent_manager.current_session.id,
                        self.agent_manager.messages,
                    )
            else:
                if not cancel_waiter.done():
                    cancel_waiter.cancel()
                if stream_task.exception():
                    raise stream_task.exception()

        except asyncio.CancelledError:
            finalize_thinking()
            stop_status()
            stop_live()
            stop_tool()
            self.console.print("\n[dim]Action cancelled.[/dim]")
        except Exception as exc:
            finalize_thinking()
            stop_status()
            stop_live()
            stop_tool()
            self.console.print(f"\n[bold red]Execution error:[/bold red] {exc}\n")
        finally:
            if not listener_task.done():
                listener_task.cancel()
                try:
                    await listener_task
                except (asyncio.CancelledError, Exception):
                    pass
            stop_status()
            stop_live()

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
