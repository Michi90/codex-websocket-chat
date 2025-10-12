#!/usr/bin/env python3
"""
MCP transport demo showcasing stdio and HTTP connectivity with Codex Client.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
from typing import Optional

from codex_client import (
    AssistantMessageStream,
    Client,
    CodexChatConfig,
    CodexHttpMcpServer,
    CodexProfile,
    CodexStdioMcpServer,
    CommandStream,
    ReasoningStream,
    ReasoningEffort,
    SandboxMode,
    Verbosity,
)
from codex_client.event import McpToolCallBeginEvent, McpToolCallEndEvent

from prompt import MCP_SYSTEM_PROMPT, WELCOME_MESSAGE, format_demo_output, get_demo_prompt


async def _stream_response(chat) -> str:
    """Stream assistant output for a single Codex turn and return the final message."""
    assistant_chunks: list[str] = []

    async for event in chat:
        if isinstance(event, AssistantMessageStream):
            async for chunk in event.stream():
                assistant_chunks.append(chunk)
            continue

        if isinstance(event, ReasoningStream):
            print("🧐 Reasoning stream:")
            async for chunk in event.stream():
                print(f"  {chunk}")
            continue

        if isinstance(event, CommandStream):
            command_str = " ".join(event.command)
            print(f"⚡ Command executed: {command_str}")
            async for chunk in event.stream():
                if chunk.text:
                    print(chunk.text, end="", flush=True)
                else:
                    print(f"[binary output: {len(chunk.data)} bytes]", flush=True)
            if event.exit_code is not None:
                status = "✅" if event.exit_code == 0 else "❌"
                duration = event.duration.total_seconds() if event.duration else None
                details = f"{status} exit {event.exit_code}"
                if duration is not None:
                    details += f" in {duration:.2f}s"
                print(details)
            continue

        if isinstance(event, McpToolCallBeginEvent):
            args = ", ".join(f"{k}={v}" for k, v in event.invocation.arguments.items())
            print(f"🔧 Tool call: {event.invocation.server}.{event.invocation.tool}({args})")
            continue

        if isinstance(event, McpToolCallEndEvent):
            duration = event.duration.total_seconds()
            result_type = "Ok" if hasattr(event.result, "Ok") else "Err"
            print(f"🔧 Tool finished in {duration:.2f}s ({result_type})")
            continue

    final_message = await chat.get()
    return final_message or "".join(assistant_chunks).strip()


def _compose_prompt(task_prompt: str) -> str:
    """Combine the system priming with a scenario-specific instruction."""
    return f"{MCP_SYSTEM_PROMPT}\n\nTask:\n{task_prompt}"


async def _run_scenario(
    config: CodexChatConfig,
    scenario_key: str,
    *,
    heading: Optional[str] = None,
) -> str:
    """Create a chat for the given scenario and return the assistant response."""
    task_prompt = get_demo_prompt(scenario_key)
    if heading:
        print(f"\n{heading}")
        print("-" * len(heading))
    print(f"📝 Prompt: {task_prompt}")
    prompt = _compose_prompt(task_prompt)

    async with Client() as client:
        chat = await client.create_chat(prompt, config=config)
        response = await _stream_response(chat)

    return response


def _build_stdio_config() -> CodexChatConfig:
    profile = CodexProfile(
        model="gpt-5",
        reasoning_effort=ReasoningEffort.MINIMAL,
        verbosity=Verbosity.MEDIUM,
        sandbox=SandboxMode.WORKSPACE_WRITE,
    )
    stdio_server = CodexStdioMcpServer(
        name="everything-stdio",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-everything"],
    )
    return CodexChatConfig(
        profile=profile,
        mcp_servers=[stdio_server],
    )


def _build_http_config() -> CodexChatConfig:
    profile = CodexProfile(
        model="gpt-5",
        reasoning_effort=ReasoningEffort.MINIMAL,
        verbosity=Verbosity.MEDIUM,
        sandbox=SandboxMode.WORKSPACE_WRITE,
    )
    http_server = CodexHttpMcpServer(
        name="everything-http",
        url="http://localhost:3001/mcp",
    )
    return CodexChatConfig(
        profile=profile,
        mcp_servers=[http_server],
    )


async def run_stdio_demo() -> bool:
    """Execute the stdio transport demo."""
    print("\n" + "=" * 60)
    print("📡 STDIO TRANSPORT DEMO")
    print("=" * 60)
    print("Using: npx -y @modelcontextprotocol/server-everything\n")

    config = _build_stdio_config()
    success = True

    for scenario in ("connectivity", "basic_math"):
        try:
            response = await _run_scenario(
                config,
                scenario,
                heading=f"Scenario: {scenario}",
            )
            print(format_demo_output("stdio", scenario, response))
        except Exception as exc:  # noqa: BLE001
            success = False
            print(f"❌ Scenario '{scenario}' failed: {exc}")

    if success:
        print("✅ Stdio transport demo completed successfully!")
    return success


async def run_http_demo() -> bool:
    """Execute the HTTP transport demo (requires local Everything server)."""
    print("\n" + "=" * 60)
    print("🌐 HTTP TRANSPORT DEMO")
    print("=" * 60)
    print("Using: npx -y @modelcontextprotocol/server-everything streamableHttp\n")

    server_process: Optional[subprocess.Popen[str]] = None
    try:
        print("🚀 Starting Everything HTTP server...")
        server_process = subprocess.Popen(
            ["npx", "-y", "@modelcontextprotocol/server-everything", "streamableHttp"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        print("⏳ Waiting for server to become ready...")
        await asyncio.sleep(3)

        config = _build_http_config()
        success = True

        for scenario in ("connectivity", "basic_math"):
            try:
                response = await _run_scenario(
                    config,
                    scenario,
                    heading=f"Scenario: {scenario}",
                )
                print(format_demo_output("http", scenario, response))
            except Exception as exc:  # noqa: BLE001
                success = False
                print(f"❌ Scenario '{scenario}' failed: {exc}")

        if success:
            print("✅ HTTP transport demo completed successfully!")
        return success

    finally:
        if server_process:
            print("🧹 Shutting down HTTP server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_process.kill()


async def main() -> None:
    print(WELCOME_MESSAGE)

    stdio_success = await run_stdio_demo()
    http_success = await run_http_demo()

    completed = sum(1 for success in (stdio_success, http_success) if success)
    print("\n" + "=" * 60)
    print(f"📊 DEMO SUMMARY: {completed}/2 transports completed successfully")
    print("=" * 60)

    if completed == 2:
        print("🎉 All MCP transport demos completed successfully!")
    else:
        print("⚠️ Some demos failed. Check the logs above for details.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Interrupted.")
