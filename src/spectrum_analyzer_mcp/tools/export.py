"""Export and file tools (CSV, screenshot, trace data)."""

import csv
import io
import logging
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from mcp.types import TextContent, Tool

from ..safety.validators import sanitize_scpi_param, validate_safe_path
from ._connection import _get_sa
from ._registry import _format_result

logger = logging.getLogger(__name__)


def get_export_tools() -> list[Tool]:
    """Get export tool definitions."""
    return [
        Tool(
            name="sa_save_trace_csv",
            description="Save trace data to CSV file",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to save CSV file",
                    },
                    "trace_number": {
                        "type": "integer",
                        "description": "Trace number (default: 1)",
                        "default": 1,
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["filepath"],
            },
        ),
        Tool(
            name="sa_save_screenshot",
            description="Save instrument screenshot (sends HCOPy command to instrument)",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path on instrument to save screenshot",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["filepath"],
            },
        ),
        Tool(
            name="sa_export_trace_data",
            description="Export trace data as JSON (frequencies, amplitudes, metadata)",
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
            name="sa_save_trace_json",
            description="Save trace data to JSON file with instrument metadata",
            inputSchema={
                "type": "object",
                "properties": {
                    "filepath": {
                        "type": "string",
                        "description": "Path to save JSON file",
                    },
                    "trace_number": {
                        "type": "integer",
                        "description": "Trace number (default: 1)",
                        "default": 1,
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["filepath"],
            },
        ),
    ]


async def _handle_save_trace_csv(args: dict[str, Any]) -> list[TextContent]:
    """Save trace data to a CSV file.

    Args:
        args: filepath, trace_number (default 1), host, port.

    Returns:
        Filepath, number of points, and save confirmation.

    SCPI: TRAC:DATA? TRACEn (to read trace before saving).
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    trace = await sa.get_trace_data(args.get("trace_number", 1))

    filepath = validate_safe_path(args["filepath"], Path.cwd())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Frequency_Hz", "Amplitude_dBm"])
    for freq, amp in zip(trace.frequencies, trace.amplitudes):
        writer.writerow([freq, amp])

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="") as f:
        f.write(output.getvalue())

    return _format_result(
        {
            "filepath": str(filepath),
            "num_points": trace.num_points,
            "saved": True,
        }
    )


async def _handle_save_screenshot(args: dict[str, Any]) -> list[TextContent]:
    """Save instrument screenshot to a file on the instrument.

    Args:
        args: filepath (path on instrument), host, port.

    Returns:
        Filepath and save confirmation.

    SCPI: HCOP:DEV:LANG PNG, MMEM:NAME, HCOP:IMM.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    filepath = args["filepath"]
    safe_filepath = sanitize_scpi_param(filepath)
    safe_filepath = safe_filepath.replace("'", "\\'")
    await sa.scpi_send("HCOP:DEV:LANG PNG")
    await sa.scpi_send(f"MMEM:NAME '{safe_filepath}'")
    await sa.scpi_send("HCOP:IMM")
    return _format_result(
        {
            "filepath": filepath,
            "screenshot_saved": True,
        }
    )


async def _handle_export_trace_data(args: dict[str, Any]) -> list[TextContent]:
    """Export trace data as JSON in the tool response.

    Args:
        args: trace_number (default 1), host, port.

    Returns:
        Full trace data dict (frequencies, amplitudes, metadata).

    SCPI: TRAC:DATA? TRACEn.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    trace = await sa.get_trace_data(args.get("trace_number", 1))
    return _format_result(trace.to_dict())


async def _handle_save_trace_json(args: dict[str, Any]) -> list[TextContent]:
    """Save trace data to a JSON file with instrument metadata.

    Args:
        args: filepath, trace_number (default 1), host, port.

    Returns:
        Filepath, number of points, and save confirmation.

    SCPI: TRAC:DATA? TRACEn, *IDN?.
    """
    import json

    sa = await _get_sa(args.get("host"), args.get("port"))
    trace = await sa.get_trace_data(args.get("trace_number", 1))

    filepath = validate_safe_path(args["filepath"], Path.cwd())

    data = trace.to_dict()
    if sa.info:
        data["instrument"] = sa.info.to_dict()

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2, default=str)

    return _format_result(
        {
            "filepath": str(filepath),
            "num_points": trace.num_points,
            "saved": True,
        }
    )


HANDLERS: dict[str, Callable[..., Coroutine]] = {
    "sa_save_trace_csv": _handle_save_trace_csv,
    "sa_save_screenshot": _handle_save_screenshot,
    "sa_export_trace_data": _handle_export_trace_data,
    "sa_save_trace_json": _handle_save_trace_json,
}
