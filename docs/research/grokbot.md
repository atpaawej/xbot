# Research: Grok Bot (xAI) & Open-Source Landscape

> Compiled 2026-11-21 to inform the design of an open-source Grok Bot alternative.

## 1. What Grok Bot Is

**Grok Bot** (often written *Grokbot*) is xAI's autonomous AI teammate platform — distinct from standard Grok chat and the coding tool Grok Build. Rather than responding to isolated prompts in a browser tab, Grok Bots run asynchronously 24/7 on a persistent cloud computer, execute multi-step workflows across apps and websites, collaborate with each other, and only interrupt the user when a decision or approval is needed.

- **Availability & Pricing**: Bundled in X Subscriptions starting at **Premium ($30/mo)**, scaling through **Super ($100/mo)**, **Ultra ($200/mo)**, and **Teams/Enterprise ($30+/user/mo)**. Accessible on desktop (macOS/Windows), web, and mobile (iOS/Android), plus partner integrations (e.g., Cursor).
- **Sources**: x.ai official Grok Bot overview, docs, and pricing pages; Tech/product reviews (DataCamp, Vellum, GoSearch, Flavio Copes).

## 2. Core Architectural Pillars

### A. Persistent Cloud Computer ("A Computer of Its Own")
- Each user account (or team bot scope) gets a persistent cloud VM with a **real browser, filesystem, and terminal**.
- Tasks continue running when the user closes their laptop or logs off.
- Browser sessions, files, and CLI state persist across runs.
- Enterprise tiers support custom network routing (corporate VPNs, IP allowlists).

### B. Hybrid Tooling: Connectors, MCP, and Computer Use
- **Native Connectors**: OAuth integrations for everyday SaaS (Gmail, Google Drive/Calendar/Workspace, Outlook/OneDrive/SharePoint, Slack, Notion, Linear, GitHub, Salesforce, HubSpot, Box, Vercel, and a native **X Connector** primarily focused on reading/monitoring timelines, search, and mentions).
- **Model Context Protocol (MCP)**: First-class support for remote/custom MCP servers to expose internal tools and APIs dynamically.
- **Browser / GUI Computer Use**: Fallback for apps and legacy web portals without clean APIs — the bot signs in and clicks/fills forms directly in its cloud browser.

### C. Skills (How to Do Work)
- A **Skill** is a reusable instruction set defining inputs, step sequences, decision rules, expected outputs, and safety boundaries.
- Workflows are typically tested interactively in chat (or demonstrated/recorded once) and then saved as a private or team-shared Skill.

### D. Routines (When to Do Work)
- A **Routine** triggers a Bot (often executing a Skill) automatically on either:
  - A **time schedule** (recurring cron-like cadence), or
  - An **external event** (incoming Slack message, email, webhook, GitHub/Linear/Sentry/PagerDuty update).

### E. Multi-Bot Collaboration & Surfaces
- Users can create a **roster of specialized Bots** (e.g., Chief of Staff, Research, Engineering, Ops) that coordinate in **group chats**, **DMs**, and external channels like **Slack**.
- Personal DMs use the member's personal computer and connected accounts; shared Team Bots operate on a shared team computer and shared memory.

### F. Persistent Memory
- **Bot-centric memory**: Personal Bots retain learned context across conversations, scoped to that Bot instance.
- **Team memory**: Team Bots share structured memory and configuration across authorized workspace members. (Third-party memory bots like `@Supermemory` can also participate in group chats.)

### G. Human-in-the-Loop Approvals ("Needs Your OK")
- Configurable **Auto Review / approval gates** pause execution before high-consequence or external actions (sending emails, publishing posts, spending money, deleting data) or when hitting blockers like **CAPTCHAs** and MFA/login prompts.

## 3. Existing Open-Source Alternatives (2026 Landscape)

| Project | License | Core Approach | Notable Strengths |
| :--- | :--- | :--- | :--- |
| **Rakazo** | Apache-2.0 | Closest direct Grok Bot clone ("Private computers" — isolated container + credentials per bot) | Per-bot isolation, lasting memory, routines, web/desktop/mobile clients |
| **OpenClaw & forks** (NanoClaw, PicoClaw, Nanobot) | Open-source | Always-on autonomous agent daemon; forks optimize for container isolation (NanoClaw) or minimal footprint (PicoClaw/Nanobot) | Large community mindshare, lightweight local/self-hosted options |
| **Hermes Agent** | MIT | Lightweight local-first autonomous agent | Self-evolving skills, MCP support, built-in cron jobs, local dashboard, explicit security boundaries |
| **OpenMausBot / Dusk Bot** | Open-source | Local-first BYOK/BYO-subscription bot rosters | Bring your own LLM keys/subscriptions, editable persistent memory |

## 4. Key Design Tensions for an Open-Source Alternative

1. **Isolation vs. Resource Cost**: Per-bot containers/VMs give clean credential and filesystem isolation, while a single shared computer is cheaper to host on a small VPS.
2. **Credential Security**: Giving an LLM access to browser cookies, OAuth tokens, and shell commands creates prompt-injection and exfiltration risks — isolating secrets from the model context (proxy/vault) and gating side effects behind approvals is critical.
3. **Browser Takeover UX**: Any real-world browser agent inevitably hits MFA, OAuth consent, and CAPTCHAs; users need a smooth way to temporarily take over the remote browser session.
4. **Structured Tools (MCP/APIs) vs. GUI Automation**: APIs/MCP are fast and reliable; browser computer use is universal but slower and more fragile.
