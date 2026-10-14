# 🤖 xbot

**xbot** is a modular, autonomous AI agent built in Python featuring an interactive **Rich TUI**, powered by the official **AI SDK of Python**, with web intelligence backed by **TinyFish**.

---

## 🌟 Key Architecture & Features

```
xbot/
├── src/xbot/
│   ├── agent/       # Core Agent loop using AI SDK of Python (ai package)
│   ├── config/      # Environment loader (.env.local > .env) via python-dotenv
│   ├── tools/       # Core tools (bash, write, edit, read, grep, glob, TinyFish web tools)
│   ├── tui/         # Rich terminal user interface with streaming and panels
│   └── main.py      # CLI entrypoint
```

1. **AI SDK Agent (`ai` package)**:
   - Uses the official `ai` Python SDK (`ai.Agent`, `@ai.tool`, `ai.stream`, `ai.providers.openai`).
   - Seamless streaming of token deltas, model reasoning, and automatic tool execution loops.
   - Compatible with **any OpenAI-compatible provider** (OpenAI, OpenRouter, Groq, DeepSeek, Together, Ollama, vLLM, LMStudio).

2. **Terminal User Interface (`rich` & `prompt_toolkit`)**:
   - Modern, sleek cyberpunk/dark aesthetic with startup banner.
   - Real-time token streaming with syntax-highlighted Markdown rendering.
   - Distinct, structured visual cards for tool invocations and results.
   - Live spinner feedback while the model is reasoning or running tools.
   - Interactive prompt with history navigation and slash command auto-completion.

3. **Core Tool Suite**:
   - `bash`: Subprocess command execution with working directory context and timeout protection.
   - `write`: File creation and overwriting with automatic directory creation.
   - `edit`: Exact string search-and-replace block editing with safety safeguards.
   - `read`: Line-numbered file reading with start/end range slicing.
   - `grep`: Regex and string pattern search across directories (ignoring `.git`, `.venv`, and build noise).
   - `glob`: Wildcard file and directory matching.

4. **TinyFish Web Intelligence**:
   - `web_search`: Live web search via TinyFish Search API (`api.search.tinyfish.ai`) delivering agent-optimized, structured results.
   - `web_fetch`: Smart web reader via TinyFish Fetch API (`api.fetch.tinyfish.ai`) that renders JavaScript, bypasses anti-bot defenses, and extracts clean, noise-free Markdown.

5. **Configuration (`python-dotenv`)**:
   - Priority cascade: `.env.local` overrides `.env`.
   - Sanitized key masking in TUI and status tables.

---

## ⚡ Installation

Install `xbot` as a standalone executable with a single command (no Python or virtual environment required):

### macOS & Linux
```bash
curl -fsSL https://raw.githubusercontent.com/atpaawej/xbot/main/install.sh | bash
```

### Windows (PowerShell)
```powershell
irm https://raw.githubusercontent.com/atpaawej/xbot/main/install.ps1 | iex
```

### Standalone Executables
Precompiled standalone single-binary executables for **Linux (x86_64)**, **macOS (Apple Silicon & Intel)**, and **Windows (x86_64 .exe)** are also directly available on the [GitHub Releases](https://github.com/atpaawej/xbot/releases) page.

---

## 🚀 Quickstart from Source (Developers)

### 1. Prerequisites
Install `uv` if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Setup Virtual Environment & Dependencies
Clone and install dependencies:
```bash
# Create venv and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e .
```

### 3. Configure `.env` or `.env.local`
Copy the example template:
```bash
cp .env.example .env.local
```

Edit `.env.local` with your preferred provider and keys:
```env
# OpenAI-Compatible Provider
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-your-openai-or-compatible-key
MODEL_ID=gpt-4o

# TinyFish Web Search & Fetch (free key: https://agent.tinyfish.ai/api-keys)
TINYFISH_API_KEY=your_tinyfish_api_key_here

# Optional: workspace directory (defaults to current dir)
WORKSPACE_DIR=.
```

---

## 💻 Usage

### Launch Interactive TUI
```bash
uv run xbot
```

### Command-Line Options
```bash
# Specify model override
uv run xbot --model deepseek-chat

# Specify custom OpenAI-compatible endpoint
uv run xbot --base-url https://api.deepseek.com/v1 --model deepseek-chat

# Run a single prompt (non-interactive one-shot)
uv run xbot -p "Inspect the repository and list python files"
```

---

## ⚡ TUI Slash Commands

Inside the interactive prompt, you can use built-in slash commands:

| Command | Action |
|---|---|
| `/help` | Display command reference and tool registry |
| `/tools` | View descriptions and parameter schemas for all 8 tools |
| `/config` | Inspect active model, base URL, and masked API keys |
| `/history` | View turn count and conversation trace statistics |
| `/reset` | Clear conversation memory and start fresh turn |
| `/clear` | Clear the terminal screen |
| `/exit` or `/quit` | Exit xbot |

---

## 🌐 Supported OpenAI-Compatible Providers

xbot works with any OpenAI-compatible completions API simply by modifying `OPENAI_BASE_URL`, `MODEL_ID`, and `OPENAI_API_KEY`:

| Provider | `OPENAI_BASE_URL` | Example `MODEL_ID` |
|---|---|---|
| **OpenAI** | `https://api.openai.com/v1` | `gpt-4o`, `gpt-4o-mini`, `o3-mini` |
| **OpenRouter** | `https://openrouter.ai/api/v1` | `anthropic/claude-3.5-sonnet`, `meta-llama/llama-3.3-70b-instruct` |
| **Groq** | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
| **DeepSeek** | `https://api.deepseek.com/v1` | `deepseek-chat`, `deepseek-reasoner` |
| **Together AI** | `https://api.together.xyz/v1` | `meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo` |
| **Local Ollama** | `http://localhost:11434/v1` | `llama3.2`, `qwen2.5-coder` |
| **Local vLLM** | `http://localhost:8000/v1` | Any hosted model |

---

## 🧪 Testing

Run the test suite using pytest:
```bash
uv pip install pytest pytest-asyncio
pytest -v
```
All 17 tests cover config precedence, all 8 tools, mock OpenAI streaming & tool calling, and Rich UI components.
