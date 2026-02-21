"""System management tools (error queue, display, calibration)."""

import base64
import logging
from collections.abc import Callable, Coroutine
from typing import Any

from mcp.types import TextContent, Tool

from ._connection import _get_sa
from ._registry import _format_result

logger = logging.getLogger(__name__)


def get_system_tools() -> list[Tool]:
    """Get system management tool definitions."""
    return [
        Tool(
            name="sa_get_error_queue",
            description="Read all errors from the instrument error queue",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_set_display_update",
            description="Enable/disable display updates (disable for faster remote operation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "description": "True to enable, False to disable display updates",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["enabled"],
            },
        ),
        Tool(
            name="sa_run_alignment",
            description="Run internal self-alignment/calibration (may take minutes)",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_set_sweep_points",
            description="Set number of sweep trace points",
            inputSchema={
                "type": "object",
                "properties": {
                    "points": {
                        "type": "integer",
                        "description": "Number of sweep points (e.g. 1001, 8192)",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["points"],
            },
        ),
        Tool(
            name="sa_get_sweep_points",
            description="Get current number of sweep trace points",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_capture_screenshot",
            description="Capture instrument screenshot and return as base64 PNG",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "description": "Image format (PNG, BMP, JPG)",
                        "default": "PNG",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
    ]


async def _handle_get_error_queue(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    errors = await sa.get_error_queue()
    return _format_result(
        {
            "error_count": len(errors),
            "errors": errors,
            "queue_empty": len(errors) == 0,
        }
    )


async def _handle_set_display_update(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    enabled = args["enabled"]
    await sa.set_display_update(enabled)
    return _format_result({"display_update": "enabled" if enabled else "disabled"})


async def _handle_run_alignment(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    result = await sa.run_alignment()
    passed = result.strip() == "0"
    return _format_result(
        {
            "alignment_result": "passed" if passed else "check_required",
            "raw_response": result,
        }
    )


async def _handle_set_sweep_points(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    points = args["points"]
    await sa.set_sweep_points(points)
    return _format_result({"sweep_points_set": points})


async def _handle_get_sweep_points(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    points = await sa.get_sweep_points()
    return _format_result({"sweep_points": points})


async def _handle_capture_screenshot(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    fmt = args.get("format", "PNG")
    data = await sa.capture_screenshot(fmt)
    b64 = base64.b64encode(data).decode("ascii")
    return _format_result(
        {
            "format": fmt,
            "size_bytes": len(data),
            "data_base64": b64,
        }
    )


HANDLERS: dict[str, Callable[..., Coroutine]] = {
    "sa_get_error_queue": _handle_get_error_queue,
    "sa_set_display_update": _handle_set_display_update,
    "sa_run_alignment": _handle_run_alignment,
    "sa_set_sweep_points": _handle_set_sweep_points,
    "sa_get_sweep_points": _handle_get_sweep_points,
    "sa_capture_screenshot": _handle_capture_screenshot,
}
