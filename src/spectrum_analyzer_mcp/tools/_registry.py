"""Tool handler registry and shared utilities."""

import json
import logging
from typing import Any

from mcp.types import CallToolResult, TextContent

from ..exceptions import SpectrumAnalyzerError

logger = logging.getLogger(__name__)


def _format_result(result: Any) -> list[TextContent]:
    """Format result as MCP TextContent."""
    if isinstance(result, (dict, list)):
        text = json.dumps(result, indent=2, default=str)
    else:
        text = str(result)
    return [TextContent(type="text", text=text)]


def _format_error(error: Exception) -> CallToolResult:
    """Format error as MCP CallToolResult with isError=True."""
    return CallToolResult(
        content=[TextContent(type="text", text=f"Error: {error}")],
        isError=True,
    )


async def handle_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Route tool call to appropriate handler.

    Returns a CallToolResult. On success, isError=False; on failure, isError=True.
    The MCP SDK recognises CallToolResult and passes it through directly.
    """
    # Import here to avoid circular imports at module level
    from . import _get_all_handlers

    handlers = _get_all_handlers()

    try:
        handler = handlers.get(name)
        if handler is None:
            return _format_error(ValueError(f"Unknown tool: {name}"))
        content = await handler(arguments)
        if isinstance(content, CallToolResult):
            return content
        return CallToolResult(content=content, isError=False)
    except SpectrumAnalyzerError as e:
        logger.error("Spectrum analyzer error in tool %s: %s", name, e)
        return _format_error(e)
    except (ValueError, TypeError, KeyError) as e:
        logger.error("Invalid argument in tool %s: %s", name, e)
        return _format_error(e)
    except OSError as e:
        logger.error("I/O error in tool %s: %s", name, e)
        return _format_error(e)
    except Exception as e:
        logger.exception("Unexpected error in tool %s", name)
        return _format_error(e)
