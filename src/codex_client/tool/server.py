"""HTTP server management for MCP tools using FastMCP."""

import inspect
import socket
import threading
import time
from typing import Any, Callable, List, Optional, Tuple

import httpx
from fastmcp import FastMCP

from ..exceptions import ConnectionError as CodexConnectionError


class MCPServer:
    """HTTP server for MCP tool endpoints using FastMCP."""

    def __init__(self, tool_instance: Any, log_level: str = "ERROR"):
        """
        Initialize MCP server for a tool instance.

        Args:
            tool_instance: Tool instance to serve
            log_level: Logging level for FastMCP (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        self.tool_instance = tool_instance
        self._server_thread: Optional[threading.Thread] = None
        self._ready = False
        self._log_level = log_level
        self._mcp_app: Optional[FastMCP] = None

    def _pick_port(self, host: str) -> int:
        """Pick an available port on the given host."""
        try:
            with socket.socket() as s:
                s.bind((host, 0))
                port = s.getsockname()[1]
                return port
        except socket.error as e:
            raise CodexConnectionError(f"Failed to bind to host {host}: {e}") from e
        except Exception as e:
            raise CodexConnectionError(f"Socket operation failed: {e}") from e

    def _collect_tool_methods(self) -> List[Tuple[Callable, dict]]:
        """Collect all methods marked with @tool decorator."""
        methods = []

        for name in dir(self.tool_instance):
            # Skip private/magic methods
            if name.startswith('_'):
                continue

            # Check if it's a property (skip properties)
            static_attr = inspect.getattr_static(type(self.tool_instance), name, None)
            if isinstance(static_attr, property):
                continue

            try:
                member = getattr(self.tool_instance, name)
                if inspect.ismethod(member) and getattr(member, "__mcp_tool__", False):
                    meta = getattr(member, "__mcp_meta__", {})
                    methods.append((member, meta))
            except (AttributeError, TypeError):
                # Skip attributes that can't be accessed
                continue

        return methods

    def _create_mcp_app(self) -> FastMCP:
        """Create FastMCP application with tool endpoints."""
        mcp = FastMCP(name=self.tool_instance.__class__.__name__)

        # Add health check endpoint
        @mcp.custom_route("/health", methods=["GET"])
        async def health(_):
            from starlette.responses import PlainTextResponse
            return PlainTextResponse("OK", status_code=200)

        # Register all tool methods
        for method, meta in self._collect_tool_methods():
            # Use FastMCP's @tool decorator to register the method
            mcp.tool(name=meta["name"], description=meta["description"])(method)

        return mcp

    def _run_server_thread(self, host: str, port: int):
        """Run MCP server in a separate thread."""
        self._mcp_app = self._create_mcp_app()
        # FastMCP's run() handles the HTTP server internally
        self._mcp_app.run(
            transport="http",
            host=host,
            port=port,
            show_banner=False,
            log_level=self._log_level.lower()
        )

    def start(self, host: str = "127.0.0.1", port: Optional[int] = None) -> Tuple[str, int]:
        """
        Start the MCP server.

        Args:
            host: Host to bind to
            port: Port to bind to (auto-select if None)

        Returns:
            Tuple of (host, port) the server is running on
        """
        if self._server_thread:
            raise RuntimeError("Server already running")

        actual_port = port or self._pick_port(host)

        self._server_thread = threading.Thread(
            target=self._run_server_thread,
            args=(host, actual_port),
            daemon=True,
        )
        self._server_thread.start()
        self._wait_ready(host, actual_port)
        return host, actual_port

    def _wait_ready(self, host: str, port: int, timeout: float = 10.0):
        """Wait for server to be ready by checking health endpoint."""
        health_url = f"http://{host}:{port}/health"
        start = time.time()
        last_err = None

        while time.time() - start < timeout:
            try:
                r = httpx.get(health_url, timeout=0.5)
                if r.status_code == 200:
                    self._ready = True
                    return
            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_err = e
            except Exception as e:
                last_err = e
            time.sleep(0.1)

        raise CodexConnectionError(
            f"MCP server not ready at {health_url} after {timeout}s (last error: {last_err})"
        )

    @property
    def is_ready(self) -> bool:
        """Check if server is ready to accept requests."""
        return self._ready

    @property
    def mcp_app(self) -> Optional[FastMCP]:
        """Get the FastMCP application instance (for debugging/monitoring)."""
        return self._mcp_app

    def cleanup(self):
        """Clean up server resources.

        Note: This cleanup is currently incomplete. FastMCP doesn't provide
        a public API to gracefully stop the underlying uvicorn server, so:
        - The HTTP server continues running on the bound port
        - Resources are not fully released
        - The daemon thread continues executing

        This should be improved when FastMCP exposes proper shutdown hooks.
        Tracking issue: https://github.com/jlowin/fastmcp/issues/TBD

        Current workaround: The thread is marked as daemon so it won't block
        process exit, but resources won't be cleaned up until the process ends.
        """
        # Thread is daemon, will be cleaned up automatically
        self._ready = False
        self._server_thread = None
        self._mcp_app = None
        # TODO: Add proper server shutdown when FastMCP supports it
        # Ideal: self._mcp_app.shutdown() or similar
