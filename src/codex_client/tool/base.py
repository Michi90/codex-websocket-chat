"""Base class for MCP tools with HTTP server support."""

from typing import Optional

from ..config import CodexHttpMcpServer
from .server import MCPServer


class BaseTool:
    """
    Base class for MCP tools with HTTP server support.

    Tools are stateless by design - manage your own data explicitly.
    The MCP server starts automatically when the tool is instantiated.

    Usage:
        # Basic usage (server cleaned up by context manager)
        class MyTool(BaseTool):
            def __init__(self):
                super().__init__()
                # Manage your own data explicitly
                self.my_data = []

            @tool()
            async def my_async_method(self, param: str) -> dict:
                '''Async tool function'''
                return {"result": "success"}

        # Context manager usage (recommended for explicit resource management)
        with MyTool() as tool:
            config = tool.config()
            # Use the tool
        # Server automatically cleaned up here

        # Multiple tools
        with MyTool() as calc_tool, WeatherTool() as weather_tool:
            # Use both tools
            pass
        # Both servers cleaned up automatically
    """

    def __init__(self, host: str = "127.0.0.1", port: Optional[int] = None, *, log_level: str = "ERROR"):
        """
        Initialize the tool and automatically start the MCP server.

        Args:
            host: Host to bind to
            port: Port to bind to (auto-select if None)
            log_level: Logging level for FastMCP (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        # Server management only
        self._server: Optional[MCPServer] = None
        self._host: str = host
        self._port: Optional[int] = None

        # Auto-start server
        self._server = MCPServer(self, log_level=log_level)
        self._host, self._port = self._server.start(host, port)

    def config(self) -> CodexHttpMcpServer:
        """Get MCP server configuration as CodexHttpMcpServer instance."""
        return CodexHttpMcpServer(
            name=self.name(),
            url=self.connection_url
        )

    def name(self) -> str:
        """Get tool/server name."""
        return self.__class__.__name__.lower()

    @property
    def connection_url(self) -> str:
        """Get MCP connection URL."""
        if self._port is None:
            raise RuntimeError("Server has been shut down")
        return f"http://{self._host}:{self._port}/mcp"

    @property
    def health_url(self) -> str:
        """Get health check URL."""
        if self._port is None:
            raise RuntimeError("Server has been shut down")
        return f"http://{self._host}:{self._port}/health"

    def __enter__(self):
        """Enter context manager - tool server is already running from __init__."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - cleanup server resources."""
        # Parameters are required by context manager protocol but unused here
        _ = exc_type, exc_val, exc_tb
        self.shutdown()
        return False  # Don't suppress exceptions

    def shutdown(self):
        """
        Explicitly stop the MCP server and clean up resources.

        This is the recommended way to clean up the server.
        """
        if hasattr(self, '_server') and self._server:
            self._server.cleanup()
            self._server = None
            self._port = None

    def __del__(self):
        """Clean up server resources when tool is destroyed.

        Warning: Relying on __del__ for cleanup is unreliable.
        Use 'with' statement or call shutdown() explicitly.
        """
        if hasattr(self, '_server') and self._server:
            import warnings
            warnings.warn(
                f"{self.__class__.__name__} was not properly closed. "
                "Use 'with' statement or call shutdown() explicitly.",
                ResourceWarning,
                stacklevel=2
            )
            self._server.cleanup()
