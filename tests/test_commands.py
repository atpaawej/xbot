"""Unit and integration tests for the slash command system and InquirerPy UI primitives."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from prompt_toolkit.document import Document
from rich.console import Console

from xbot.commands import (
    BaseCommand,
    CommandContext,
    CommandRegistry,
    CommandResult,
    SlashCompleter,
    get_default_registry,
)
from xbot.commands.builtin.info import ConfigCommand, HelpCommand, ToolsCommand
from xbot.commands.builtin.resume import ResumeCommand
from xbot.commands.builtin.session import ClearCommand, NewCommand
from xbot.commands.builtin.system import ExitCommand
from xbot.sessions import SessionSummary


class DummyCommand(BaseCommand):
    name = "dummy"
    aliases = ["dum", "d"]
    description = "Dummy test command"
    usage = "/dummy [arg]"
    category = "Testing"

    async def execute(self, context: CommandContext) -> CommandResult:
        context.console.print(f"Executed with args: {context.args}")
        return CommandResult(handled=True)


@pytest.fixture
def mock_agent_manager():
    mgr = MagicMock()
    mgr.config = MagicMock()
    mgr.config.base_url = "https://api.openai.com/v1"
    mgr.config.model_id = "gpt-4o"
    mgr.config.masked_api_key = "sk-***"
    mgr.config.masked_tinyfish_key = "tf-***"
    mgr.config.is_tinyfish_configured = False
    mgr.config.workspace_dir = "/tmp"
    mgr.config.bash_timeout = 30
    mgr.config.temperature = 0.0
    mgr.config.loaded_env_files = []

    curr_session = MagicMock()
    curr_session.title = "Current Session"
    curr_session.id = "curr_123"
    mgr.current_session = curr_session

    dummy_sessions = [
        SessionSummary(
            id="sess_001",
            title="Setup React App",
            created_at="2026-10-13T10:00:00",
            updated_at="2026-10-13T10:30:00",
            model_id="gpt-4o",
            project_name="web-proj",
        ),
        SessionSummary(
            id="sess_002",
            title="Fix API Auth Bug",
            created_at="2026-10-13T11:00:00",
            updated_at="2026-10-13T11:45:00",
            model_id="gpt-4o",
            project_name="api-proj",
        ),
    ]

    session_mgr = MagicMock()
    session_mgr.active_project = MagicMock(name="web-proj")
    session_mgr.active_project.name = "web-proj"
    session_mgr.list_sessions.return_value = dummy_sessions
    mgr.session_manager = session_mgr
    mgr.load_session.return_value = True

    return mgr


@pytest.fixture
def console():
    return Console(record=True, width=100)


def test_command_registry_registration():
    reg = CommandRegistry()
    cmd = DummyCommand()
    reg.register(cmd)

    assert reg.get("dummy") is cmd
    assert reg.get("dum") is cmd
    assert reg.get("D") is cmd
    assert reg.get("/dummy") is cmd
    assert reg.get("/DUM") is cmd
    assert reg.get("nonexistent") is None
    assert len(reg.all_commands()) == 1


def test_command_registry_find():
    reg = CommandRegistry()
    reg.register(DummyCommand())
    reg.register(ResumeCommand())

    # Search by prefix or substring
    matches = reg.find("dum")
    assert len(matches) == 1
    assert matches[0].name == "dummy"

    # Search by alias
    matches_alias = reg.find("history")
    assert len(matches_alias) == 1
    assert matches_alias[0].name == "resume"

    # Empty search returns all
    assert len(reg.find("")) == 2


async def test_command_registry_dispatch(console, mock_agent_manager):
    reg = CommandRegistry()
    reg.register(DummyCommand())

    # Successful dispatch
    result = await reg.dispatch("/dummy foo bar", console, mock_agent_manager)
    assert result.handled is True
    assert "Executed with args: ['foo', 'bar']" in console.export_text()

    # Unknown command dispatch
    result_unknown = await reg.dispatch("/unknown_command", console, mock_agent_manager)
    assert result_unknown.handled is False
    assert "Unknown command" in console.export_text()

    # Non-slash input dispatch
    result_non_slash = await reg.dispatch("just a normal message", console, mock_agent_manager)
    assert result_non_slash.handled is False


def test_slash_completer():
    reg = CommandRegistry()
    reg.register(ResumeCommand())
    reg.register(NewCommand())
    reg.register(ExitCommand())

    completer = SlashCompleter(reg)

    # Regular typing should yield NO completions
    doc_text = Document("Please help me fix this bug")
    assert list(completer.get_completions(doc_text, None)) == []

    # Space after command should yield NO completions
    doc_space = Document("/resume ")
    assert list(completer.get_completions(doc_space, None)) == []

    # Triggering on '/' yields all registered commands
    doc_slash = Document("/")
    comps = list(completer.get_completions(doc_slash, None))
    comp_names = [c.text for c in comps]
    assert "/resume" in comp_names
    assert "/new" in comp_names
    assert "/exit" in comp_names

    # Prefix filtering on '/res'
    doc_res = Document("/res")
    comps_res = list(completer.get_completions(doc_res, None))
    res_texts = [c.text for c in comps_res]
    assert "/resume" in res_texts
    # Check that metadata description is provided
    resume_comp = next(c for c in comps_res if c.text == "/resume")
    assert "Browse and resume" in resume_comp.display_meta_text

    # Alias matching: '/hist' matches '/history'
    doc_hist = Document("/hist")
    comps_hist = list(completer.get_completions(doc_hist, None))
    assert any(c.text == "/history" for c in comps_hist)


async def test_builtin_resume_command_direct_index(console, mock_agent_manager):
    cmd = ResumeCommand()
    context = CommandContext.create(console, mock_agent_manager, raw_args="1")

    res = await cmd.execute(context)
    assert res.handled is True
    mock_agent_manager.load_session.assert_called_with("sess_001")
    assert "Loaded session" in console.export_text()


async def test_builtin_resume_command_direct_id(console, mock_agent_manager):
    cmd = ResumeCommand()
    context = CommandContext.create(console, mock_agent_manager, raw_args="sess_002")

    res = await cmd.execute(context)
    assert res.handled is True
    mock_agent_manager.load_session.assert_called_with("sess_002")
    assert "Loaded session" in console.export_text()


async def test_builtin_resume_command_invalid_index(console, mock_agent_manager):
    cmd = ResumeCommand()
    context = CommandContext.create(console, mock_agent_manager, raw_args="99")

    res = await cmd.execute(context)
    assert res.handled is True
    assert "Invalid session index #99" in console.export_text()


async def test_builtin_resume_command_interactive(console, mock_agent_manager):
    cmd = ResumeCommand()
    context = CommandContext.create(console, mock_agent_manager, raw_args="")

    # Mock interactive fuzzy selection selecting sess_002
    with patch.object(context, "fuzzy_select", new=AsyncMock(return_value="sess_002")) as mock_select:
        res = await cmd.execute(context)
        assert res.handled is True
        mock_select.assert_called_once()
        mock_agent_manager.load_session.assert_called_with("sess_002")
        assert "Loaded session" in console.export_text()


async def test_builtin_resume_command_interactive_cancelled(console, mock_agent_manager):
    cmd = ResumeCommand()
    context = CommandContext.create(console, mock_agent_manager, raw_args="")

    # Mock user pressing Escape (returns None)
    with patch.object(context, "fuzzy_select", new=AsyncMock(return_value=None)) as mock_select:
        res = await cmd.execute(context)
        assert res.handled is True
        mock_select.assert_called_once()
        mock_agent_manager.load_session.assert_not_called()
        assert "Session selection cancelled" in console.export_text()


async def test_builtin_resume_command_all_flag(console, mock_agent_manager):
    cmd = ResumeCommand()
    context = CommandContext.create(console, mock_agent_manager, raw_args="all")

    with patch.object(context, "fuzzy_select", new=AsyncMock(return_value=None)):
        await cmd.execute(context)
        mock_agent_manager.session_manager.list_sessions.assert_called_with(
            all_projects=True, limit=50
        )


async def test_builtin_new_command(console, mock_agent_manager):
    cmd = NewCommand()
    context = CommandContext.create(console, mock_agent_manager)

    res = await cmd.execute(context)
    assert res.handled is True
    mock_agent_manager.reset.assert_called_once()
    assert "Started a new session" in console.export_text()


async def test_builtin_clear_command(console, mock_agent_manager):
    cmd = ClearCommand()
    tui_mock = MagicMock()
    context = CommandContext.create(console, mock_agent_manager, tui=tui_mock)

    res = await cmd.execute(context)
    assert res.handled is True
    tui_mock.print_banner.assert_called_once()


async def test_builtin_exit_command(console, mock_agent_manager):
    cmd = ExitCommand()
    context = CommandContext.create(console, mock_agent_manager)

    res = await cmd.execute(context)
    assert res.handled is True
    assert res.should_exit is True
    assert "Farewell from xbot" in console.export_text()


async def test_builtin_info_commands(console, mock_agent_manager):
    help_cmd = HelpCommand()
    config_cmd = ConfigCommand()
    tools_cmd = ToolsCommand()

    ctx = CommandContext.create(console, mock_agent_manager)

    # /help
    res_help = await help_cmd.execute(ctx)
    assert res_help.handled is True
    assert "Slash Commands" in console.export_text()

    # /config
    res_cfg = await config_cmd.execute(ctx)
    assert res_cfg.handled is True
    assert "Current Configuration" in console.export_text()

    # /tools
    res_tools = await tools_cmd.execute(ctx)
    assert res_tools.handled is True
    assert "Agent Registered Tools" in console.export_text()


def test_get_default_registry():
    reg = get_default_registry()
    names = [c.name for c in reg.all_commands()]
    assert "resume" in names
    assert "new" in names
    assert "clear" in names
    assert "help" in names
    assert "config" in names
    assert "tools" in names
    assert "exit" in names

    # Aliases
    assert reg.get("history") is reg.get("resume")
    assert reg.get("reset") is reg.get("new")
    assert reg.get("cls") is reg.get("clear")
    assert reg.get("quit") is reg.get("exit")
    assert reg.get("q") is reg.get("exit")
    assert reg.get("settings") is reg.get("config")
    assert reg.get("?") is reg.get("help")


async def test_command_context_ui_helpers(console, mock_agent_manager):
    ctx = CommandContext.create(console, mock_agent_manager)

    with patch("xbot.commands.base.fuzzy_select_async", new=AsyncMock(return_value="res_fuzzy")) as mock_f:
        res = await ctx.fuzzy_select("Choose:", ["a", "b"])
        assert res == "res_fuzzy"
        mock_f.assert_called_once()

    with patch("xbot.commands.base.select_async", new=AsyncMock(return_value="res_select")) as mock_s:
        res = await ctx.select("Choose:", ["a", "b"])
        assert res == "res_select"
        mock_s.assert_called_once()

    with patch("xbot.commands.base.confirm_async", new=AsyncMock(return_value=True)) as mock_c:
        res = await ctx.confirm("Sure?")
        assert res is True
        mock_c.assert_called_once()

    with patch("xbot.commands.base.ask_async", new=AsyncMock(return_value="my text")) as mock_a:
        res = await ctx.ask("Prompt:")
        assert res == "my text"
        mock_a.assert_called_once()


async def test_ui_prompts_cancellation():
    from xbot.commands.ui.prompts import (
        ask_async,
        confirm_async,
        fuzzy_select_async,
        select_async,
    )

    with patch("xbot.commands.ui.prompts.inquirer.fuzzy") as mock_fuzzy:
        mock_fuzzy.side_effect = KeyboardInterrupt
        res = await fuzzy_select_async("Test", ["a"])
        assert res is None

    with patch("xbot.commands.ui.prompts.inquirer.select") as mock_select:
        mock_select.side_effect = KeyboardInterrupt
        res = await select_async("Test", ["a"])
        assert res is None

    with patch("xbot.commands.ui.prompts.inquirer.confirm") as mock_confirm:
        mock_confirm.side_effect = KeyboardInterrupt
        res = await confirm_async("Test")
        assert res is None

    with patch("xbot.commands.ui.prompts.inquirer.text") as mock_text:
        mock_text.side_effect = KeyboardInterrupt
        res = await ask_async("Test")
        assert res is None
