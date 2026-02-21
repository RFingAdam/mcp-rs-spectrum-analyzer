"""Frequency control tools."""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from mcp.types import TextContent, Tool

from ._connection import _get_sa
from ._registry import _format_result

logger = logging.getLogger(__name__)


def get_frequency_tools() -> list[Tool]:
    """Get frequency control tool definitions."""
    return [
        Tool(
            name="sa_set_center_span",
            description="Set center frequency and span",
            inputSchema={
                "type": "object",
                "properties": {
                    "center_hz": {
                        "type": "number",
                        "description": "Center frequency in Hz",
                    },
                    "span_hz": {
                        "type": "number",
                        "description": "Frequency span in Hz",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["center_hz", "span_hz"],
            },
        ),
        Tool(
            name="sa_set_start_stop",
            description="Set start and stop frequencies",
            inputSchema={
                "type": "object",
                "properties": {
                    "start_hz": {
                        "type": "number",
                        "description": "Start frequency in Hz",
                    },
                    "stop_hz": {
                        "type": "number",
                        "description": "Stop frequency in Hz",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["start_hz", "stop_hz"],
            },
        ),
        Tool(
            name="sa_set_frequency_step",
            description="Set frequency step size for manual tuning",
            inputSchema={
                "type": "object",
                "properties": {
                    "step_hz": {
                        "type": "number",
                        "description": "Frequency step in Hz",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["step_hz"],
            },
        ),
        Tool(
            name="sa_full_span",
            description="Set full span (maximum frequency range)",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
    ]


async def _handle_set_center_span(args: dict[str, Any]) -> list[TextContent]:
    """Set center frequency and span.

    Args:
        args: center_hz, span_hz, host, port.

    Returns:
        Confirmed center frequency and span values.

    SCPI: SENS:FREQ:CENT, SENS:FREQ:SPAN.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_center_span(args["center_hz"], args["span_hz"])
    return _format_result(
        {
            "center_frequency_hz": args["center_hz"],
            "span_hz": args["span_hz"],
        }
    )


async def _handle_set_start_stop(args: dict[str, Any]) -> list[TextContent]:
    """Set start and stop frequencies.

    Args:
        args: start_hz, stop_hz, host, port.

    Returns:
        Confirmed start and stop frequency values.

    SCPI: SENS:FREQ:STAR, SENS:FREQ:STOP.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_start_stop(args["start_hz"], args["stop_hz"])
    return _format_result(
        {
            "start_frequency_hz": args["start_hz"],
            "stop_frequency_hz": args["stop_hz"],
        }
    )


async def _handle_set_frequency_step(args: dict[str, Any]) -> list[TextContent]:
    """Set frequency step size for manual tuning.

    Args:
        args: step_hz, host, port.

    Returns:
        Confirmed frequency step value.

    SCPI: SENS:FREQ:CENT:STEP.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_frequency_step(args["step_hz"])
    return _format_result({"frequency_step_hz": args["step_hz"]})


async def _handle_full_span(args: dict[str, Any]) -> list[TextContent]:
    """Set analyzer to full span (maximum frequency range).

    Args:
        args: host, port.

    Returns:
        Confirmation that full span was set.

    SCPI: SENS:FREQ:SPAN:FULL.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.full_span()
    return _format_result({"full_span": True})


HANDLERS: dict[str, Callable[..., Coroutine]] = {
    "sa_set_center_span": _handle_set_center_span,
    "sa_set_start_stop": _handle_set_start_stop,
    "sa_set_frequency_step": _handle_set_frequency_step,
    "sa_full_span": _handle_full_span,
}
