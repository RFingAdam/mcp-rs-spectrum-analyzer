"""Measurement template tools."""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any

from mcp.types import CallToolResult, TextContent, Tool

from ..safety.validators import validate_safe_path
from ..templates import (
    ACLRTemplate,
    ChannelPowerTemplate,
    EMIPrecomplianceTemplate,
    HarmonicTemplate,
    MeasurementTemplate,
    OccupiedBandwidthTemplate,
    SpuriousEmissionTemplate,
)
from ._connection import _get_sa
from ._registry import _format_error, _format_result

logger = logging.getLogger(__name__)

# Global template storage
_current_template: MeasurementTemplate | None = None

# asyncio.Lock for template state
_template_lock = asyncio.Lock()


def get_template_tools() -> list[Tool]:
    """Get template tool definitions."""
    return [
        Tool(
            name="sa_list_templates",
            description="List all available measurement templates",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="sa_load_template",
            description="Load a measurement template by name or from file",
            inputSchema={
                "type": "object",
                "properties": {
                    "template_name": {
                        "type": "string",
                        "description": ("Built-in template name (e.g. 'lte_10mhz_channel_power')"),
                    },
                    "filepath": {
                        "type": "string",
                        "description": "Path to template JSON file (alternative to template_name)",
                    },
                },
            },
        ),
        Tool(
            name="sa_apply_template",
            description="Apply the currently loaded template to the instrument",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
    ]


async def _handle_list_templates(args: dict[str, Any]) -> list[TextContent]:
    """List all available built-in measurement templates.

    Args:
        args: (none required).

    Returns:
        Dict of template categories with template names and descriptions.
    """
    templates = {
        "channel_power": {
            "lte_10mhz_channel_power": "LTE 10 MHz channel power measurement",
            "nr_100mhz_channel_power": "5G NR 100 MHz channel power",
            "wlan_80mhz_channel_power": "WLAN 80 MHz channel power",
        },
        "aclr": {
            "lte_10mhz_aclr": "LTE 10 MHz E-UTRA ACLR",
            "nr_100mhz_aclr": "5G NR 100 MHz ACLR",
            "wlan_80mhz_aclr": "WLAN 80 MHz ACLR",
        },
        "emi": {
            "cispr_32_class_b": "CISPR 32 Class B conducted emissions",
            "cispr_32_class_b_radiated": "CISPR 32 Class B radiated (30 MHz - 1 GHz)",
        },
        "spurious": {
            "wideband_spurious": "Wideband spurious emission scan",
            "harmonic_spurious": "Harmonic spurious scan",
        },
        "obw": {
            "lte_10mhz_obw": "LTE 10 MHz occupied bandwidth",
        },
        "harmonics": {
            "harmonic_measurement": "Fundamental + N harmonics measurement",
        },
    }
    return _format_result(templates)


async def _handle_load_template(args: dict[str, Any]) -> list[TextContent] | CallToolResult:
    """Load a measurement template by name or from a JSON file.

    Args:
        args: template_name (built-in name) or filepath (JSON file path).

    Returns:
        Template summary (name, description, configuration).
    """
    global _current_template

    filepath = args.get("filepath")
    template_name = args.get("template_name")

    async with _template_lock:
        if filepath:
            safe_path = validate_safe_path(filepath, Path.cwd())
            _current_template = MeasurementTemplate.load(safe_path)
        elif template_name:
            template_map = {
                "lte_10mhz_channel_power": lambda: ChannelPowerTemplate.lte_10mhz(),
                "nr_100mhz_channel_power": lambda: ChannelPowerTemplate.nr_100mhz(),
                "wlan_80mhz_channel_power": lambda: ChannelPowerTemplate.wlan_80mhz(),
                "lte_10mhz_aclr": lambda: ACLRTemplate.lte_10mhz(),
                "nr_100mhz_aclr": lambda: ACLRTemplate.nr_100mhz(),
                "wlan_80mhz_aclr": lambda: ACLRTemplate.wlan_80mhz(),
                "cispr_32_class_b": lambda: EMIPrecomplianceTemplate.cispr_32_class_b(),
                "cispr_32_class_b_radiated": (
                    lambda: EMIPrecomplianceTemplate.cispr_32_class_b_radiated()
                ),
                "wideband_spurious": lambda: SpuriousEmissionTemplate.wideband_spurious(),
                "harmonic_spurious": lambda: SpuriousEmissionTemplate.harmonic_spurious(),
                "lte_10mhz_obw": lambda: OccupiedBandwidthTemplate.lte_10mhz(),
                "harmonic_measurement": lambda: HarmonicTemplate.create(1e9),
            }

            factory = template_map.get(template_name)
            if factory is None:
                return _format_error(ValueError(f"Unknown template: {template_name}"))
            _current_template = factory()
        else:
            return _format_error(ValueError("Specify either template_name or filepath"))

        return _format_result(_current_template.get_summary())


async def _handle_apply_template(args: dict[str, Any]) -> list[TextContent] | CallToolResult:
    """Apply the currently loaded template to the instrument.

    Args:
        args: host, port.

    Returns:
        Applied template name and configuration.

    SCPI: Varies by template (frequency, bandwidth, detector settings).
    """
    global _current_template
    async with _template_lock:
        if _current_template is None:
            return _format_error(ValueError("No template loaded. Use sa_load_template first."))

        sa = await _get_sa(args.get("host"), args.get("port"))
        await _current_template.apply(sa)
        return _format_result(
            {
                "template_applied": _current_template.name,
                "config": _current_template.config.to_dict(),
            }
        )


HANDLERS: dict[str, Callable[..., Coroutine]] = {
    "sa_list_templates": _handle_list_templates,
    "sa_load_template": _handle_load_template,
    "sa_apply_template": _handle_apply_template,
}
