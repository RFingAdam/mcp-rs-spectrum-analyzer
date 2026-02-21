"""Limit line tools."""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from mcp.types import TextContent, Tool

from ..limits import LimitLine, LimitManager, LimitSegment
from ._connection import _get_sa
from ._registry import _format_result

logger = logging.getLogger(__name__)

# Global limit manager
_limit_manager = LimitManager()

# asyncio.Lock for limit/measurement state
_measurement_lock = asyncio.Lock()


def get_limit_tools() -> list[Tool]:
    """Get limit line tool definitions."""
    return [
        Tool(
            name="sa_define_limit",
            description="Define a limit line with frequency segments and max/min values",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Limit line name",
                    },
                    "segments": {
                        "type": "array",
                        "description": (
                            "Limit segments: [{start_freq_hz, stop_freq_hz, max_db, min_db, name}]"
                        ),
                        "items": {
                            "type": "object",
                            "properties": {
                                "start_freq_hz": {"type": "number"},
                                "stop_freq_hz": {"type": "number"},
                                "max_db": {"type": "number"},
                                "min_db": {"type": "number"},
                                "name": {"type": "string"},
                            },
                            "required": ["start_freq_hz", "stop_freq_hz"],
                        },
                    },
                    "description": {
                        "type": "string",
                        "description": "Limit description",
                    },
                },
                "required": ["name", "segments"],
            },
        ),
        Tool(
            name="sa_check_limits",
            description="Check current trace data against all defined limits",
            inputSchema={
                "type": "object",
                "properties": {
                    "trace_number": {
                        "type": "integer",
                        "description": "Trace number (default: 1)",
                        "default": 1,
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_clear_limits",
            description="Clear all defined limit lines",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="sa_list_limits",
            description="List all defined limit lines",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
    ]


async def _handle_define_limit(args: dict[str, Any]) -> list[TextContent]:
    """Define a limit line with frequency segments and max/min thresholds.

    Args:
        args: name, segments (list of start/stop/max/min), description.

    Returns:
        Limit name and number of segments defined.
    """
    segments = []
    for seg_data in args["segments"]:
        segments.append(
            LimitSegment(
                start_freq_hz=seg_data["start_freq_hz"],
                stop_freq_hz=seg_data["stop_freq_hz"],
                max_db=seg_data.get("max_db"),
                min_db=seg_data.get("min_db"),
                name=seg_data.get("name"),
            )
        )

    limit = LimitLine(
        name=args["name"],
        segments=segments,
        description=args.get("description", ""),
    )
    async with _measurement_lock:
        _limit_manager.add_limit(limit)

    return _format_result(
        {
            "limit_defined": args["name"],
            "num_segments": len(segments),
        }
    )


async def _handle_check_limits(args: dict[str, Any]) -> list[TextContent]:
    """Check current trace data against all defined limit lines.

    Args:
        args: trace_number (default 1), host, port.

    Returns:
        Overall pass/fail status and per-limit violation details.

    SCPI: TRAC:DATA? TRACEn (to read trace for comparison).
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    trace = await sa.get_trace_data(args.get("trace_number", 1))
    async with _measurement_lock:
        result = _limit_manager.get_overall_status(trace)
    return _format_result(result)


async def _handle_clear_limits(args: dict[str, Any]) -> list[TextContent]:
    """Clear all defined limit lines.

    Args:
        args: (none required).

    Returns:
        Confirmation that limits were cleared.
    """
    async with _measurement_lock:
        _limit_manager.clear_limits()
    return _format_result({"limits_cleared": True})


async def _handle_list_limits(args: dict[str, Any]) -> list[TextContent]:
    """List all defined limit lines with their segments.

    Args:
        args: (none required).

    Returns:
        List of limits with names, descriptions, and segment details.
    """
    async with _measurement_lock:
        names = _limit_manager.list_limits()
        limits_info = []
        for name in names:
            limit = _limit_manager.get_limit(name)
            if limit:
                limits_info.append(
                    {
                        "name": name,
                        "description": limit.description,
                        "num_segments": len(limit.segments),
                        "segments": [s.to_dict() for s in limit.segments],
                    }
                )
    return _format_result({"limits": limits_info, "count": len(limits_info)})


HANDLERS: dict[str, Callable[..., Coroutine]] = {
    "sa_define_limit": _handle_define_limit,
    "sa_check_limits": _handle_check_limits,
    "sa_clear_limits": _handle_clear_limits,
    "sa_list_limits": _handle_list_limits,
}
