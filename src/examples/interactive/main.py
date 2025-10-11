#!/usr/bin/env python3
"""
Interactive Codex Client demo showing streaming responses, reasoning traces,
and command execution across multiple chat turns.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

# Ensure the repository src/ directory is importable when running directly
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codex_client import (  # type: ignore
    AssistantMessageStream,
    Client,
    CodexChatConfig,
    CodexProfile,
    CommandStream,
    ReasoningStream,
    ReasoningEffort,
    SandboxMode,
    SessionConfiguredEvent,
    TaskCompleteEvent,
    TaskStartedEvent,
    TokenCountEvent,
    Verbosity,
)
from codex_client.event import McpToolCallBeginEvent, McpToolCallEndEvent  # type: ignore

WELCOME_MESSAGE = """\
🤖 Codex Client Interactive Chat
================================

This demo highlights:
- Streaming assistant messages with live updates
- Reasoning traces as Codex thinks
- Command executions triggered by the model
- Support for multi-turn conversations via `chat.resume`

Press Enter on an empty prompt to exit.
"""


async def _stream_turn(chat) -> Optional[str]:
    """
    Stream a single Codex turn, printing aggregated outputs to the console.

    Returns the final assistant reply for the turn once available.
    """
    final_reply: Optional[str] = None

    async for event in chat:
        if isinstance(event, AssistantMessageStream):
            print("\n🧠 Assistant:", end=" ", flush=True)
            chunks = []
            async for chunk in event.stream():
                chunks.append(chunk)
                print(chunk, end="", flush=True)
            final_reply = "".join(chunks).strip() or None
            print("\n")
            continue

        if isinstance(event, ReasoningStream):
            print("🧐 Reasoning:", end=" ", flush=True)
            async for chunk in event.stream():
                print(chunk, end="", flush=True)
            print()
            continue

        if isinstance(event, CommandStream):
            command_str = " ".join(event.command)
            print(f"\n⚡ Command: {command_str}")
            async for chunk in event.stream():
                if chunk.text is not None:
                    print(chunk.text, end="", flush=True)
                else:
                    print(f"[binary chunk: {len(chunk.data)} bytes]", flush=True)
            if event.exit_code is not None:
                duration = event.duration.total_seconds() if event.duration else None
                status = "✅" if event.exit_code == 0 else "❌"
                details = f"{status} exit {event.exit_code}"
                if duration is not None:
                    details += f" ({duration:.2f}s)"
                print(details)
            print()
            continue

        if isinstance(event, SessionConfiguredEvent):
            print(
                f"\n🔧 Session configured with model '{event.model}'"
                + (f" | reasoning: {event.reasoning_effort.value}" if event.reasoning_effort else "")
            )
            continue

        if isinstance(event, TaskStartedEvent):
            context = (
                f"{event.model_context_window:,} tokens"
                if event.model_context_window is not None
                else "unknown context"
            )
            print(f"\n🚀 Task started ({context})")
            continue

        if isinstance(event, TaskCompleteEvent):
            print("🎉 Task complete")
            continue

        if isinstance(event, TokenCountEvent):
            total = event.info.total_token_usage.total_tokens if event.info else None
            delta = event.info.last_token_usage.total_tokens if event.info else None
            if total is not None and delta is not None:
                print(f"💰 Tokens used: {total:,} total (+{delta:,} this turn)")
            continue

        if isinstance(event, McpToolCallBeginEvent):
            args = ", ".join(f"{k}={v}" for k, v in event.invocation.arguments.items())
            print(f"\n🔧 Tool call: {event.invocation.server}.{event.invocation.tool}({args})")
            continue

        if isinstance(event, McpToolCallEndEvent):
            duration = event.duration.total_seconds()
            result_type = "Ok" if hasattr(event.result, "Ok") else "Err"
            print(f"🔧 Tool finished in {duration:.2f}s ({result_type})")
            continue

    # Ensure the final assistant response is available before returning
    message = await chat.get()
    return final_reply or message


async def run_interactive_chat() -> None:
    """Entry point for running the interactive chat loop."""
    print(WELCOME_MESSAGE)

    profile = CodexProfile(
        model="gpt-5",
        reasoning_effort=ReasoningEffort.MINIMAL,
        verbosity=Verbosity.MEDIUM,
        sandbox=SandboxMode.WORKSPACE_WRITE,
    )
    config = CodexChatConfig(profile=profile)

    try:
        initial_prompt = input("📝 Enter your prompt (default: Introduce yourself): ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n👋 Goodbye!")
        return

    if not initial_prompt:
        initial_prompt = "Introduce yourself."
        print(f"Using default prompt: {initial_prompt}")

    async with Client() as client:
        chat = await client.create_chat(initial_prompt, config=config)

        turn = 1
        while True:
            print(f"\n=== Turn {turn} ===")
            final_reply = await _stream_turn(chat)
            if final_reply is not None:
                preview = (final_reply[:250] + "...") if len(final_reply) > 250 else final_reply
                print(f"📬 Final reply: {preview}")

            try:
                follow_up = input("\n💬 Next prompt (leave blank to exit): ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n👋 Goodbye!")
                break

            if not follow_up:
                print("👋 Session ended.")
                break

            await chat.resume(follow_up)
            turn += 1


def main() -> None:
    try:
        asyncio.run(run_interactive_chat())
    except KeyboardInterrupt:
        print("\n👋 Interrupted.")


if __name__ == "__main__":
    main()
