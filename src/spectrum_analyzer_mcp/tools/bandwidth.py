"""Bandwidth and sweep time control tools."""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from mcp.types import TextContent, Tool

from ._connection import _get_sa
from ._registry import _format_result

logger = logging.getLogger(__name__)


def get_bandwidth_tools() -> list[Tool]:
    """Get bandwidth control tool definitions."""
    return [
        Tool(
            name="sa_set_rbw",
            description="Set resolution bandwidth (RBW)",
            inputSchema={
                "type": "object",
                "properties": {
                    "rbw_hz": {
                        "type": "number",
                        "description": "Resolution bandwidth in Hz",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["rbw_hz"],
            },
        ),
        Tool(
            name="sa_set_vbw",
            description="Set video bandwidth (VBW)",
            inputSchema={
                "type": "object",
                "properties": {
                    "vbw_hz": {
                        "type": "number",
                        "description": "Video bandwidth in Hz",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["vbw_hz"],
            },
        ),
        Tool(
            name="sa_set_sweep_time",
            description="Set sweep time in seconds",
            inputSchema={
                "type": "object",
                "properties": {
                    "time_s": {
                        "type": "number",
                        "description": "Sweep time in seconds",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["time_s"],
            },
        ),
        Tool(
            name="sa_auto_coupling",
            description="Enable auto-coupling for RBW, VBW, and sweep time",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
    ]


async def _handle_set_rbw(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_rbw(args["rbw_hz"])
    return _format_result({"rbw_hz": args["rbw_hz"]})


async def _handle_set_vbw(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_vbw(args["vbw_hz"])
    return _format_result({"vbw_hz": args["vbw_hz"]})


async def _handle_set_sweep_time(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_sweep_time(args["time_s"])
    return _format_result({"sweep_time_s": args["time_s"]})


async def _handle_auto_coupling(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.auto_coupling()
    return _format_result({"auto_coupling": True})


HANDLERS: dict[str, Callable[..., Coroutine]] = {
    "sa_set_rbw": _handle_set_rbw,
    "sa_set_vbw": _handle_set_vbw,
    "sa_set_sweep_time": _handle_set_sweep_time,
    "sa_auto_coupling": _handle_auto_coupling,
}
