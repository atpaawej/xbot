"""Built-in /model command to view, search, and switch active model across authenticated providers."""

from __future__ import annotations

from typing import Optional

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.panel import Panel
from rich.table import Table

from xbot.commands.base import BaseCommand, CommandContext, CommandResult
from xbot.providers.auth import get_auth_store
from xbot.providers.manager import get_provider_manager
from xbot.providers.models import ModelInfo, canonical_model_id, parse_model_ref
from xbot.providers.registry import get_provider_registry


class ModelCommand(BaseCommand):
    """View, search, or switch active LLM model across all authenticated providers."""

    name = "model"
    aliases = ["models", "m"]
    description = "View or switch active LLM model (strict provider/model_id format)"
    usage = "/model [provider/model_id] [--refresh]"
    category = "Config"

    async def execute(self, context: CommandContext) -> Optional[CommandResult]:
        auth_store = get_auth_store()
        provider_manager = get_provider_manager()
        registry = get_provider_registry()
        console = context.console

        raw_args = context.raw_args.strip()
        force_refresh = False

        if "--refresh" in raw_args:
            force_refresh = True
            raw_args = raw_args.replace("--refresh", "").strip()

        # 1. Direct model switch if model argument is provided
        if raw_args:
            # Enforce strict canonical provider/model_id format
            try:
                provider_id, model_id = parse_model_ref(raw_args)
            except ValueError as err:
                console.print(
                    Panel(
                        f"[bold red]Invalid Model Format[/bold red]\n\n"
                        f"{err}\n\n"
                        "[dim]Examples: 'anthropic/claude-3-7-sonnet-20250219', 'openai/gpt-4o', "
                        "'deepseek/deepseek-reasoner', 'groq/llama-3.3-70b-versatile'[/dim]",
                        title="❌ Model Error",
                        border_style="red",
                    )
                )
                return CommandResult(handled=True)

            canonical_model = canonical_model_id(provider_id, model_id)

            # Check authentication status
            authenticated = auth_store.get_authenticated_providers()
            if provider_id not in authenticated:
                console.print(
                    f"[bold yellow]Warning:[/bold yellow] Provider '{provider_id}' is not yet authenticated.\n"
                    f"Run [cyan]/login {provider_id}[/cyan] to configure your API key."
                )

            # Switch active model
            provider_manager.switch_model(canonical_model, persist=True)
            if hasattr(context.agent_manager, "switch_model"):
                context.agent_manager.switch_model(canonical_model)

            console.print(
                Panel(
                    f"Active model successfully switched to: [bold bright_cyan]{canonical_model}[/bold bright_cyan]\n"
                    f"Provider: [bold green]{provider_id}[/bold green]",
                    title="✓ Model Switched",
                    border_style="green",
                )
            )
            return CommandResult(handled=True)

        # 2. Interactive Fuzzy Picker across all authenticated providers
        authenticated = auth_store.get_authenticated_providers()
        if not authenticated:
            console.print(
                Panel(
                    "[bold yellow]No providers currently authenticated.[/bold yellow]\n\n"
                    "Run [cyan]/login[/cyan] to connect your OpenAI, Anthropic, Gemini, Groq, "
                    "DeepSeek, or local Ollama provider.",
                    title="⚠️ No Authenticated Providers",
                    border_style="yellow",
                )
            )
            return CommandResult(handled=True)

        refresh_msg = " [cyan](Refreshing catalogs from endpoints...)[/cyan]" if force_refresh else ""
        console.print(f"[dim]Loading models from authenticated providers ({', '.join(authenticated)})...{refresh_msg}[/dim]")

        all_models = await provider_manager.list_available_models(force_refresh=force_refresh)

        if not all_models:
            console.print(
                "[bold red]No models could be loaded from authenticated providers.[/bold red]\n"
                "Please check your network connection or run [cyan]/login[/cyan] to re-authenticate."
            )
            return CommandResult(handled=True)

        # Build fuzzy choices
        choices: list[Choice] = []
        active_model = provider_manager.active_model

        for m in all_models:
            specs: list[str] = []
            if m.context_window:
                ctx_k = m.context_window // 1000
                specs.append(f"{ctx_k}k ctx")
            if m.supports_reasoning:
                specs.append("Reasoning")
            if m.supports_vision:
                specs.append("Vision")

            spec_str = f" [dim]({', '.join(specs)})[/dim]" if specs else ""
            is_active = " [bold bright_green]● (active)[/bold bright_green]" if m.full_id == active_model else ""
            display = f"{m.full_id}{spec_str}{is_active}"

            choices.append(Choice(value=m.full_id, name=display))

        try:
            chosen = await inquirer.fuzzy(
                message="Search & select LLM model (type to filter):",
                choices=choices,
                default=active_model,
            ).execute_async()
        except (KeyboardInterrupt, Exception):
            console.print("\n[yellow]Model selection cancelled.[/yellow]\n")
            return CommandResult(handled=True)

        if not chosen:
            return CommandResult(handled=True)

        # Switch model in provider_manager and agent_manager
        provider_manager.switch_model(chosen, persist=True)
        if hasattr(context.agent_manager, "switch_model"):
            context.agent_manager.switch_model(chosen)

        provider_id, _ = parse_model_ref(chosen)
        console.print(
            Panel(
                f"Active model switched to: [bold bright_cyan]{chosen}[/bold bright_cyan]\n"
                f"Provider: [bold green]{provider_id}[/bold green]",
                title="✓ Model Activated",
                border_style="green",
            )
        )
        return CommandResult(handled=True)
