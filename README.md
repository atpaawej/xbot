# xbot

> An open-source, local-first alternative to Grok Bot powered by the **Agent Client Protocol (ACP)**.

`xbot` turns production-ready AI coding agents (Claude Code, Goose, OpenHands, etc.) into persistent, autonomous teammates with scheduled routines, persistent memory, and human-in-the-loop approvals.

## Documentation

- [Project Specification](docs/spec/SPEC.md)
- [Grok Bot Architecture Research](docs/research/grokbot.md)

## Architecture Overview

```
React Web Chat UI (Vite + Tailwind)
          │
          ▼ (WebSocket / SSE)
    xbot Daemon (Node.js / TypeScript)
    ├── SQLite (Bots, Sessions, Routines, Approvals)
    ├── Cron Scheduler (24/7 Routines)
    ├── Human Approval Relay ("Needs Your OK")
    └── ACP JSON-RPC Client (stdio)
          │
          ▼
    ACP Agent Harness (Claude Code / Goose / OpenHands)
    └── Persistent Bot Workspace (`workspaces/<bot-id>/MEMORY.md`)
```

## License

MIT
