"""Instrument state management tools."""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from mcp.types import TextContent, Tool

from ..safety.validators import validate_safe_path
from ..state import InstrumentState, StateManager
from ._connection import _get_sa
from ._registry import _format_result

logger = logging.getLogger(__name__)

# Global state manager
_state_manager = StateManager()


def get_state_tools() -> list[Tool]:
    """Get state management tool definitions."""
    return [
        Tool(
            name="sa_save_state",
            description="Save current instrument state to file",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "State name (used as filename)",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Optional notes about this state",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="sa_load_state",
            description="Load and restore instrument state from file",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "State name to load",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="sa_get_full_state",
            description="Get complete current instrument state (all settings)",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
    ]


async def _handle_save_state(args: dict[str, Any]) -> list[TextContent]:
    """Save current instrument state to a JSON file.

    Args:
        args: name (state filename), notes (optional), host, port.

    Returns:
        State name, filepath, and configuration summary.

    SCPI: Multiple queries to capture all instrument settings.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    state = await _state_manager.capture_state(sa)

    if args.get("notes"):
        state.notes = args["notes"]

    state_dir = _state_manager.state_directory
    filepath = validate_safe_path(f"{args['name']}.json", state_dir)
    state.save(filepath)

    return _format_result(
        {
            "state_saved": args["name"],
            "filepath": str(filepath),
            "summary": state.get_summary(),
        }
    )


async def _handle_load_state(args: dict[str, Any]) -> list[TextContent]:
    """Load and restore instrument state from a JSON file.

    Args:
        args: name (state filename), host, port.

    Returns:
        State name and configuration summary. Rolls back on failure.

    SCPI: Multiple commands to restore all instrument settings.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))

    state_dir = _state_manager.state_directory
    filepath = validate_safe_path(f"{args['name']}.json", state_dir)

    state = InstrumentState.load(filepath)
    await _state_manager.restore_state(sa, state)

    return _format_result(
        {
            "state_loaded": args["name"],
            "summary": state.get_summary(),
        }
    )


async def _handle_get_full_state(args: dict[str, Any]) -> list[TextContent]:
    """Get complete current instrument configuration.

    Args:
        args: host, port.

    Returns:
        Full instrument state (frequency, amplitude, bandwidth, trace, markers).

    SCPI: Multiple queries to read all instrument settings.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    state = await _state_manager.capture_state(sa)
    return _format_result(state.to_dict())


HANDLERS: dict[str, Callable[..., Coroutine]] = {
    "sa_save_state": _handle_save_state,
    "sa_load_state": _handle_load_state,
    "sa_get_full_state": _handle_get_full_state,
}
