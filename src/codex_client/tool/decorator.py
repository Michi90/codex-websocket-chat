"""MCP tool method decorator for marking methods as tools."""

import asyncio
from typing import Callable, Optional


def tool(name: Optional[str] = None) -> Callable:
    """
    Decorator to mark methods as MCP tools.

    Args:
        name: Tool name (defaults to function name)

    The tool description is automatically extracted from the function's docstring.
    If no docstring exists, a default description based on the function name is used.

    Note: Only async functions are supported in this minimal implementation.

    Example:
        @tool()
        async def my_tool(self, param: str) -> dict:
            '''Tool description from docstring'''
            return {"result": param}
    """
    def decorator(fn: Callable) -> Callable:
        # Validate async function
        if not asyncio.iscoroutinefunction(fn):
            raise TypeError(
                f"Tool '{name or fn.__name__}' must be an async function. "
                "Use 'async def' to define the method."
            )

        # Mark as MCP tool
        setattr(fn, "__mcp_tool__", True)
        setattr(fn, "__mcp_meta__", {
            "name": name or fn.__name__,
            "description": fn.__doc__ or f"{fn.__name__} function",
        })
        return fn

    return decorator
