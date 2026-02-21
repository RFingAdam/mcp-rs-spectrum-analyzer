"""Raw SCPI command tools."""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from mcp.types import CallToolResult, TextContent, Tool

from ..config import get_settings
from ._connection import _get_sa
from ._registry import _format_error, _format_result

logger = logging.getLogger(__name__)


def get_scpi_tools() -> list[Tool]:
    """Get raw SCPI tool definitions."""
    return [
        Tool(
            name="sa_scpi_send",
            description="Send raw SCPI command to spectrum analyzer (no response)",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "SCPI command string",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="sa_scpi_query",
            description="Send raw SCPI query and return response",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "SCPI query string (must end with ?)",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="sa_reset",
            description="Reset spectrum analyzer to factory defaults (*RST)",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_preset",
            description="Preset spectrum analyzer (SYST:PRES)",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
    ]


async def _handle_scpi_send(args: dict[str, Any]) -> list[TextContent] | CallToolResult:
    """Send a raw SCPI command (no response expected).

    Args:
        args: command (SCPI string), host, port.

    Returns:
        Confirmation that command was sent.

    Note:
        Blocked if SA_ALLOW_RAW_SCPI=false.
    """
    settings = get_settings()
    command = args["command"]

    if not settings.allow_raw_scpi:
        logger.warning("Raw SCPI send blocked (allow_raw_scpi=False): %s", command)
        return _format_error(
            ValueError("Raw SCPI commands are disabled. Set SA_ALLOW_RAW_SCPI=true to enable.")
        )

    logger.warning("Raw SCPI send: %s", command)

    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.scpi_send(command)
    return _format_result({"command": command, "sent": True})


async def _handle_scpi_query(args: dict[str, Any]) -> list[TextContent] | CallToolResult:
    """Send a raw SCPI query and return the response.

    Args:
        args: command (SCPI query ending with ?), host, port.

    Returns:
        Query command and instrument response string.

    Note:
        Blocked if SA_ALLOW_RAW_SCPI=false.
    """
    settings = get_settings()
    command = args["command"]

    if not settings.allow_raw_scpi:
        logger.warning("Raw SCPI query blocked (allow_raw_scpi=False): %s", command)
        return _format_error(
            ValueError("Raw SCPI commands are disabled. Set SA_ALLOW_RAW_SCPI=true to enable.")
        )

    logger.warning("Raw SCPI query: %s", command)

    sa = await _get_sa(args.get("host"), args.get("port"))
    response = await sa.scpi_query(command)
    return _format_result({"command": command, "response": response})


async def _handle_reset(args: dict[str, Any]) -> list[TextContent]:
    """Reset instrument to factory defaults.

    Args:
        args: host, port.

    Returns:
        Confirmation that reset was sent.

    SCPI: *RST.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.reset()
    return _format_result({"reset": True})


async def _handle_preset(args: dict[str, Any]) -> list[TextContent]:
    """Preset instrument to default measurement state.

    Args:
        args: host, port.

    Returns:
        Confirmation that preset was sent.

    SCPI: SYST:PRES.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.preset()
    return _format_result({"preset": True})


HANDLERS: dict[str, Callable[..., Coroutine]] = {
    "sa_scpi_send": _handle_scpi_send,
    "sa_scpi_query": _handle_scpi_query,
    "sa_reset": _handle_reset,
    "sa_preset": _handle_preset,
}
