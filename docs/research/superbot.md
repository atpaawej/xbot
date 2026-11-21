# Research: SuperBot (David Ondrej) Architecture & Lessons for xbot

> Compiled 2026-11-21 to document SuperBot's architecture, harness patterns, and how it informs `xbot`.

---

## 1. Overview & Origin

**SuperBot** is an open-source, self-hosted AI teammate platform created by developer and YouTuber **David Ondrej**. 

* **Motivation**: Grok Bot (xAI) costs between $30/mo and $200+/mo, imposes restrictive usage caps and rate limits, and locks users into xAI's proprietary infrastructure.
* **Goal**: Replicate the core autonomous workflows of Grok Bot—persistent AI teammates, background routines, memory, and tool execution—as a free, self-hosted, local-first system.
* **Core Philosophy**: *"The harness is the agent that does the work."*

---

## 2. Core Architectural Pillars

### A. Harness-Agnostic Architecture
SuperBot does **not** attempt to build its own ReAct agent loop, tool-calling parser, terminal executor, or context window compactor. Instead, it delegates all execution to battle-tested external coding agent CLIs:

* **Claude Code CLI** (Anthropic)
* **Codex CLI** (OpenAI)
* **Pi Agent**
* *(Planned/Extensions: Grok Build, Hermes Agent)*

The SuperBot daemon acts strictly as the **orchestrator, scheduler, and interface layer**.

### B. The Adapter Pattern (`server/src/adapters/`)
For each supported CLI harness, SuperBot implements a dedicated adapter module:
* **Session Lifecycle**: Spawns and manages CLI subprocesses, binding them to specific bot workspaces and persistent session IDs.
* **Input Injection**: Injects user prompts, bot system personas, skills, and memory files formatted for that CLI's native structure.
* **Output Streaming**: Parses and normalizes stdout/stderr streams into Server-Sent Events (SSE) for the frontend web interface (text deltas, tool calls, status updates).
* **Approval Handling**: Attempts to detect and intercept permission checks from the CLI to surface them to the user.

### C. Persistent Bot Teammates & Workspaces
* Each bot represents a distinct virtual coworker (e.g. Researcher, Code Reviewer, Ops Monitor).
* **Workspace Isolation**: Each bot is assigned a physical directory on the host VPS/machine.
* **Memory**: Bots retain context and instructions across conversations via structured `MEMORY.md` files and custom rule files injected into session runs.

### D. Routines & Autonomous Execution
* Built-in cron scheduler running inside the daemon.
* Allows configuring recurring background tasks (e.g., checking GitHub PRs every morning, auditing dependencies, summarizing logs).
* Executes without requiring an active browser tab.

### E. Storage & Tech Stack
* **Backend**: Rust (built for high performance, low VPS resource consumption, and single-binary deployment).
* **Database**: SQLite (manages bot metadata, session mappings, routine schedules, and execution logs).
* **Frontend**: Browser-based chat interface consuming SSE streams.

---

## 3. Strengths & Limitations of SuperBot's Approach

| Aspect | SuperBot Design | Strengths | Limitations |
| :--- | :--- | :--- | :--- |
| **Execution Engine** | External Agent CLIs | Zero agent loop boilerplate; leverages top-tier models and tools immediately. | Relies on bespoke adapters that scrape stdout/ANSI codes; updates to CLIs can break parsing. |
| **Runtime** | Rust Daemon | Ultra-low RAM/CPU overhead; runs on a $5/mo VPS. | Higher barrier to contribution for web developers compared to TypeScript. |
| **Approvals** | CLI screen-scraping | Keeps human in the loop. | Brittle; CLIs don't have uniform approval hooks over raw stdout. |
| **Persistence** | SQLite + `MEMORY.md` | Simple, inspection-friendly, zero external database setup. | Works best on single-host deployments (which is fine for MVP). |

---

## 4. Evolution from SuperBot to `xbot` via ACP

SuperBot validated the core thesis: **users want persistent AI teammates with routines, and delegating execution to existing agent harnesses is the winning architecture.**

However, SuperBot's biggest architectural vulnerability is writing **custom stdout/stdin adapters** for each CLI. 

`xbot` improves upon SuperBot by adopting the **Agent Client Protocol (ACP)**:

1. **Protocol-Level Standardization**: Instead of brittle screen-scraping, ACP standardizes communication over JSON-RPC 2.0 (`initialize`, `session/new`, `session/prompt`, `session/update`).
2. **First-Class Human Approvals**: ACP natively provides `session/request_permission`. When Claude Code, Goose, or OpenHands needs to run a bash command, it sends a structured JSON-RPC request rather than prompting raw text to a pseudo-terminal.
3. **Universal Compatibility**: Any agent that implements ACP immediately works with `xbot` without writing a new adapter file.
4. **Full-Stack TypeScript**: Unifying backend and frontend in TypeScript allows sharing ACP protocol schemas and event types directly with the React UI.
