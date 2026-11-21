# Spec: xbot — Open-Source Grok Bot Alternative Powered by ACP

## Problem Statement

Users and developers seeking autonomous AI teammates (such as xAI's Grok Bot) face significant barriers:
1. **High Cost & Vendor Lock-in**: Grok Bot costs $30 to $200+/month, is closed-source, restricts models to xAI's ecosystem, and enforces strict usage limits.
2. **Fragility of Existing Alternatives**: Current open-source alternatives either require heavy, complex infrastructure (Docker microVM fleets, Redis, PostgreSQL) or rely on fragile, bespoke CLI screen-scraping adapters that break whenever underlying agent tools update.
3. **Lack of Autonomous Asynchronous Capability**: Most AI chat interfaces are passive, requiring active browser sessions and immediate user input, rather than running 24/7 background routines, maintaining persistent workspaces, and requesting approvals only when needed.

## Solution

`xbot` is a lightweight, open-source, local-first alternative to Grok Bot. Instead of reinventing an agent execution runtime or maintaining brittle CLI adapters, `xbot` leverages the standardized **Agent Client Protocol (ACP)** to drive production-ready coding agents (such as Claude Code, Goose, or OpenHands) as execution harnesses.

`xbot` provides:
- A clean **React web interface** for real-time chat, task management, and human-in-the-loop approvals.
- **Persistent Bot Workspaces** with isolated filesystems and long-term memory (`MEMORY.md`).
- A 24/7 **Background Routines Scheduler** (cron-based automation) that triggers autonomous agent workflows.
- A **Human Approval Relay** ("Needs Your OK") that intercepts ACP permission requests and prompts the user in the web UI before any sensitive tool operation runs.

## User Stories

1. As a developer, I want to create a new AI bot teammate with a custom name, persona/system prompt, and isolated workspace directory, so that the bot can perform dedicated tasks without cluttering other projects.
2. As a user, I want to interact with my bot through a clean React web chat interface, so that I have a responsive, modern environment to assign tasks.
3. As a user, I want to see streaming responses, real-time thinking indicators, and tool execution logs in the chat, so that I understand what actions the bot is taking.
4. As a user, I want the bot to ask for my confirmation ("Needs Your OK") whenever it attempts a sensitive action (like running bash commands, deleting files, or making network requests), so that I remain in full control of my machine.
5. As a user, I want to approve or reject a permission request directly inside the web UI with a single click, so that the bot can either proceed safely or gracefully halt.
6. As a user, I want options to "Allow Once", "Allow Always", or "Reject" when an approval request occurs, so that I don't have to repeatedly approve routine commands.
7. As a user, I want to schedule recurring routines (e.g. daily code reviews, dependency checks, or morning summaries) using standard cron expressions, so that the bot works for me even when I am offline.
8. As a user, I want to view a dashboard of all active and past routines, including their next scheduled run time and previous execution outcomes, so that I can monitor automated work.
9. As a developer, I want to define reusable skills as plain markdown files that can be injected into routine tasks or chat commands, so that complex multi-step workflows are repeatable.
10. As a user, I want each bot to maintain a persistent `MEMORY.md` file in its workspace, so that it remembers project conventions, user preferences, and learnings across conversations.
11. As a user, I want to view and edit the bot's `MEMORY.md` directly from the web interface, so that I can correct or augment what the bot knows.
12. As a developer, I want `xbot` to connect to any ACP-compliant agent CLI (such as Claude Code or Goose) without code modifications, so that I can use my preferred AI harness and model.
13. As a developer, I want `xbot` to run locally or self-host on a single VPS with minimal dependencies (SQLite and Node.js), so that setup takes less than two minutes.
14. As a user, I want to see a history of all completed tasks and generated artifacts, so that I can review code diffs or reports created during background runs.
15. As a developer, I want `xbot` to handle subprocess failure or network disconnection gracefully, so that long-running routines do not crash the orchestrator daemon.

## Implementation Decisions

- **Full-Stack TypeScript Architecture**: Both the backend daemon and frontend web client are written in TypeScript to share protocol schemas, event interfaces, and configuration types without duplication.
- **Harness Communication via Agent Client Protocol (ACP)**:
  - The backend communicates with agent harnesses via JSON-RPC 2.0 over standard `stdio`.
  - Implements the standard ACP lifecycle:
    - `initialize`: Capability exchange between `xbot` and the agent harness.
    - `session/new` and `session/resume`: Session lifecycle management tied to specific bot workspaces.
    - `session/prompt`: Dispatches user requests and routine instructions to the agent.
    - `session/request_permission`: Intercepted by `xbot` to trigger human-in-the-loop approvals.
    - `session/update`: Streams token deltas and tool execution updates from the harness to the web UI.
- **Real-Time Client-Server Communication**:
  - WebSockets (or Server-Sent Events) are used to stream ACP events, agent status updates, and permission requests from the daemon to the React UI in real time.
- **Data Persistence via SQLite**:
  - A lightweight local SQLite database manages bots, chat sessions, routine schedules, and approval logs.
  - Relational schema shape:
    - `bots`: `id`, `name`, `system_prompt`, `harness_command`, `workspace_path`, `created_at`
    - `sessions`: `id`, `bot_id`, `created_at`, `status`
    - `messages`: `id`, `session_id`, `role`, `content`, `created_at`
    - `routines`: `id`, `bot_id`, `name`, `cron_expression`, `prompt`, `enabled`, `last_run_at`
    - `approvals`: `id`, `session_id`, `request_id`, `tool_call`, `status` (`pending`, `allowed`, `rejected`), `created_at`
- **Workspace and Memory Isolation**:
  - Each bot operates strictly within its designated workspace directory on the host filesystem.
  - Every workspace contains a `MEMORY.md` file automatically read and injected into new agent sessions.
- **React Frontend Design**:
  - Single-page application using React, Vite, and Tailwind CSS.
  - Multi-panel layout: Bot navigation sidebar, real-time chat with streaming markdown, interactive Approval Cards for pending permissions, and a Routines management drawer.

## Testing Decisions

- **Seams**: The primary integration seam is the **ACP Client Bridge**. All external agent interactions (spawning, prompt dispatch, token streaming, permission requests) pass through this boundary.
- **What Makes a Good Test**: Tests must verify observable behavior and protocol compliance rather than internal implementation details. Tests must not rely on live paid LLM API calls or external networks.
- **Module Coverage**:
  - **ACP Client Bridge Tests**: Use a mock ACP stdio subprocess to verify standard handshakes (`initialize`), prompt routing (`session/prompt`), streaming delta emissions, and permission request/response round-trips (`session/request_permission`).
  - **Routines Engine Tests**: Verify scheduled cron triggering, routine job execution against an agent session, and logging of execution results.
  - **Approval State Machine Tests**: Verify transition invariants (`pending` -> `allowed_once` / `allowed_always` / `rejected`), ensuring no tool action proceeds before resolution.
- **Prior Art**: Protocol integration tests modeled after standard Language Server Protocol (LSP) and Model Context Protocol (MCP) client test suites.

## Out of Scope

- Native iOS/Android mobile apps or messaging bots (Telegram, Discord, Slack) — React web interface is the focus for MVP.
- Multi-tenant cloud VM fleet management or Kubernetes container orchestration.
- Live interactive VNC desktop streaming (headless terminal and file-based execution are sufficient for v1).
- Multi-agent swarm debate rooms (focus is on 1-on-1 bot workspaces and autonomous routine execution).
- OAuth SaaS brokers for external tools (delegated to standard MCP servers configured within the agent harness).

## Further Notes

- By utilizing ACP as the foundational abstraction, `xbot` stays evergreen: whenever new agent harnesses (Claude Code, Goose, OpenHands, Codex) update their internal models or tools, `xbot` inherits the enhancements immediately with zero code changes.
- Future phases may introduce team-shared workspaces and multi-bot delegation channels once single-bot autonomy and routines are rock-solid.
