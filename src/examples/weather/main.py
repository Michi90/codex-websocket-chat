#!/usr/bin/env python3
"""
Weather demo using Codex Client and an MCP weather tool backed by wttr.in.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

# Ensure codex_client package can be imported when running directly
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from codex_client import (  # type: ignore
    Client,
    CodexChatConfig,
    CodexProfile,
    ReasoningEffort,
    SandboxMode,
    SessionConfiguredEvent,
    TaskCompleteEvent,
    TaskStartedEvent,
    TokenCountEvent,
    Verbosity,
)
from codex_client.event import McpToolCallBeginEvent, McpToolCallEndEvent  # type: ignore
from codex_client.structured import (  # type: ignore
    AssistantMessageStream,
    CommandStream,
    ReasoningStream,
    structured,
)

from prompt import WELCOME_MESSAGE, WEATHER_SYSTEM_PROMPT
from tool import WeatherTool


async def _stream_weather_turn(chat) -> Optional[str]:
    """Stream a single Codex turn for the weather demo."""
    final_reply: Optional[str] = None

    async for event in structured(chat):
        if isinstance(event, AssistantMessageStream):
            print("\n🤖 Weather Assistant:\n", end="", flush=True)
            chunks = []
            async for chunk in event.stream():
                chunks.append(chunk)
                print(chunk, end="", flush=True)
            final_reply = "".join(chunks).strip() or None
            print("\n")
            continue

        if isinstance(event, ReasoningStream):
            print("🧐 Reasoning:")
            async for chunk in event.stream():
                print(f"  {chunk}")
            continue

        if isinstance(event, CommandStream):
            command_str = " ".join(event.command)
            print(f"\n⚡ Executing command: {command_str}")
            async for chunk in event.stream():
                if chunk.text is not None:
                    print(chunk.text, end="", flush=True)
                else:
                    print(f"[binary output: {len(chunk.data)} bytes]", flush=True)
            if event.exit_code is not None:
                status = "✅" if event.exit_code == 0 else "❌"
                duration = event.duration.total_seconds() if event.duration else None
                summary = f"{status} exit {event.exit_code}"
                if duration is not None:
                    summary += f" in {duration:.2f}s"
                print(summary)
            continue

        if isinstance(event, SessionConfiguredEvent):
            details = f" model={event.model}"
            if event.reasoning_effort:
                details += f" reasoning={event.reasoning_effort.value}"
            print(f"\n🔧 Session configured:{details}")
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
                print(f"💰 Tokens: {total:,} total (+{delta:,} this turn)")
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

    message = await chat.get()
    return final_reply or message


def _format_weather_prompt(user_prompt: str) -> str:
    """Combine system priming with the user prompt."""
    return (
        f"{WEATHER_SYSTEM_PROMPT}\n\n"
        f"Task:\n{user_prompt}"
    )


def _build_config(weather_tool: WeatherTool) -> CodexChatConfig:
    profile = CodexProfile(
        model="gpt-5",
        reasoning_effort=ReasoningEffort.MINIMAL,
        verbosity=Verbosity.HIGH,
        sandbox=SandboxMode.WORKSPACE_WRITE,
    )
    return CodexChatConfig(
        profile=profile,
        mcp_servers=[weather_tool.config()],
    )


async def run_weather_demo() -> bool:
    """Run scripted weather demos highlighting different tool flows."""
    print("\n" + "=" * 60)
    print("WEATHER DEMO")
    print("=" * 60)

    scenarios = [
        (
            "🌤️ Demo 1: Current Weather Conditions",
            "Please get the current weather conditions for Tokyo, Japan. "
            "Provide comprehensive information including temperature, humidity, wind, "
            "and practical advice about what to expect.",
        ),
        (
            "🌦️ Demo 2: Weather Forecast",
            "Now get a 3-day weather forecast for London, England. "
            "Help me understand what the weather will be like and what I should plan for.",
        ),
        (
            "🔄 Demo 3: Weather Comparison",
            "Compare the current weather between New York City and Los Angeles. "
            "Which city has better weather right now and why?",
        ),
        (
            "✈️ Demo 4: Travel Weather Planning",
            "I'm planning to travel from Paris to Sydney next week. "
            "Can you help me understand what weather to expect and what to pack? "
            "Also, add both cities to my favorites list for future reference.",
        ),
        (
            "📊 Demo 5: State Management",
            "Show me my weather query history and favorite locations. "
            "What locations have I been checking the weather for?",
        ),
    ]

    try:
        with WeatherTool() as weather_tool:
            config = _build_config(weather_tool)

            async with Client() as client:
                for heading, prompt in scenarios:
                    print(f"\n{heading}")
                    print("-" * len(heading))
                    print(f"📝 Prompt: {prompt}")

                    chat_prompt = _format_weather_prompt(prompt)
                    chat = await client.create_chat(chat_prompt, config=config)
                    response = await _stream_weather_turn(chat)
                    preview = (response[:400] + "...") if len(response) > 400 else response
                    print(f"\n📬 Assistant reply preview:\n{preview}\n")

            print("\n" + "=" * 60)
            print(f"✅ Weather tool invoked {weather_tool.query_count} times")
            print(f"⭐ Favorites stored: {len(weather_tool.favorite_locations)}")
            print(f"🕓 Last location queried: {weather_tool.last_location}")
            print("=" * 60)
            return weather_tool.query_count > 0

    except Exception as exc:  # noqa: BLE001
        print(f"\n❌ Error during weather demo: {exc}")
        return False


async def run_interactive_mode() -> None:
    """Run the weather assistant in interactive mode for user input."""
    print(WELCOME_MESSAGE)

    with WeatherTool() as weather_tool:
        config = _build_config(weather_tool)
        async with Client() as client:
            chat = None
            print("\n🤖 Weather assistant is ready! Type 'quit' to exit.")
            print("💡 Try: 'What's the weather in Paris?' or 'Compare NYC and LA weather'")

            while True:
                try:
                    user_input = input("\n📝 Your weather question: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n👋 Goodbye!")
                    break

                if user_input.lower() in {"quit", "exit", "q"}:
                    print("👋 Goodbye!")
                    break
                if not user_input:
                    continue

                if chat is None:
                    initial_prompt = _format_weather_prompt(f"User question: {user_input}")
                    chat = await client.create_chat(initial_prompt, config=config)
                else:
                    await chat.resume(f"User question: {user_input}")

                response = await _stream_weather_turn(chat)
                if response:
                    print(f"🤖 Assistant:\n{response}\n")


async def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        await run_interactive_mode()
    else:
        success = await run_weather_demo()
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Interrupted.")
