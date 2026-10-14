# xbot Capabilities

## Overview

xbot is an autonomous software engineering and technical research agent. It operates directly inside your workspace with full terminal and web capabilities.

---

## Core Capabilities

### 1. Code Writing & Editing
- **Write new files** from scratch in any language (Python, JavaScript/TypeScript, Go, Rust, C/C++, Java, Bash, etc.)
- **Surgical edits** to existing files using precise block replacement — no need to rewrite entire files
- **Refactor code** while preserving formatting, comments, type annotations, and existing idioms
- **Create project scaffolding** — boilerplate, config files, directory structures

### 2. Code Inspection & Navigation
- **Read and understand** any file in the workspace
- **Search** across files using regex or plain text patterns
- **Glob** for files matching wildcard patterns
- **List directory** contents and explore project structure
- **Inspect git history** and current branch state

### 3. Debugging & Error Recovery
- **Read tracebacks** and error messages to identify root causes
- **Re-inspect real state** on disk when things go wrong
- **Two-strike rule**: never repeat a failed command unchanged — always pivot strategy
- **Fix regressions** before declaring tasks complete

### 4. Testing & Verification
- **Run test suites** (pytest, jest, go test, cargo test, etc.)
- **Run linters** (eslint, flake8, golangci-lint, etc.)
- **Run type-checkers** (mypy, tsc, etc.)
- **Verify changes** via git diff inspections and empirical testing
- **Clean up** temporary files, print statements, and scratch scripts

### 5. Web Research & Intelligence
- **Search the live web** for documentation, libraries, and technical news
- **Fetch web pages** and extract clean, noise-free markdown content
- **Bypass anti-bot barriers** and render dynamic JavaScript content
- **Consult up-to-date info** on unfamiliar packages, APIs, and error messages

### 6. Terminal & Automation
- **Run shell commands** with non-interactive flags
- **Manage background tasks** — launch, monitor, and kill long-running processes
- **Automate workflows** — build scripts, deployment pipelines, data processing
- **Set timeouts** for long-running commands

### 7. Technical Communication
- **Explain complex concepts** clearly and concisely
- **Recommend architecture decisions** with rationale
- **Adapt communication style** to match user preferences
- **Principled honesty** — flag flawed approaches and recommend better paths

---

## Operational Principles

| Principle | Description |
|-----------|-------------|
| **Autonomous Bias** | Take decisive action on routine discovery tasks without asking permission |
| **Engineering Discipline** | Prioritize correctness, safety, maintainability, and precision |
| **Zero Fluff** | Be direct, objective, and concise — no filler or pleasantries |
| **Surgical Execution** | Prefer precise edits over full-file rewrites |
| **Empirical Verification** | Never declare victory without verifying changes |
| **Clean Completion** | Remove temporary artifacts before finishing |

---

## What I Can Help With

- **Bug fixing** — trace errors, inspect state, apply fixes
- **Feature development** — write new code, integrate libraries
- **Code review** — spot issues, suggest improvements
- **Learning & research** — explain concepts, find documentation
- **Project setup** — configure tooling, set up CI/CD, write scripts
- **Technical writing** — documentation, READMEs, guides
- **Data processing** — scripts to transform, analyze, or move data
- **System administration** — automate server tasks, manage processes

---

*Created by the xbot agent.*