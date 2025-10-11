"""Codex Client - A minimal library for programmatic control of Codex.

Example:
    from codex_client import Client

    async with Client() as client:
        chat = await client.create_chat("Hello, Codex!")

        async for event in chat:
            print(event)

        await chat.resume("Can you elaborate?")
"""

from .client import Client
from .chat import Chat
from .config import (
    CodexChatConfig,
    CodexMcpServer,
    CodexStdioMcpServer,
    CodexHttpMcpServer,
    CodexProfile,
    ApprovalPolicy,
    SandboxMode,
    ReasoningEffort,
    Verbosity,
)
from .exceptions import (
    CodexError,
    ConnectionError,
    ChatError,
    ToolError,
    AuthenticationError,
    MiddlewareError,
)
from .event import (
    AgentMessageDeltaEvent,
    AgentMessageEvent,
    AgentReasoningDeltaEvent,
    AgentReasoningEvent,
    AgentReasoningSectionBreakEvent,
    CodexEventMsg,
    Duration,
    EventMetadata,
    ExecCommandBeginEvent,
    ExecCommandEndEvent,
    ExecCommandOutputDeltaEvent,
    ExecOutputStream,
    McpToolCallBeginEvent,
    McpToolCallEndEvent,
    SessionConfiguredEvent,
    TaskCompleteEvent,
    TaskStartedEvent,
    TokenCountEvent,
    parse_event,
)
from .structured import (
    AggregatedChatEvent,
    AssistantMessageStream,
    CommandOutputChunk,
    CommandStream,
    ReasoningStream,
    structured,
)
from .middleware import setup_mcp_middleware, get_middleware

__version__ = "0.1.0"

__all__ = [
    # Core SDK
    "Client",
    "Chat",
    "CodexError",
    "ConnectionError",
    "ChatError",
    "ToolError",
    "AuthenticationError",
    "MiddlewareError",

    # Config
    "CodexChatConfig",
    "CodexProfile",
    "CodexMcpServer",
    "CodexStdioMcpServer",
    "CodexHttpMcpServer",
    "ApprovalPolicy",
    "SandboxMode",
    "ReasoningEffort",
    "Verbosity",

    # Events
    "AgentMessageDeltaEvent",
    "AgentMessageEvent",
    "AgentReasoningDeltaEvent",
    "AgentReasoningEvent",
    "AgentReasoningSectionBreakEvent",
    "CodexEventMsg",
    "Duration",
    "EventMetadata",
    "ExecCommandBeginEvent",
    "ExecCommandEndEvent",
    "ExecCommandOutputDeltaEvent",
    "ExecOutputStream",
    "McpToolCallBeginEvent",
    "McpToolCallEndEvent",
    "SessionConfiguredEvent",
    "TaskCompleteEvent",
    "TaskStartedEvent",
    "TokenCountEvent",
    "parse_event",

    # Structured stream helpers
    "structured",
    "AggregatedChatEvent",
    "AssistantMessageStream",
    "CommandOutputChunk",
    "CommandStream",
    "ReasoningStream",

    # Middleware
    "setup_mcp_middleware",
    "get_middleware",
]
