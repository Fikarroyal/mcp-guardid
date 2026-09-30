"""
MCP client abstraction sitting underneath the MCP Gateway.

Two implementations of the same `McpClient` interface:

  - `InProcessMcpClient` (default): calls the shared execution core
    (`mcp_server.tools.executor`) directly, in-process. Zero IPC overhead,
    deterministic for demos/tests. This is what `mcp_server/server.py` wraps
    with a real MCP transport -- both share one execution core so behavior
    never diverges between "demo mode" and "real MCP mode".

  - `StdioMcpClient` (production-realistic): spawns
    `python -m mcp_server.server` as a subprocess and speaks the actual MCP
    protocol over stdio using the official SDK's `ClientSession`. Use this
    when the tool server runs as a genuinely separate process/host (the
    normal production topology), e.g. by setting `MCP_CLIENT_MODE=stdio`.

The Gateway (app/mcp/gateway.py) and everything above it depends only on
`McpClient.call_tool()` -- it does not know or care which transport is live.
"""
from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from contextlib import AsyncExitStack
from typing import Any

from mcp_server.tools.executor import ToolExecutionError, get_executor


class McpClient(ABC):
    @abstractmethod
    async def call_tool(self, name: str, arguments: dict[str, Any], timeout: int) -> dict[str, Any]: ...

    async def aclose(self) -> None:
        return None


class InProcessMcpClient(McpClient):
    async def call_tool(self, name: str, arguments: dict[str, Any], timeout: int) -> dict[str, Any]:
        started = time.time()
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(get_executor().execute, name, arguments), timeout=timeout
            )
            return {
                "tool_name": name,
                "status": "success",
                "latency_ms": round((time.time() - started) * 1000, 2),
                "result": result,
            }
        except asyncio.TimeoutError:
            return {"tool_name": name, "status": "timeout",
                    "latency_ms": round((time.time() - started) * 1000, 2), "result": None}
        except ToolExecutionError as exc:
            return {"tool_name": name, "status": "failed",
                    "latency_ms": round((time.time() - started) * 1000, 2), "result": None, "error": str(exc)}


class StdioMcpClient(McpClient):
    """Spawns the real MCP server as a subprocess and speaks MCP over stdio."""

    def __init__(self) -> None:
        self._stack: AsyncExitStack | None = None
        self._session = None
        self._lock = asyncio.Lock()

    async def _ensure_session(self) -> None:
        if self._session is not None:
            return
        # Imported lazily -- only needed when this transport is actually selected.
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        self._stack = AsyncExitStack()
        params = StdioServerParameters(command="python3", args=["-m", "mcp_server.server"])
        read_stream, write_stream = await self._stack.enter_async_context(stdio_client(params))
        session = await self._stack.enter_async_context(ClientSession(read_stream, write_stream))
        await session.initialize()
        self._session = session

    async def call_tool(self, name: str, arguments: dict[str, Any], timeout: int) -> dict[str, Any]:
        async with self._lock:
            await self._ensure_session()
        started = time.time()
        try:
            result = await asyncio.wait_for(
                self._session.call_tool(name, arguments), timeout=timeout  # type: ignore[union-attr]
            )
            return {"tool_name": name, "status": "success",
                    "latency_ms": round((time.time() - started) * 1000, 2), "result": result}
        except TimeoutError:
            return {"tool_name": name, "status": "timeout",
                    "latency_ms": round((time.time() - started) * 1000, 2), "result": None}

    async def aclose(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
            self._session = None


_client_instance: McpClient | None = None


def get_mcp_client() -> McpClient:
    global _client_instance
    if _client_instance is None:
        from app.core.config import get_settings

        mode = getattr(get_settings(), "MCP_CLIENT_MODE", "inprocess")
        _client_instance = StdioMcpClient() if mode == "stdio" else InProcessMcpClient()
    return _client_instance
