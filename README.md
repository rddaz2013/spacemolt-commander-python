# 🚀 SpaceMolt Commander (Python)

> Autonomous AI agent for the [SpaceMolt](https://spacemolt.com) text-based MMO — a Python re-implementation of the [TypeScript commander](https://github.com/SpaceMolt/commander) with hybrid-LLM architecture and token-optimised code execution.

## Architecture

```
┌─────────────────────────────────────────────┐
│  cli.py — Click CLI (run / service / status)│
│         ↓                                   │
│  commander.py — Outer Loop                  │
│    • Build system prompt                    │
│    • Run turn → sleep → poll → nudge        │
│    • Graceful shutdown + session handoff     │
│         ↓                                   │
│  loop.py — Inner Tool-Calling Loop          │
│    • Context compaction (>55 % budget)       │
│    • LLM call with retry                    │
│    • Tool dispatch                          │
│    ↓           ↓             ↓              │
│  tools.py    llm_router.py  compaction.py   │
│  (6 tools)   (hybrid LLM)   (summarise)    │
│    ↓                                        │
│  api.py — httpx async REST client           │
│    • Session auto-renewal                   │
│    • Rate-limit / reconnect handling        │
│    • YAML result formatting                 │
│         ↓                                   │
│  SpaceMolt Game Server (v2 REST API)        │
└─────────────────────────────────────────────┘
```

## Key Design Decisions

| Feature | Approach |
|---------|----------|
| **Tool count** | 6 tools (game, save_credentials, update_todo, read_todo, status_log, execute_code) instead of 224 individual endpoints |
| **Token saving** | Universal `game` tool + compact pipe-delimited command list in system prompt |
| **Code execution** | LLM generates Python for data-heavy tasks → local execution → compact summary returned (up to 99 % token reduction) |
| **LLM routing** | Cloud (Anthropic/OpenAI) for strategy, local Ollama for simple API calls |
| **Context compaction** | LLM-based summarisation when messages > 55 % of context window |
| **Session handoff** | 3–8 bullet-point summary saved to disk + Captain's Log on shutdown |

## Quick Start

```bash
# 1. Install
pip install -e .

# 2. Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# 3. Run with a mission
spacemolt run "mine ore and get rich" --session my_first_run

# 4. Or in service mode (continuous)
spacemolt service --mission "dominate the galaxy"

# 5. Check session status
spacemolt status --session my_first_run
```

## Hybrid LLM Architecture

The commander routes tasks between **cloud** and **local** LLMs:

| Backend | Used for | Example models |
|---------|----------|---------------|
| ☁️ Cloud | Strategic decisions, code generation, complex planning | `anthropic/claude-sonnet-4-20250514`, `openai/gpt-4o` |
| 🏠 Local | Simple API calls, status checks, quick reactions | `ollama/qwen3:8b`, `ollama/llama3.1:8b` |

Routing is automatic (`--backend auto`) or can be forced (`--backend cloud` / `--backend local`).

**Requires [Ollama](https://ollama.com) for local models:**
```bash
ollama pull qwen3:8b
```

## Token Optimisation

### 1. Universal Game Tool
Instead of defining 224 tool schemas (≈ 50–200 tokens each), the commander exposes **one `game` tool** that accepts any command + args. Available commands are listed as compact text in the system prompt.

### 2. Code Execution
For data-heavy operations (market analysis, route planning), the LLM generates Python code that runs locally:

```python
# LLM generates:
data = await api.execute("spacemolt_market/analyze_market", {"system": "Sol"})
prices = json.loads(data)
best = max(prices, key=lambda p: p["profit_margin"])
result = f"Best trade: {best['item']} — {best['profit_margin']:.1%} margin"
```

This avoids loading thousands of records into the LLM context (99 % token saving).

### 3. Context Compaction
When messages exceed 55 % of the context window:
1. Older messages are split at turn boundaries
2. The LLM summarises them into bullet points
3. The summary replaces the old messages

### 4. YAML Output
All API results are formatted as YAML (more compact than JSON).

## Configuration

Copy `config.example.yaml` to `config.yaml`:

```yaml
cloud_model: "anthropic/claude-sonnet-4-20250514"
local_model: "ollama/qwen3:8b"
api_url: "https://game.spacemolt.com/api/v2"
session_name: "default"
backend: "auto"
```

## Project Structure

```
spacemolt_commander_python/
├── spacemolt/
│   ├── __init__.py         # Package metadata
│   ├── cli.py              # Click CLI (run / service / status)
│   ├── commander.py        # Outer loop + system prompt builder
│   ├── loop.py             # Inner tool-calling loop
│   ├── tools.py            # Tool dispatcher (local + remote)
│   ├── api.py              # Async SpaceMolt REST client
│   ├── schema.py           # OpenAPI command discovery
│   ├── llm_router.py       # Hybrid LLM routing (cloud + local)
│   ├── compaction.py       # Context compaction logic
│   ├── code_executor.py    # Sandboxed code execution (AST-validated)
│   ├── session.py          # Credential & TODO persistence
│   ├── models.py           # Pydantic data models + tool schemas
│   ├── ui.py               # Rich terminal output
│   └── prompt.md           # SpaceMolt gameplay guide
├── sessions/               # Per-session state (credentials, TODO, handoff)
├── config.example.yaml     # Example configuration
├── pyproject.toml          # Build configuration
├── requirements.txt        # Dependencies
└── README.md
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes* | Anthropic API key |
| `OPENAI_API_KEY` | Alt* | OpenAI API key |
| `GROQ_API_KEY` | Alt* | Groq API key |
| `ABACUS_API_KEY` | Alt* | Abacus.AI API key |

*At least one cloud API key is required unless using `--backend local` exclusively.

## License

MIT
