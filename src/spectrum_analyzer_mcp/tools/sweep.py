"""Sweep and trigger control tools."""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from mcp.types import TextContent, Tool

from ._connection import _get_sa
from ._registry import _format_result

logger = logging.getLogger(__name__)


def get_sweep_tools() -> list[Tool]:
    """Get sweep/trigger tool definitions."""
    return [
        Tool(
            name="sa_single_sweep",
            description="Trigger a single sweep and wait for completion",
            inputSchema={
                "type": "object",
                "properties": {
                    "timeout": {
                        "type": "number",
                        "description": "Timeout in seconds",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_continuous_sweep",
            description="Enable or disable continuous sweep mode",
            inputSchema={
                "type": "object",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "description": "True for continuous, False for single",
                        "default": True,
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_set_trigger",
            description=(
                "Configure trigger source: IMM (free run), "
                "EXT (external), VID (video), IFP (IF power)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Trigger source",
                        "enum": ["IMM", "EXT", "VID", "IFP", "RFP"],
                    },
                    "level": {
                        "type": "number",
                        "description": "Trigger level (for video/IF power triggers)",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["source"],
            },
        ),
    ]


async def _handle_single_sweep(args: dict[str, Any]) -> list[TextContent]:
    """Trigger a single sweep and wait for completion.

    Args:
        args: timeout (seconds), host, port.

    Returns:
        Confirmation that sweep completed.

    SCPI: INIT:CONT OFF, INIT;*WAI.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.single_sweep(args.get("timeout"))
    return _format_result({"sweep_complete": True})


async def _handle_continuous_sweep(args: dict[str, Any]) -> list[TextContent]:
    """Enable or disable continuous sweep mode.

    Args:
        args: enabled (bool, default True), host, port.

    Returns:
        Confirmed continuous sweep state.

    SCPI: INIT:CONT ON|OFF.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.continuous_sweep(args.get("enabled", True))
    return _format_result({"continuous_sweep": args.get("enabled", True)})


async def _handle_set_trigger(args: dict[str, Any]) -> list[TextContent]:
    """Configure trigger source and level.

    Args:
        args: source (IMM|EXT|VID|IFP|RFP), level (for video/IF triggers), host, port.

    Returns:
        Confirmed trigger source.

    SCPI: TRIG:SOUR, TRIG:LEV.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_trigger(args["source"], args.get("level"))
    return _format_result({"trigger_source": args["source"]})


HANDLERS: dict[str, Callable[..., Coroutine]] = {
    "sa_single_sweep": _handle_single_sweep,
    "sa_continuous_sweep": _handle_continuous_sweep,
    "sa_set_trigger": _handle_set_trigger,
}
