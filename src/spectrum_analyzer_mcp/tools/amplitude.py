"""Amplitude control tools."""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from mcp.types import TextContent, Tool

from ._connection import _get_sa
from ._registry import _format_result

logger = logging.getLogger(__name__)


def get_amplitude_tools() -> list[Tool]:
    """Get amplitude control tool definitions."""
    return [
        Tool(
            name="sa_set_reference_level",
            description="Set reference level (top of display) in dBm",
            inputSchema={
                "type": "object",
                "properties": {
                    "level_dbm": {
                        "type": "number",
                        "description": "Reference level in dBm",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["level_dbm"],
            },
        ),
        Tool(
            name="sa_set_attenuation",
            description="Set RF input attenuation in dB",
            inputSchema={
                "type": "object",
                "properties": {
                    "attenuation_db": {
                        "type": "number",
                        "description": "Attenuation in dB (0-75)",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["attenuation_db"],
            },
        ),
        Tool(
            name="sa_set_preamp",
            description="Enable or disable the internal preamplifier",
            inputSchema={
                "type": "object",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "description": "True to enable, False to disable",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["enabled"],
            },
        ),
        Tool(
            name="sa_set_scale",
            description="Set Y-axis scale in dB/division",
            inputSchema={
                "type": "object",
                "properties": {
                    "db_per_div": {
                        "type": "number",
                        "description": "dB per division (e.g. 10)",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["db_per_div"],
            },
        ),
    ]


async def _handle_set_reference_level(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_reference_level(args["level_dbm"])
    return _format_result({"reference_level_dbm": args["level_dbm"]})


async def _handle_set_attenuation(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_attenuation(args["attenuation_db"])
    return _format_result({"attenuation_db": args["attenuation_db"]})


async def _handle_set_preamp(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_preamp(args["enabled"])
    return _format_result({"preamp_enabled": args["enabled"]})


async def _handle_set_scale(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_scale(args["db_per_div"])
    return _format_result({"scale_db_per_div": args["db_per_div"]})


HANDLERS: dict[str, Callable[..., Coroutine]] = {
    "sa_set_reference_level": _handle_set_reference_level,
    "sa_set_attenuation": _handle_set_attenuation,
    "sa_set_preamp": _handle_set_preamp,
    "sa_set_scale": _handle_set_scale,
}
