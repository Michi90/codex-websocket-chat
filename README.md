# Codex Client

Lightweight Python wrapper for the Codex CLI. Stream chats, handle reasoning/tool events, and build custom MCP tools.

## Installation

```bash
pip install codex-client
```

Requires `codex` executable on your PATH.

## Authentication (CLI)

```bash
# Login via browser
codex-client login

# Export credentials (copy to another machine)
codex-client read

# Import credentials
codex-client set "<payload>"

# Clear credentials
codex-client logout
```

## Basic Usage

```python
import asyncio
from codex_client import (
    AssistantMessageStream,
    Client,
    CodexChatConfig,
    CodexProfile,
    ReasoningEffort,
    SandboxMode,
)

async def main():
    config = CodexChatConfig(
        profile=CodexProfile(
            model="gpt-5",
            reasoning_effort=ReasoningEffort.MINIMAL,
            sandbox=SandboxMode.WORKSPACE_WRITE,
        )
    )

    async with Client() as client:
        chat = await client.create_chat("Write a Python fibonacci function", config=config)

        # Stream responses
        async for event in chat:
            if isinstance(event, AssistantMessageStream):
                async for chunk in event.stream():
                    print(chunk, end="", flush=True)

        # Get final response
        final = await chat.get()
        print(f"\n\nFinal: {final}")

        # Continue conversation
        await chat.resume("Now make it recursive")

asyncio.run(main())
```

## Custom Tools

```python
from codex_client import BaseTool, tool

class CalculatorTool(BaseTool):
    @tool()
    async def add(self, a: float, b: float) -> dict:
        """Add two numbers."""
        return {"result": a + b}

    @tool()
    async def multiply(self, a: float, b: float) -> dict:
        """Multiply two numbers."""
        return {"result": a * b}

# Use the tool
async def main():
    with CalculatorTool() as calc:
        config = CodexChatConfig(
            profile=CodexProfile(model="gpt-5"),
            mcp_servers=[calc.config()]
        )

        async with Client() as client:
            chat = await client.create_chat("What is 15 + 27?", config=config)
            async for event in chat:
                if isinstance(event, AssistantMessageStream):
                    async for chunk in event.stream():
                        print(chunk, end="", flush=True)

asyncio.run(main())
```

## Authentication (Code)

```python
from codex_client.auth import CodexAuth

auth = CodexAuth()

# Trigger login flow (opens browser)
session = auth.login()
print(f"Visit: {session.url}")
success = session.wait()  # Blocks until user completes login

# Or import existing credentials
auth.set("<payload-from-codex-client-read>")

# Verify credentials
token = auth.read()
```

## Examples

See `src/examples/` for complete demos:

- **Interactive Chat** - Multi-turn conversations with streaming
- **MCP Transport** - HTTP and stdio MCP server connectivity
- **Weather Assistant** - Custom tool with state management

```bash
cd src/examples
uv sync
uv run weather/main.py
```
