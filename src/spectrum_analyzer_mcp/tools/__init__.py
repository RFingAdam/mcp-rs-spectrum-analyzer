"""MCP tool definitions and handlers for spectrum analyzer operations.

This package splits the tool implementations into category modules.
Server.py only needs: ``from .tools import get_tools, handle_tool``
"""

from collections.abc import Callable, Coroutine

from mcp.types import Tool

from ._registry import handle_tool  # noqa: F401 – re-exported for server.py
from .amplitude import HANDLERS as _AMP_HANDLERS
from .amplitude import get_amplitude_tools
from .bandwidth import HANDLERS as _BW_HANDLERS
from .bandwidth import get_bandwidth_tools
from .connection import HANDLERS as _CONN_HANDLERS
from .connection import get_connection_tools
from .export import HANDLERS as _EXPORT_HANDLERS
from .export import get_export_tools
from .frequency import HANDLERS as _FREQ_HANDLERS
from .frequency import get_frequency_tools
from .limits_tools import HANDLERS as _LIMIT_HANDLERS
from .limits_tools import get_limit_tools
from .markers import HANDLERS as _MARKER_HANDLERS
from .markers import get_marker_tools
from .measurements import HANDLERS as _MEAS_HANDLERS
from .measurements import get_measurement_tools
from .scpi import HANDLERS as _SCPI_HANDLERS
from .scpi import get_scpi_tools
from .state_tools import HANDLERS as _STATE_HANDLERS
from .state_tools import get_state_tools
from .sweep import HANDLERS as _SWEEP_HANDLERS
from .sweep import get_sweep_tools
from .system import HANDLERS as _SYS_HANDLERS
from .system import get_system_tools
from .templates_tools import HANDLERS as _TMPL_HANDLERS
from .templates_tools import get_template_tools
from .trace import HANDLERS as _TRACE_HANDLERS
from .trace import get_trace_tools

# Aggregate all handlers into one dict
_ALL_HANDLERS: dict[str, Callable[..., Coroutine]] = {}
for _h in (
    _CONN_HANDLERS,
    _FREQ_HANDLERS,
    _AMP_HANDLERS,
    _BW_HANDLERS,
    _TRACE_HANDLERS,
    _MARKER_HANDLERS,
    _MEAS_HANDLERS,
    _SWEEP_HANDLERS,
    _EXPORT_HANDLERS,
    _SCPI_HANDLERS,
    _TMPL_HANDLERS,
    _LIMIT_HANDLERS,
    _STATE_HANDLERS,
    _SYS_HANDLERS,
):
    _ALL_HANDLERS.update(_h)


def _get_all_handlers() -> dict[str, Callable[..., Coroutine]]:
    """Return the aggregated handlers dict (called by _registry.handle_tool)."""
    return _ALL_HANDLERS


def get_tools() -> list[Tool]:
    """Get all MCP tool definitions."""
    tools: list[Tool] = []
    tools.extend(get_connection_tools())
    tools.extend(get_frequency_tools())
    tools.extend(get_amplitude_tools())
    tools.extend(get_bandwidth_tools())
    tools.extend(get_trace_tools())
    tools.extend(get_marker_tools())
    tools.extend(get_measurement_tools())
    tools.extend(get_sweep_tools())
    tools.extend(get_export_tools())
    tools.extend(get_scpi_tools())
    tools.extend(get_template_tools())
    tools.extend(get_limit_tools())
    tools.extend(get_state_tools())
    tools.extend(get_system_tools())
    return tools


# Re-export locks and internal state for tests that need them
from ._connection import _connection_lock  # noqa: E402, F401
from .limits_tools import _measurement_lock  # noqa: E402, F401
from .templates_tools import _current_template, _template_lock  # noqa: E402, F401

__all__ = [
    "get_tools",
    "handle_tool",
    "_get_all_handlers",
    "_connection_lock",
    "_template_lock",
    "_measurement_lock",
    "_current_template",
]
