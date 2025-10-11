"""Tool package - MCP tool framework for Codex Client.

Framework for creating custom MCP tools with HTTP server support.
Users manage their own data explicitly - no automatic state management.
"""

from .base import BaseTool
from .decorator import tool

# BaseTool is the concrete HTTP-based MCP tool implementation
__all__ = ["BaseTool", "tool"]
