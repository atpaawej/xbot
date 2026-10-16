"""Built-in /login command for interactive multi-provider authentication and default model selection."""

from __future__ import annotations

from typing import Any, Optional

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.panel import Panel
from rich.table import Table

from xbot.commands.base import BaseCommand, CommandContext, CommandResult
from xbot.providers.auth import get_auth_store
from xbot.providers.fetcher import fetch_provider_models
from xbot.providers.models import canonical_model_id, parse_model_ref
from xbot.providers.registry import get_provider_registry


class LoginCommand(BaseCommand):
    """Authenticate with an LLM provider, validate credentials, and select default model."""

    name = "login"
    aliases = ["connect", "auth"]
    description = "Authenticate with an LLM provider and set its default model"
    usage = "/login [provider_name]"
    category = "Config"

    async def execute(self, context: CommandContext) -> Optional[CommandResult]:
        registry = get_provider_registry()
        auth_store = get_auth_store()
        console = context.console

        target_provider_id: Optional[str] = None
        raw_arg = context.raw_args.strip().lower()

        if raw_arg:
            profile = registry.get(raw_arg)
            if profile:
                target_provider_id = profile.id
            else:
                console.print(
                    f"[bold red]Unknown provider:[/bold red] '{raw_arg}'. "
                    "Run [cyan]/login[/cyan] without arguments to choose from the list.\n"
                )
                return CommandResult(handled=True)

        # 1. Interactive Provider Selection if not specified in arguments
        if not target_provider_id:
            choices: list[Choice] = []
            authenticated_providers = set(auth_store.get_authenticated_providers())

            for p in registry.all_providers():
                auth_indicator = " (Logged In)" if p.id in authenticated_providers else ""
                desc = f" — {p.description}" if p.description else ""
                display_name = f"{p.name}{auth_indicator}{desc}"
                choices.append(Choice(value=p.id, name=display_name))

            choices.append(Choice(value="custom", name="Custom OpenAI-Compatible Endpoint..."))

            try:
                selected = await inquirer.select(
                    message="Select LLM Provider to authenticate:",
                    choices=choices,
                    default=registry.all_providers()[0].id,
                ).execute_async()
            except (KeyboardInterrupt, Exception):
                console.print("\n[yellow]Login cancelled.[/yellow]\n")
                return CommandResult(handled=True)

            if not selected:
                return CommandResult(handled=True)

            target_provider_id = selected

        # 2. Handle Custom Provider vs Prebuilt
        custom_base_url: Optional[str] = None
        custom_provider_name: Optional[str] = None

        if target_provider_id == "custom":
            try:
                custom_provider_name = (
                    await inquirer.text(
                        message="Enter a unique name for this custom provider (e.g. 'my-vllm'):",
                        validate=lambda text: len(text.strip()) > 0,
                    ).execute_async()
                ).strip().lower()

                custom_base_url = (
                    await inquirer.text(
                        message="Enter Base URL (e.g. 'http://localhost:8000/v1'):",
                        validate=lambda text: text.strip().startswith("http"),
                    ).execute_async()
                ).strip()

                target_provider_id = custom_provider_name
            except (KeyboardInterrupt, Exception):
                console.print("\n[yellow]Login cancelled.[/yellow]\n")
                return CommandResult(handled=True)

        profile = registry.get(target_provider_id)
        provider_display_name = profile.name if profile else target_provider_id

        # 3. Prompt for API Key (masked)
        is_ollama = target_provider_id == "ollama"
        key_instruction = " (optional for local Ollama)" if is_ollama else ""

        try:
            api_key = await inquirer.secret(
                message=f"Enter API Key for {provider_display_name}{key_instruction}:",
            ).execute_async()
        except (KeyboardInterrupt, Exception):
            console.print("\n[yellow]Login cancelled.[/yellow]\n")
            return CommandResult(handled=True)

        api_key = api_key.strip() if api_key else ""
        if not api_key and not is_ollama:
            console.print("[bold red]API Key cannot be empty for this provider.[/bold red]\n")
            return CommandResult(handled=True)

        # 4. Live Connection & Model Discovery Validation
        console.print(f"\n[cyan]⚡ Connecting to {provider_display_name} and retrieving live models...[/cyan]")

        try:
            models = await fetch_provider_models(
                provider_id=target_provider_id,
                api_key=api_key,
                base_url=custom_base_url,
                force_refresh=True,
                timeout=10.0,
            )
        except Exception as exc:
            console.print(
                Panel(
                    f"[bold red]Authentication / Connection Failed[/bold red]\n\n"
                    f"Error: {exc}\n\n"
                    "Credentials were not saved. Please check your API key, base URL, and network connection.",
                    title="❌ Connection Failed",
                    border_style="red",
                )
            )
            return CommandResult(handled=True)

        if not models:
            console.print(
                Panel(
                    f"[bold yellow]Warning:[/bold yellow] Successfully connected to {provider_display_name}, "
                    "but no models were returned by the endpoint.\n"
                    "Will configure default model identifier.",
                    title="⚠️ Empty Model Catalog",
                    border_style="yellow",
                )
            )
            fallback_model = profile.default_model if profile else f"{target_provider_id}/default"
            chosen_canonical_model = fallback_model
        else:
            console.print(f"[bold green]✓ Verified![/bold green] Found {len(models)} models available.\n")

            # 5. Default Model Selection (Strict canonical 'provider/model_id')
            model_choices: list[Choice] = []
            for m in models:
                specs: list[str] = []
                if m.context_window:
                    ctx_k = m.context_window // 1000
                    specs.append(f"{ctx_k}k ctx")
                if m.supports_reasoning:
                    specs.append("Reasoning")
                if m.supports_vision:
                    specs.append("Vision")

                spec_str = f" [dim]({', '.join(specs)})[/dim]" if specs else ""
                display = f"{m.full_id}{spec_str}"
                model_choices.append(Choice(value=m.full_id, name=display))

            default_choice = profile.default_model if (profile and profile.default_model) else models[0].full_id

            try:
                chosen_canonical_model = await inquirer.select(
                    message=f"Select default model for {provider_display_name}:",
                    choices=model_choices,
                    default=default_choice,
                ).execute_async()
            except (KeyboardInterrupt, Exception):
                chosen_canonical_model = default_choice

        # 6. Save Credentials & Default Model to auth.json
        auth_store.save_provider_auth(
            provider_id=target_provider_id,
            api_key=api_key,
            default_model=chosen_canonical_model,
            base_url=custom_base_url,
            set_as_active=True,
        )

        # 7. Update Active Agent Manager Runtime
        if hasattr(context.agent_manager, "switch_model"):
            context.agent_manager.switch_model(chosen_canonical_model)

        # 8. Render Success Confirmation Panel
        info_table = Table.grid(padding=(0, 2))
        info_table.add_column("Field", style="bold yellow")
        info_table.add_column("Value", style="bright_white")

        info_table.add_row("Provider", f"[bold green]{provider_display_name}[/bold green] ({target_provider_id})")
        info_table.add_row("Active Model", f"[bold bright_cyan]{chosen_canonical_model}[/bold bright_cyan]")
        masked_key = (api_key[:4] + "..." + api_key[-4:]) if len(api_key) > 8 else ("***" if api_key else "None")
        info_table.add_row("API Key", masked_key)
        if custom_base_url:
            info_table.add_row("Base URL", custom_base_url)
        info_table.add_row("Stored In", str(auth_store.file_path))

        console.print(
            Panel(
                info_table,
                title="[bold green]✓ Provider Authenticated & Activated[/bold green]",
                border_style="green",
            )
        )
        return CommandResult(handled=True)
