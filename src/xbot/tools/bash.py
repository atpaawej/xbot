"""Bash command execution tool for xbot."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

from ai import tool
from xbot.config import get_config

MAX_OUTPUT_CHARS = 40_000


@tool
async def bash(command: str, timeout: Optional[int] = None) -> str:
    """Execute a bash shell command in the workspace directory.

    Args:
        command: The bash command string to execute.
        timeout: Optional timeout in seconds. Defaults to BASH_TIMEOUT from config.

    Returns:
        The execution output including exit code, stdout, and stderr.
    """
    config = get_config()
    cwd = config.workspace_dir
    cwd.mkdir(parents=True, exist_ok=True)

    effective_timeout = timeout if timeout is not None else config.bash_timeout

    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
        )

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), timeout=float(effective_timeout)
            )
        except asyncio.TimeoutError:
            try:
                process.kill()
            except ProcessLookupError:
                pass
            return (
                f"[Command timed out after {effective_timeout} seconds]\n"
                f"Command: {command}"
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        return_code = process.returncode

        # Output formatting
        output_parts: list[str] = [f"Exit code: {return_code}"]

        if stdout:
            if len(stdout) > MAX_OUTPUT_CHARS:
                truncated = stdout[:MAX_OUTPUT_CHARS]
                output_parts.append(
                    f"STDOUT (truncated to {MAX_OUTPUT_CHARS} chars):\n{truncated}\n...[output truncated]..."
                )
            else:
                output_parts.append(f"STDOUT:\n{stdout}")

        if stderr:
            if len(stderr) > MAX_OUTPUT_CHARS:
                truncated = stderr[:MAX_OUTPUT_CHARS]
                output_parts.append(
                    f"STDERR (truncated to {MAX_OUTPUT_CHARS} chars):\n{truncated}\n...[output truncated]..."
                )
            else:
                output_parts.append(f"STDERR:\n{stderr}")

        if not stdout and not stderr:
            output_parts.append("(Command produced no output)")

        return "\n\n".join(output_parts)

    except Exception as exc:
        return f"Error executing bash command '{command}': {exc}"
