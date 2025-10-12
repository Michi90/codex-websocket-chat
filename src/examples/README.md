# Examples

Complete demos showing Codex Client usage patterns.

## Setup

**Prerequisites**: Python 3.11+, uv, Codex CLI, Node.js (for MCP demos)

```bash
# Install dependencies
cd src/examples
uv sync

# Authenticate
uv run codex-client login
```

## Examples

### Interactive Chat

Multi-turn conversation with streaming responses, reasoning traces, and command execution.

```bash
uv run interactive/main.py
```

Try prompts like "Introduce yourself", "Create a fibonacci function", or "What's the current time?"

### MCP Transport

Tests MCP server connectivity using stdio and HTTP transports.

```bash
uv run mcp/main.py
```

Automatically runs connectivity tests and basic tool operations with the Everything MCP Server.

### Weather Assistant

Custom MCP tool implementation with wttr.in weather API. Demonstrates `BaseTool`, `@tool()` decorator, and stateful tools.

```bash
# Scripted demo (5 scenarios)
uv run weather/main.py

# Interactive mode
uv run weather/main.py --interactive
```

**Scripted scenarios**: Current weather, forecasts, comparisons, travel planning, state management

**Interactive mode**: Ask your own weather questions conversationally

## Troubleshooting

**"codex: command not found"**

Install Codex CLI and add to PATH: https://docs.anthropic.com/en/docs/claude-code

**"Authentication required"**

```bash
uv run codex-client login
```

**"npx: command not found" (MCP demos)**

Install Node.js: https://nodejs.org/

**"ModuleNotFoundError: No module named 'codex_client'"**

```bash
uv sync
```

## Structure

```
interactive/main.py    # Streaming event handling, multi-turn chat
mcp/main.py           # Stdio and HTTP transport tests
weather/              # Complete custom tool implementation
  ├── main.py         # Scripted and interactive modes
  ├── tool.py         # BaseTool with @tool() methods
  ├── weather.py      # wttr.in API client
  └── prompt.py       # System prompts
```

## Learn More

See [main README](../../README.md) for API reference and basic usage patterns.
