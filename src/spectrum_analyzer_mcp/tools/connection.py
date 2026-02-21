"""Connection management tools for spectrum analyzer MCP server."""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from mcp.types import TextContent, Tool

from ..config import get_settings
from ..driver import RSSpectrumAnalyzerDriver
from ..exceptions import SpectrumAnalyzerError
from ._connection import _close_sa, _get_sa
from ._registry import _format_result

logger = logging.getLogger(__name__)


# =============================================================================
# Tool Definitions
# =============================================================================


def get_connection_tools() -> list[Tool]:
    """Get connection-related MCP tool definitions."""
    return [
        Tool(
            name="sa_discover",
            description="Scan for spectrum analyzers on the network",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "Host to scan (default: from settings)",
                    },
                    "start_port": {
                        "type": "integer",
                        "description": "Start port (default: 5025)",
                        "default": 5025,
                    },
                    "end_port": {
                        "type": "integer",
                        "description": "End port (default: 5035)",
                        "default": 5035,
                    },
                },
            },
        ),
        Tool(
            name="sa_connect",
            description="Connect to spectrum analyzer via host:port or VISA resource string",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "Instrument hostname or IP",
                    },
                    "port": {
                        "type": "integer",
                        "description": "TCP port (default: 5025)",
                    },
                    "resource": {
                        "type": "string",
                        "description": (
                            "VISA resource string (overrides host/port). "
                            "E.g. TCPIP::192.168.1.100::INSTR, "
                            "GPIB::20::INSTR, USB::0x0AAD::INSTR"
                        ),
                    },
                },
            },
        ),
        Tool(
            name="sa_disconnect",
            description="Disconnect from spectrum analyzer",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_identify",
            description=(
                "Get spectrum analyzer identification (*IDN?): "
                "manufacturer, model, serial, firmware"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_get_status",
            description="Get spectrum analyzer connection and configuration status",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
    ]


# =============================================================================
# Handler Implementations
# =============================================================================


async def _handle_discover(args: dict[str, Any]) -> list[TextContent]:
    settings = get_settings()
    host = args.get("host", settings.default_host)
    start_port = args.get("start_port", 5025)
    end_port = args.get("end_port", 5035)

    found = []
    for port in range(start_port, end_port + 1):
        try:
            sa = RSSpectrumAnalyzerDriver(host=host, port=port, timeout=settings.discovery_timeout)
            info = await sa.connect()
            found.append(
                {
                    "host": host,
                    "port": port,
                    "instrument": info.to_dict(),
                }
            )
            await sa.disconnect()
        except (OSError, SpectrumAnalyzerError) as e:
            logger.debug("No instrument at %s:%d: %s", host, port, e)

    if found:
        return _format_result({"found": found, "count": len(found)})
    return _format_result({"found": [], "count": 0, "message": "No instruments found"})


async def _handle_connect(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"), args.get("resource"))
    return _format_result(
        {
            "connected": True,
            "instrument": sa.info.to_dict() if sa.info else {},
            "family": sa.family.value if sa.family else "Unknown",
        }
    )


async def _handle_disconnect(args: dict[str, Any]) -> list[TextContent]:
    settings = get_settings()
    host = args.get("host", settings.default_host)
    port = args.get("port", settings.default_port)
    closed = await _close_sa(host, port)
    return _format_result({"disconnected": closed})


async def _handle_identify(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    return _format_result(sa.info.to_dict() if sa.info else {"error": "No info available"})


async def _handle_get_status(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    status = await sa.get_status()
    return _format_result(status)


# =============================================================================
# Handler Registry
# =============================================================================

HANDLERS: dict[str, Callable[..., Coroutine]] = {
    "sa_discover": _handle_discover,
    "sa_connect": _handle_connect,
    "sa_disconnect": _handle_disconnect,
    "sa_identify": _handle_identify,
    "sa_get_status": _handle_get_status,
}
