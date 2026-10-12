"""CLI entrypoint for xbot."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

from xbot import __version__
from xbot.agent import AgentManager
from xbot.config import Config, get_config
from xbot.tui import XBotTUI


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="xbot",
        description="Autonomous AI Agent with Rich TUI, AI SDK of Python, and TinyFish Web Intelligence",
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"xbot {__version__}",
    )
    parser.add_argument(
        "-m", "--model",
        dest="model_id",
        help="Override the model identifier (e.g. gpt-4o, claude-3-5-sonnet, deepseek-chat)",
    )
    parser.add_argument(
        "-u", "--base-url",
        dest="base_url",
        help="Override the OpenAI-compatible base URL (e.g. https://openrouter.ai/api/v1)",
    )
    parser.add_argument(
        "-p", "--prompt",
        dest="prompt",
        help="Execute a single prompt in non-interactive mode and output the response",
    )
    parser.add_argument(
        "-w", "--workspace",
        dest="workspace",
        help="Working directory path for agent execution",
    )
    return parser.parse_args()


def main() -> None:
    """Main CLI entrypoint."""
    args = parse_args()

    # Apply command-line overrides to environment if specified
    if args.model_id:
        os.environ["MODEL_ID"] = args.model_id
    if args.base_url:
        os.environ["OPENAI_BASE_URL"] = args.base_url
    if args.workspace:
        os.environ["WORKSPACE_DIR"] = args.workspace

    config = get_config(reload=True)
    agent = AgentManager(config=config)
    tui = XBotTUI(agent_manager=agent)

    # One-shot CLI mode if prompt provided
    if args.prompt:
        async def run_oneshot() -> None:
            await tui.run_turn(args.prompt)

        try:
            asyncio.run(run_oneshot())
        except KeyboardInterrupt:
            sys.exit(130)
        return

    # Interactive TUI mode
    try:
        asyncio.run(tui.start())
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
