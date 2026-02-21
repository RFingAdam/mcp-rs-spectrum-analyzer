"""Trace data and configuration tools."""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from mcp.types import TextContent, Tool

from ..models.sa_types import DetectorType, TraceMode
from ._connection import _get_sa
from ._registry import _format_result

logger = logging.getLogger(__name__)


def get_trace_tools() -> list[Tool]:
    """Get trace tool definitions."""
    return [
        Tool(
            name="sa_get_trace_data",
            description="Read trace data (frequencies and amplitudes) from instrument",
            inputSchema={
                "type": "object",
                "properties": {
                    "trace_number": {
                        "type": "integer",
                        "description": "Trace number (1-6, default: 1)",
                        "default": 1,
                    },
                    "include_raw_data": {
                        "type": "boolean",
                        "description": "Include raw frequency/amplitude arrays (default: false)",
                        "default": False,
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_set_trace_mode",
            description="Set trace mode: WRITe (clear/write), MAXHold, MINHold, AVERage",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "description": "Trace mode",
                        "enum": ["WRITe", "MAXHold", "MINHold", "AVERage"],
                    },
                    "trace_number": {
                        "type": "integer",
                        "description": "Trace number (default: 1)",
                        "default": 1,
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["mode"],
            },
        ),
        Tool(
            name="sa_set_averaging_count",
            description="Set trace averaging count (1 = off)",
            inputSchema={
                "type": "object",
                "properties": {
                    "count": {
                        "type": "integer",
                        "description": "Number of averages (1 = off)",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["count"],
            },
        ),
        Tool(
            name="sa_clear_trace",
            description="Clear/reset trace to clear-write mode",
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
            name="sa_set_detector",
            description=(
                "Set detector type: POS (peak), RMS, AVER (average), "
                "SAMP (sample), QPE (quasi-peak), NEG (negative peak)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "detector": {
                        "type": "string",
                        "description": "Detector type",
                        "enum": ["POS", "RMS", "AVER", "SAMP", "QPE", "NEG"],
                    },
                    "trace_number": {
                        "type": "integer",
                        "description": "Trace number (default: 1)",
                        "default": 1,
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["detector"],
            },
        ),
    ]


async def _handle_get_trace_data(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    trace = await sa.get_trace_data(args.get("trace_number", 1))
    if args.get("include_raw_data", False):
        return _format_result(trace.to_dict())
    return _format_result(trace.to_summary())


async def _handle_set_trace_mode(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    mode = TraceMode(args["mode"])
    await sa.set_trace_mode(mode, args.get("trace_number", 1))
    return _format_result({"trace_mode": args["mode"]})


async def _handle_set_averaging_count(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_averaging_count(args["count"])
    return _format_result({"averaging_count": args["count"]})


async def _handle_clear_trace(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.clear_trace(args.get("trace_number", 1))
    return _format_result({"trace_cleared": True})


async def _handle_set_detector(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    detector = DetectorType(args["detector"])
    await sa.set_detector(detector, args.get("trace_number", 1))
    return _format_result({"detector_type": args["detector"]})


HANDLERS: dict[str, Callable[..., Coroutine]] = {
    "sa_get_trace_data": _handle_get_trace_data,
    "sa_set_trace_mode": _handle_set_trace_mode,
    "sa_set_averaging_count": _handle_set_averaging_count,
    "sa_clear_trace": _handle_clear_trace,
    "sa_set_detector": _handle_set_detector,
}
