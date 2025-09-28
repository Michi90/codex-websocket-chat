"""Centralised exception hierarchy for the Codex Client."""


class CodexError(Exception):
    """Base exception for all Codex Client errors."""


class ConnectionError(CodexError):
    """Raised when there's an issue connecting to the Codex MCP server."""


class ChatError(CodexError):
    """Raised when there's an issue with chat handling or retrieval."""


class ToolError(CodexError):
    """Raised when a tool call fails."""


class AuthenticationError(CodexError):
    """Raised when authentication helpers cannot complete successfully."""


class MiddlewareError(CodexError):
    """Raised when middleware components fail to process Codex events."""
