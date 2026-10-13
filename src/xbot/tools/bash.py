"""Bash command execution tool for xbot with background process management."""

from __future__ import annotations

import asyncio
import os
import signal
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

from ai import tool
from xbot.config import get_config

MAX_OUTPUT_CHARS = 40_000


@dataclass
class BackgroundTask:
    task_id: str
    command: str
    process: asyncio.subprocess.Process
    start_time: float
    log_file: Path
    status: str = "running"
    exit_code: Optional[int] = None


class BackgroundTaskManager:
    """Tracks and manages running background shell tasks."""

    def __init__(self) -> None:
        self.tasks: Dict[str, BackgroundTask] = {}
        self._counter: int = 1

    def generate_id(self) -> str:
        tid = f"bg_{self._counter}"
        self._counter += 1
        return tid

    def register(
        self,
        task_id: str,
        command: str,
        process: asyncio.subprocess.Process,
        log_file: Path,
    ) -> BackgroundTask:
        task = BackgroundTask(
            task_id=task_id,
            command=command,
            process=process,
            start_time=time.time(),
            log_file=log_file,
            status="running",
        )
        self.tasks[task_id] = task
        return task

    def get(self, task_id: str) -> Optional[BackgroundTask]:
        return self.tasks.get(task_id)

    def list_all(self) -> list[BackgroundTask]:
        return list(self.tasks.values())


# Global manager instance
_bg_manager = BackgroundTaskManager()


async def _monitor_background_process(
    task: BackgroundTask, stdout_stream, stderr_stream
) -> None:
    """Stream background process output to log file and record completion."""
    try:
        with open(task.log_file, "a", encoding="utf-8", errors="replace") as f:
            while True:
                out_chunk = await stdout_stream.read(1024)
                err_chunk = await stderr_stream.read(1024)

                if out_chunk:
                    f.write(out_chunk.decode("utf-8", errors="replace"))
                    f.flush()
                if err_chunk:
                    f.write(f"[STDERR] {err_chunk.decode('utf-8', errors='replace')}")
                    f.flush()

                if not out_chunk and not err_chunk:
                    break

        exit_code = await task.process.wait()
        task.exit_code = exit_code
        if task.status == "running":
            task.status = "completed" if exit_code == 0 else f"failed (code {exit_code})"
    except Exception as exc:
        if task.status == "running":
            task.status = f"error ({exc})"


@tool
async def bash(
    command: str = "",
    action: str = "run",
    is_bg: bool = False,
    task_id: Optional[str] = None,
    timeout: Optional[int] = None,
) -> str:
    """Execute shell commands or manage background tasks.

    Args:
        command: The bash command string to execute (required when action='run').
        action: One of 'run' (execute command), 'list' (list background tasks),
                'status' (check a background task's output), or 'kill' (terminate a task).
        is_bg: When True and action='run', launches the command in the background without blocking.
        task_id: Identifier of the background task (required for action='status' or 'kill').
        timeout: Execution timeout in seconds for synchronous commands (defaults to BASH_TIMEOUT from config).

    Returns:
        Execution output or background task status information.
    """
    config = get_config()
    cwd = config.workspace_dir
    cwd.mkdir(parents=True, exist_ok=True)
    action = (action or "run").strip().lower()

    # 1. Action: LIST background tasks
    if action == "list":
        tasks = _bg_manager.list_all()
        if not tasks:
            return "No background tasks currently recorded."

        lines = ["Active & Previous Background Tasks:"]
        for t in tasks:
            elapsed = int(time.time() - t.start_time)
            lines.append(
                f"- [{t.task_id}] Status: {t.status} (elapsed: {elapsed}s)\n"
                f"  Command: {t.command}\n"
                f"  Log: {t.log_file}"
            )
        return "\n".join(lines)

    # 2. Action: STATUS of a background task
    if action == "status":
        if not task_id:
            return "Error: 'task_id' must be specified to check status. Use action='list' to see active task IDs."
        task = _bg_manager.get(task_id)
        if not task:
            return f"Error: No background task found with ID '{task_id}'."

        elapsed = int(time.time() - task.start_time)
        status_info = [
            f"Task ID: {task.task_id}",
            f"Status: {task.status}",
            f"Elapsed: {elapsed}s",
            f"Command: {task.command}",
            f"Log File: {task.log_file}",
        ]

        # Read last part of log
        if task.log_file.exists():
            log_content = task.log_file.read_text(encoding="utf-8", errors="replace")
            if log_content:
                tail = log_content[-3000:]
                status_info.append(f"\n--- Output Tail ---\n{tail}")
            else:
                status_info.append("\n(Log file is currently empty)")
        else:
            status_info.append("\n(No log file created yet)")

        return "\n".join(status_info)

    # 3. Action: KILL a background task
    if action == "kill":
        if not task_id:
            return "Error: 'task_id' must be specified to kill a task. Use action='list' to see active task IDs."
        task = _bg_manager.get(task_id)
        if not task:
            return f"Error: No background task found with ID '{task_id}'."

        if task.status != "running":
            return f"Task '{task_id}' is not running (Current status: {task.status})."

        try:
            task.process.terminate()
            task.status = "killed"
            return f"Successfully sent termination signal to task '{task_id}'."
        except ProcessLookupError:
            task.status = "killed"
            return f"Task '{task_id}' process already finished."
        except Exception as exc:
            return f"Error terminating task '{task_id}': {exc}"

    # 4. Action: RUN command
    if not command.strip():
        return "Error: 'command' cannot be empty when action='run'."

    # 4a. Run in BACKGROUND
    if is_bg:
        tid = _bg_manager.generate_id()
        task_dir = cwd / ".xbot" / "tasks"
        task_dir.mkdir(parents=True, exist_ok=True)
        log_file = task_dir / f"{tid}.log"
        log_file.write_text(f"--- Task {tid} started: {command} ---\n", encoding="utf-8")

        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(cwd),
        )

        task = _bg_manager.register(tid, command, proc, log_file)
        asyncio.create_task(
            _monitor_background_process(task, proc.stdout, proc.stderr)
        )

        return (
            f"Started background task '{tid}'.\n"
            f"Command: {command}\n"
            f"Log file: {log_file}\n"
            f"Check output using action='status' task_id='{tid}' or stop it using action='kill' task_id='{tid}'."
        )

    # 4b. Run SYNCHRONOUSLY
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
                f"Command: {command}\n"
                f"Tip: For long-running processes, set is_bg=True to run in background."
            )

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        return_code = process.returncode

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
