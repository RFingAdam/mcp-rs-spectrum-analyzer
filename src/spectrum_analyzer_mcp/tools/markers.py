"""Marker tools."""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from mcp.types import TextContent, Tool

from ._connection import _get_sa
from ._registry import _format_result

logger = logging.getLogger(__name__)


def get_marker_tools() -> list[Tool]:
    """Get marker tool definitions."""
    return [
        Tool(
            name="sa_set_marker",
            description="Position a marker at a specific frequency",
            inputSchema={
                "type": "object",
                "properties": {
                    "frequency_hz": {
                        "type": "number",
                        "description": "Marker frequency in Hz",
                    },
                    "marker_number": {
                        "type": "integer",
                        "description": "Marker number (1-4, default: 1)",
                        "default": 1,
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["frequency_hz"],
            },
        ),
        Tool(
            name="sa_get_marker",
            description="Read marker position (frequency) and value (amplitude)",
            inputSchema={
                "type": "object",
                "properties": {
                    "marker_number": {
                        "type": "integer",
                        "description": "Marker number (1-4, default: 1)",
                        "default": 1,
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_peak_search",
            description="Find the peak signal on the trace and position marker there",
            inputSchema={
                "type": "object",
                "properties": {
                    "marker_number": {
                        "type": "integer",
                        "description": "Marker number (default: 1)",
                        "default": 1,
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_next_peak",
            description="Find next peak from current marker position",
            inputSchema={
                "type": "object",
                "properties": {
                    "direction": {
                        "type": "string",
                        "description": "Search direction: next, left, right",
                        "enum": ["next", "left", "right"],
                        "default": "next",
                    },
                    "marker_number": {
                        "type": "integer",
                        "description": "Marker number (default: 1)",
                        "default": 1,
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_marker_to_center",
            description="Set center frequency to current marker position",
            inputSchema={
                "type": "object",
                "properties": {
                    "marker_number": {
                        "type": "integer",
                        "description": "Marker number (default: 1)",
                        "default": 1,
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_marker_delta",
            description="Enable/disable delta marker mode for relative measurements",
            inputSchema={
                "type": "object",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "description": "Enable delta marker",
                        "default": True,
                    },
                    "marker_number": {
                        "type": "integer",
                        "description": "Marker number (default: 1)",
                        "default": 1,
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_marker_bandwidth",
            description="Measure N-dB bandwidth using marker function",
            inputSchema={
                "type": "object",
                "properties": {
                    "n_db": {
                        "type": "number",
                        "description": "Bandwidth criteria in dB (default: 3.0)",
                        "default": 3.0,
                    },
                    "marker_number": {
                        "type": "integer",
                        "description": "Marker number (default: 1)",
                        "default": 1,
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
    ]


async def _handle_set_marker(args: dict[str, Any]) -> list[TextContent]:
    """Position a marker at a specific frequency.

    Args:
        args: frequency_hz, marker_number (1-4, default 1), host, port.

    Returns:
        Marker data (frequency, amplitude) after positioning.

    SCPI: CALC:MARKn ON, CALC:MARKn:X.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_marker(args["frequency_hz"], args.get("marker_number", 1))
    marker = await sa.get_marker(args.get("marker_number", 1))
    return _format_result(marker.to_dict())


async def _handle_get_marker(args: dict[str, Any]) -> list[TextContent]:
    """Read current marker position and amplitude.

    Args:
        args: marker_number (1-4, default 1), host, port.

    Returns:
        Marker frequency (Hz) and amplitude (dBm).

    SCPI: CALC:MARKn:X?, CALC:MARKn:Y?.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    marker = await sa.get_marker(args.get("marker_number", 1))
    return _format_result(marker.to_dict())


async def _handle_peak_search(args: dict[str, Any]) -> list[TextContent]:
    """Find the peak signal on the trace.

    Args:
        args: marker_number (default 1), host, port.

    Returns:
        Marker data at peak position (frequency and amplitude).

    SCPI: CALC:MARKn:MAX.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    marker = await sa.peak_search(args.get("marker_number", 1))
    return _format_result(marker.to_dict())


async def _handle_next_peak(args: dict[str, Any]) -> list[TextContent]:
    """Find the next peak from current marker position.

    Args:
        args: direction (next|left|right), marker_number, host, port.

    Returns:
        Marker data at next peak position.

    SCPI: CALC:MARKn:MAX:NEXT / LEFT / RIGHT.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    marker = await sa.next_peak(
        args.get("marker_number", 1),
        args.get("direction", "next"),
    )
    return _format_result(marker.to_dict())


async def _handle_marker_to_center(args: dict[str, Any]) -> list[TextContent]:
    """Set center frequency to current marker position.

    Args:
        args: marker_number (default 1), host, port.

    Returns:
        Confirmation that center was set to marker.

    SCPI: CALC:MARKn:FUNC:CENT.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.marker_to_center(args.get("marker_number", 1))
    return _format_result({"marker_to_center": True})


async def _handle_marker_delta(args: dict[str, Any]) -> list[TextContent]:
    """Enable or disable delta marker mode.

    Args:
        args: enabled (bool, default True), marker_number, host, port.

    Returns:
        Confirmed delta marker state.

    SCPI: CALC:DELT:STAT ON|OFF.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_delta_marker(
        args.get("marker_number", 1),
        args.get("enabled", True),
    )
    return _format_result({"delta_marker_enabled": args.get("enabled", True)})


async def _handle_marker_bandwidth(args: dict[str, Any]) -> list[TextContent]:
    """Measure N-dB bandwidth using marker function.

    Args:
        args: n_db (default 3.0), marker_number, host, port.

    Returns:
        Bandwidth, center frequency, lower/upper frequencies, quality factor.

    SCPI: CALC:MARKn:FUNC:BWID:STAT ON, CALC:MARKn:FUNC:BWID:RES?.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    result = await sa.marker_bandwidth(
        args.get("n_db", 3.0),
        args.get("marker_number", 1),
    )
    return _format_result(result)


HANDLERS: dict[str, Callable[..., Coroutine]] = {
    "sa_set_marker": _handle_set_marker,
    "sa_get_marker": _handle_get_marker,
    "sa_peak_search": _handle_peak_search,
    "sa_next_peak": _handle_next_peak,
    "sa_marker_to_center": _handle_marker_to_center,
    "sa_marker_delta": _handle_marker_delta,
    "sa_marker_bandwidth": _handle_marker_bandwidth,
}
