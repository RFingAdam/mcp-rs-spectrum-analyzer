"""MCP tool definitions and handlers for spectrum analyzer operations."""

import asyncio
import csv
import io
import json
import logging
from pathlib import Path
from typing import Any

from mcp.types import CallToolResult, TextContent, Tool

from .config import get_settings
from .driver import RSSpectrumAnalyzerDriver
from .exceptions import SpectrumAnalyzerError
from .limits import LimitLine, LimitManager, LimitSegment
from .models.sa_types import DetectorType, TraceMode
from .safety.validators import sanitize_scpi_param, validate_safe_path
from .state import InstrumentState, StateManager
from .templates import (
    ACLRTemplate,
    ChannelPowerTemplate,
    EMIPrecomplianceTemplate,
    HarmonicTemplate,
    MeasurementTemplate,
    OccupiedBandwidthTemplate,
    SpuriousEmissionTemplate,
)

logger = logging.getLogger(__name__)

# Global connection manager
_sa_connections: dict[str, RSSpectrumAnalyzerDriver] = {}

# Global template storage
_current_template: MeasurementTemplate | None = None

# Global limit manager
_limit_manager = LimitManager()

# Global state manager
_state_manager = StateManager()

# Issue 4: asyncio.Lock instances for shared mutable state
_connection_lock = asyncio.Lock()
_template_lock = asyncio.Lock()
_measurement_lock = asyncio.Lock()


def _get_connection_key(host: str, port: int) -> str:
    """Generate unique key for connection."""
    return f"{host}:{port}"


async def _get_sa(host: str | None = None, port: int | None = None) -> RSSpectrumAnalyzerDriver:
    """Get or create spectrum analyzer connection."""
    settings = get_settings()
    host = host if host is not None else settings.default_host
    port = port if port is not None else settings.default_port
    key = _get_connection_key(host, port)

    async with _connection_lock:
        if key in _sa_connections:
            sa = _sa_connections[key]
            if sa.is_connected:
                return sa

        # Create new connection
        sa = RSSpectrumAnalyzerDriver(
            host=host,
            port=port,
            timeout=settings.connection_timeout,
            command_timeout=settings.command_timeout,
            safety_limits=settings.get_safety_limits(),
        )
        await sa.connect()
        _sa_connections[key] = sa
        return sa


async def _close_sa(host: str, port: int) -> bool:
    """Close spectrum analyzer connection."""
    key = _get_connection_key(host, port)
    async with _connection_lock:
        if key in _sa_connections:
            sa = _sa_connections.pop(key)
            await sa.disconnect()
            return True
        return False


def _format_result(result: Any) -> list[TextContent]:
    """Format result as MCP TextContent."""
    if isinstance(result, dict):
        text = json.dumps(result, indent=2, default=str)
    elif isinstance(result, list):
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


# =============================================================================
# Tool Definitions
# =============================================================================

def get_tools() -> list[Tool]:
    """Get all MCP tool definitions."""
    return [
        # =====================================================================
        # Connection Tools
        # =====================================================================
        Tool(
            name="sa_discover",
            description="Scan for R&S spectrum analyzers on port 5025",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "Host to scan (default: from settings)",
                    },
                    "start_port": {
                        "type": "integer",
                        "description": "Start port (default: 5025)",
                        "default": 5025,
                    },
                    "end_port": {
                        "type": "integer",
                        "description": "End port (default: 5035)",
                        "default": 5035,
                    },
                },
            },
        ),
        Tool(
            name="sa_connect",
            description="Connect to R&S spectrum analyzer at specified host:port",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": "Instrument hostname or IP",
                    },
                    "port": {
                        "type": "integer",
                        "description": "TCP port (default: 5025)",
                    },
                },
            },
        ),
        Tool(
            name="sa_disconnect",
            description="Disconnect from spectrum analyzer",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_identify",
            description=(
                "Get spectrum analyzer identification (*IDN?): "
                "manufacturer, model, serial, firmware"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_get_status",
            description="Get spectrum analyzer connection and configuration status",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        # =====================================================================
        # Frequency Tools
        # =====================================================================
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
        # =====================================================================
        # Amplitude Tools
        # =====================================================================
        Tool(
            name="sa_set_reference_level",
            description="Set reference level (top of display) in dBm",
            inputSchema={
                "type": "object",
                "properties": {
                    "level_dbm": {
                        "type": "number",
                        "description": "Reference level in dBm",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["level_dbm"],
            },
        ),
        Tool(
            name="sa_set_attenuation",
            description="Set RF input attenuation in dB",
            inputSchema={
                "type": "object",
                "properties": {
                    "attenuation_db": {
                        "type": "number",
                        "description": "Attenuation in dB (0-75)",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["attenuation_db"],
            },
        ),
        Tool(
            name="sa_set_preamp",
            description="Enable or disable the internal preamplifier",
            inputSchema={
                "type": "object",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "description": "True to enable, False to disable",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["enabled"],
            },
        ),
        Tool(
            name="sa_set_scale",
            description="Set Y-axis scale in dB/division",
            inputSchema={
                "type": "object",
                "properties": {
                    "db_per_div": {
                        "type": "number",
                        "description": "dB per division (e.g. 10)",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["db_per_div"],
            },
        ),
        # =====================================================================
        # Bandwidth Tools
        # =====================================================================
        Tool(
            name="sa_set_rbw",
            description="Set resolution bandwidth (RBW)",
            inputSchema={
                "type": "object",
                "properties": {
                    "rbw_hz": {
                        "type": "number",
                        "description": "Resolution bandwidth in Hz",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["rbw_hz"],
            },
        ),
        Tool(
            name="sa_set_vbw",
            description="Set video bandwidth (VBW)",
            inputSchema={
                "type": "object",
                "properties": {
                    "vbw_hz": {
                        "type": "number",
                        "description": "Video bandwidth in Hz",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["vbw_hz"],
            },
        ),
        Tool(
            name="sa_set_sweep_time",
            description="Set sweep time in seconds",
            inputSchema={
                "type": "object",
                "properties": {
                    "time_s": {
                        "type": "number",
                        "description": "Sweep time in seconds",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["time_s"],
            },
        ),
        Tool(
            name="sa_auto_coupling",
            description="Enable auto-coupling for RBW, VBW, and sweep time",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        # =====================================================================
        # Trace Tools
        # =====================================================================
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
        # =====================================================================
        # Marker Tools
        # =====================================================================
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
        # =====================================================================
        # Measurement Tools
        # =====================================================================
        Tool(
            name="sa_measure_channel_power",
            description="Measure channel power at specified frequency and bandwidth",
            inputSchema={
                "type": "object",
                "properties": {
                    "center_hz": {
                        "type": "number",
                        "description": "Center frequency in Hz",
                    },
                    "bandwidth_hz": {
                        "type": "number",
                        "description": "Channel bandwidth in Hz",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["center_hz", "bandwidth_hz"],
            },
        ),
        Tool(
            name="sa_measure_aclr",
            description="Measure adjacent channel leakage ratio (ACLR)",
            inputSchema={
                "type": "object",
                "properties": {
                    "center_hz": {
                        "type": "number",
                        "description": "Center frequency in Hz",
                    },
                    "channel_bw_hz": {
                        "type": "number",
                        "description": "Channel bandwidth in Hz",
                    },
                    "adjacent_bw_hz": {
                        "type": "number",
                        "description": "Adjacent channel bandwidth (default: same as channel)",
                    },
                    "adjacent_offset_hz": {
                        "type": "number",
                        "description": "Adjacent channel offset (default: same as channel BW)",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["center_hz", "channel_bw_hz"],
            },
        ),
        Tool(
            name="sa_measure_obw",
            description="Measure occupied bandwidth (99% power bandwidth)",
            inputSchema={
                "type": "object",
                "properties": {
                    "power_percentage": {
                        "type": "number",
                        "description": "Power percentage (default: 99.0)",
                        "default": 99.0,
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_measure_sem",
            description="Measure spectrum emission mask (SEM) with pass/fail",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_measure_evm",
            description="Measure error vector magnitude (requires digital demod option)",
            inputSchema={
                "type": "object",
                "properties": {
                    "modulation": {
                        "type": "string",
                        "description": "Modulation type (e.g. QPSK, 16QAM, 64QAM)",
                        "default": "QPSK",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_measure_ccdf",
            description=(
                "Measure complementary cumulative distribution "
                "function (CCDF/crest factor)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "num_samples": {
                        "type": "integer",
                        "description": "Number of samples (default: 1000000)",
                        "default": 1000000,
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        # =====================================================================
        # Trigger/Sweep Tools
        # =====================================================================
        Tool(
            name="sa_single_sweep",
            description="Trigger a single sweep and wait for completion",
            inputSchema={
                "type": "object",
                "properties": {
                    "timeout": {
                        "type": "number",
                        "description": "Timeout in seconds",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_continuous_sweep",
            description="Enable or disable continuous sweep mode",
            inputSchema={
                "type": "object",
                "properties": {
                    "enabled": {
                        "type": "boolean",
                        "description": "True for continuous, False for single",
                        "default": True,
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_set_trigger",
            description=(
                "Configure trigger source: IMM (free run), "
                "EXT (external), VID (video), IFP (IF power)"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Trigger source",
                        "enum": ["IMM", "EXT", "VID", "IFP", "RFP"],
                    },
                    "level": {
                        "type": "number",
                        "description": "Trigger level (for video/IF power triggers)",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["source"],
            },
        ),
        # =====================================================================
        # Export Tools
        # =====================================================================
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
        # =====================================================================
        # Raw SCPI Tools
        # =====================================================================
        Tool(
            name="sa_scpi_send",
            description="Send raw SCPI command to spectrum analyzer (no response)",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "SCPI command string",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="sa_scpi_query",
            description="Send raw SCPI query and return response",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "SCPI query string (must end with ?)",
                    },
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
                "required": ["command"],
            },
        ),
        Tool(
            name="sa_reset",
            description="Reset spectrum analyzer to factory defaults (*RST)",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        Tool(
            name="sa_preset",
            description="Preset spectrum analyzer (SYST:PRES)",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {"type": "string"},
                    "port": {"type": "integer"},
                },
            },
        ),
        # =====================================================================
        # Template Tools
        # =====================================================================
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
                        "description": (
                            "Built-in template name "
                            "(e.g. 'lte_10mhz_channel_power')"
                        ),
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
        # =====================================================================
        # Limit Tools
        # =====================================================================
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
                            "Limit segments: [{start_freq_hz, "
                            "stop_freq_hz, max_db, min_db, name}]"
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
        # =====================================================================
        # State Tools
        # =====================================================================
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


# =============================================================================
# Tool Handlers
# =============================================================================

async def handle_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Route tool call to appropriate handler.

    Returns a CallToolResult. On success, isError=False; on failure, isError=True.
    The MCP SDK recognises CallToolResult and passes it through directly.
    """
    try:
        handler = _TOOL_HANDLERS.get(name)
        if handler is None:
            return _format_error(ValueError(f"Unknown tool: {name}"))
        content = await handler(arguments)
        # Handler returned successfully - wrap content in a CallToolResult
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


# =============================================================================
# Handler Implementations
# =============================================================================

async def _handle_discover(args: dict[str, Any]) -> list[TextContent]:
    settings = get_settings()
    host = args.get("host", settings.default_host)
    start_port = args.get("start_port", 5025)
    end_port = args.get("end_port", 5035)

    found = []
    for port in range(start_port, end_port + 1):
        try:
            sa = RSSpectrumAnalyzerDriver(host=host, port=port, timeout=2.0)
            info = await sa.connect()
            found.append({
                "host": host,
                "port": port,
                "instrument": info.to_dict(),
            })
            await sa.disconnect()
        except (OSError, SpectrumAnalyzerError) as e:
            logger.debug("No instrument at %s:%d: %s", host, port, e)

    if found:
        return _format_result({"found": found, "count": len(found)})
    return _format_result({"found": [], "count": 0, "message": "No instruments found"})


async def _handle_connect(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    return _format_result({
        "connected": True,
        "instrument": sa.info.to_dict() if sa.info else {},
        "family": sa.family.value if sa.family else "Unknown",
    })


async def _handle_disconnect(args: dict[str, Any]) -> list[TextContent]:
    settings = get_settings()
    host = args.get("host", settings.default_host)
    port = args.get("port", settings.default_port)
    closed = await _close_sa(host, port)
    return _format_result({"disconnected": closed})


async def _handle_identify(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    return _format_result(sa.info.to_dict() if sa.info else {"error": "No info available"})


async def _handle_get_status(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    status = await sa.get_status()
    return _format_result(status)


async def _handle_set_center_span(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_center_span(args["center_hz"], args["span_hz"])
    return _format_result({
        "center_frequency_hz": args["center_hz"],
        "span_hz": args["span_hz"],
    })


async def _handle_set_start_stop(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_start_stop(args["start_hz"], args["stop_hz"])
    return _format_result({
        "start_frequency_hz": args["start_hz"],
        "stop_frequency_hz": args["stop_hz"],
    })


async def _handle_set_frequency_step(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_frequency_step(args["step_hz"])
    return _format_result({"frequency_step_hz": args["step_hz"]})


async def _handle_full_span(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.full_span()
    return _format_result({"full_span": True})


async def _handle_set_reference_level(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_reference_level(args["level_dbm"])
    return _format_result({"reference_level_dbm": args["level_dbm"]})


async def _handle_set_attenuation(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_attenuation(args["attenuation_db"])
    return _format_result({"attenuation_db": args["attenuation_db"]})


async def _handle_set_preamp(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_preamp(args["enabled"])
    return _format_result({"preamp_enabled": args["enabled"]})


async def _handle_set_scale(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_scale(args["db_per_div"])
    return _format_result({"scale_db_per_div": args["db_per_div"]})


async def _handle_set_rbw(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_rbw(args["rbw_hz"])
    return _format_result({"rbw_hz": args["rbw_hz"]})


async def _handle_set_vbw(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_vbw(args["vbw_hz"])
    return _format_result({"vbw_hz": args["vbw_hz"]})


async def _handle_set_sweep_time(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_sweep_time(args["time_s"])
    return _format_result({"sweep_time_s": args["time_s"]})


async def _handle_auto_coupling(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.auto_coupling()
    return _format_result({"auto_coupling": True})


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


async def _handle_set_marker(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_marker(args["frequency_hz"], args.get("marker_number", 1))
    marker = await sa.get_marker(args.get("marker_number", 1))
    return _format_result(marker.to_dict())


async def _handle_get_marker(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    marker = await sa.get_marker(args.get("marker_number", 1))
    return _format_result(marker.to_dict())


async def _handle_peak_search(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    marker = await sa.peak_search(args.get("marker_number", 1))
    return _format_result(marker.to_dict())


async def _handle_next_peak(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    marker = await sa.next_peak(
        args.get("marker_number", 1),
        args.get("direction", "next"),
    )
    return _format_result(marker.to_dict())


async def _handle_marker_to_center(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.marker_to_center(args.get("marker_number", 1))
    return _format_result({"marker_to_center": True})


async def _handle_marker_delta(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_delta_marker(
        args.get("marker_number", 1),
        args.get("enabled", True),
    )
    return _format_result({"delta_marker_enabled": args.get("enabled", True)})


async def _handle_marker_bandwidth(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    result = await sa.marker_bandwidth(
        args.get("n_db", 3.0),
        args.get("marker_number", 1),
    )
    return _format_result(result)


async def _handle_measure_channel_power(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    result = await sa.measure_channel_power(args["center_hz"], args["bandwidth_hz"])
    return _format_result(result.to_dict())


async def _handle_measure_aclr(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    result = await sa.measure_aclr(
        args["center_hz"],
        args["channel_bw_hz"],
        args.get("adjacent_bw_hz"),
        args.get("adjacent_offset_hz"),
    )
    return _format_result(result.to_dict())


async def _handle_measure_obw(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    result = await sa.measure_obw(args.get("power_percentage", 99.0))
    return _format_result(result.to_dict())


async def _handle_measure_sem(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    result = await sa.measure_sem()
    return _format_result(result.to_dict())


async def _handle_measure_evm(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    modulation = sanitize_scpi_param(args.get("modulation", "QPSK"))
    # EVM requires digital demod option; send relevant SCPI
    await sa.scpi_send(f"SENS:DDEM:FORM {modulation}")
    await sa.single_sweep()
    try:
        evm_resp = await sa.scpi_query("CALC:MARK:FUNC:DDEM:EVM?")
        return _format_result({
            "modulation": modulation,
            "evm_percent": float(evm_resp.strip()),
        })
    except (SpectrumAnalyzerError, ValueError) as e:
        logger.warning("EVM measurement failed (may require digital demod option): %s", e)
        return _format_result({
            "modulation": modulation,
            "error": f"EVM measurement requires digital demod option: {e}",
        })


async def _handle_measure_ccdf(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    num_samples = args.get("num_samples", 1000000)
    # CCDF measurement via statistics function
    await sa.scpi_send("CALC:STAT:CCDF ON")
    await sa.scpi_send(f"CALC:STAT:NSAM {num_samples}")
    await sa.single_sweep()
    try:
        ccdf_resp = await sa.scpi_query("CALC:STAT:RES?")
        parts = ccdf_resp.split(",")
        result: dict[str, Any] = {"num_samples": num_samples}
        if len(parts) >= 1:
            result["crest_factor_db"] = float(parts[0])
        if len(parts) >= 2:
            result["mean_power_dbm"] = float(parts[1])
        if len(parts) >= 3:
            result["peak_power_dbm"] = float(parts[2])
        return _format_result(result)
    except (SpectrumAnalyzerError, ValueError) as e:
        logger.warning("CCDF measurement failed: %s", e)
        return _format_result({
            "error": f"CCDF measurement failed: {e}",
        })


async def _handle_single_sweep(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.single_sweep(args.get("timeout"))
    return _format_result({"sweep_complete": True})


async def _handle_continuous_sweep(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.continuous_sweep(args.get("enabled", True))
    return _format_result({"continuous_sweep": args.get("enabled", True)})


async def _handle_set_trigger(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.set_trigger(args["source"], args.get("level"))
    return _format_result({"trigger_source": args["source"]})


async def _handle_save_trace_csv(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    trace = await sa.get_trace_data(args.get("trace_number", 1))

    # Issue 2: Validate path stays within cwd using proper path validation
    filepath = validate_safe_path(args["filepath"], Path.cwd())

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Frequency_Hz", "Amplitude_dBm"])
    for freq, amp in zip(trace.frequencies, trace.amplitudes):
        writer.writerow([freq, amp])

    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="") as f:
        f.write(output.getvalue())

    return _format_result({
        "filepath": str(filepath),
        "num_points": trace.num_points,
        "saved": True,
    })


async def _handle_save_screenshot(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    filepath = args["filepath"]
    # Sanitize to prevent SCPI command injection via metacharacters
    safe_filepath = sanitize_scpi_param(filepath)
    # Also escape single quotes for the SCPI string literal
    safe_filepath = safe_filepath.replace("'", "\\'")
    # R&S instruments can save screenshots via SCPI
    await sa.scpi_send("HCOP:DEV:LANG PNG")
    await sa.scpi_send(f"MMEM:NAME '{safe_filepath}'")
    await sa.scpi_send("HCOP:IMM")
    return _format_result({
        "filepath": filepath,
        "screenshot_saved": True,
    })


async def _handle_export_trace_data(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    trace = await sa.get_trace_data(args.get("trace_number", 1))
    return _format_result(trace.to_dict())


async def _handle_scpi_send(args: dict[str, Any]) -> list[TextContent] | CallToolResult:
    settings = get_settings()
    command = args["command"]

    # Issue 3: Check if raw SCPI is allowed
    if not settings.allow_raw_scpi:
        logger.warning(
            "Raw SCPI send blocked (allow_raw_scpi=False): %s", command
        )
        return _format_error(
            ValueError(
                "Raw SCPI commands are disabled. "
                "Set SA_ALLOW_RAW_SCPI=true to enable."
            )
        )

    # Issue 3: Log WARNING on every raw SCPI execution
    logger.warning("Raw SCPI send: %s", command)

    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.scpi_send(command)
    return _format_result({"command": command, "sent": True})


async def _handle_scpi_query(args: dict[str, Any]) -> list[TextContent] | CallToolResult:
    settings = get_settings()
    command = args["command"]

    # Issue 3: Check if raw SCPI is allowed
    if not settings.allow_raw_scpi:
        logger.warning(
            "Raw SCPI query blocked (allow_raw_scpi=False): %s", command
        )
        return _format_error(
            ValueError(
                "Raw SCPI commands are disabled. "
                "Set SA_ALLOW_RAW_SCPI=true to enable."
            )
        )

    # Issue 3: Log WARNING on every raw SCPI execution
    logger.warning("Raw SCPI query: %s", command)

    sa = await _get_sa(args.get("host"), args.get("port"))
    response = await sa.scpi_query(command)
    return _format_result({"command": command, "response": response})


async def _handle_reset(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.reset()
    return _format_result({"reset": True})


async def _handle_preset(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    await sa.preset()
    return _format_result({"preset": True})


async def _handle_list_templates(args: dict[str, Any]) -> list[TextContent]:
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
    global _current_template

    filepath = args.get("filepath")
    template_name = args.get("template_name")

    async with _template_lock:
        if filepath:
            # Issue 2: Validate template filepath stays within cwd
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
    global _current_template
    async with _template_lock:
        if _current_template is None:
            return _format_error(ValueError("No template loaded. Use sa_load_template first."))

        sa = await _get_sa(args.get("host"), args.get("port"))
        await _current_template.apply(sa)
        return _format_result({
            "template_applied": _current_template.name,
            "config": _current_template.config.to_dict(),
        })


async def _handle_define_limit(args: dict[str, Any]) -> list[TextContent]:
    segments = []
    for seg_data in args["segments"]:
        segments.append(LimitSegment(
            start_freq_hz=seg_data["start_freq_hz"],
            stop_freq_hz=seg_data["stop_freq_hz"],
            max_db=seg_data.get("max_db"),
            min_db=seg_data.get("min_db"),
            name=seg_data.get("name"),
        ))

    limit = LimitLine(
        name=args["name"],
        segments=segments,
        description=args.get("description", ""),
    )
    async with _measurement_lock:
        _limit_manager.add_limit(limit)

    return _format_result({
        "limit_defined": args["name"],
        "num_segments": len(segments),
    })


async def _handle_check_limits(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    trace = await sa.get_trace_data(args.get("trace_number", 1))
    async with _measurement_lock:
        result = _limit_manager.get_overall_status(trace)
    return _format_result(result)


async def _handle_clear_limits(args: dict[str, Any]) -> list[TextContent]:
    async with _measurement_lock:
        _limit_manager.clear_limits()
    return _format_result({"limits_cleared": True})


async def _handle_list_limits(args: dict[str, Any]) -> list[TextContent]:
    async with _measurement_lock:
        names = _limit_manager.list_limits()
        limits_info = []
        for name in names:
            limit = _limit_manager.get_limit(name)
            if limit:
                limits_info.append({
                    "name": name,
                    "description": limit.description,
                    "num_segments": len(limit.segments),
                    "segments": [s.to_dict() for s in limit.segments],
                })
    return _format_result({"limits": limits_info, "count": len(limits_info)})


async def _handle_save_state(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    state = await _state_manager.capture_state(sa)

    if args.get("notes"):
        state.notes = args["notes"]

    # Issue 2: Validate path stays within state directory
    state_dir = _state_manager.state_directory
    filepath = validate_safe_path(f"{args['name']}.json", state_dir)
    state.save(filepath)

    return _format_result({
        "state_saved": args["name"],
        "filepath": str(filepath),
        "summary": state.get_summary(),
    })


async def _handle_load_state(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))

    # Issue 2: Validate path stays within state directory
    state_dir = _state_manager.state_directory
    filepath = validate_safe_path(f"{args['name']}.json", state_dir)

    state = InstrumentState.load(filepath)
    await _state_manager.restore_state(sa, state)

    return _format_result({
        "state_loaded": args["name"],
        "summary": state.get_summary(),
    })


async def _handle_get_full_state(args: dict[str, Any]) -> list[TextContent]:
    sa = await _get_sa(args.get("host"), args.get("port"))
    state = await _state_manager.capture_state(sa)
    return _format_result(state.to_dict())


# =============================================================================
# Tool Handler Registry
# =============================================================================

_TOOL_HANDLERS = {
    # Connection
    "sa_discover": _handle_discover,
    "sa_connect": _handle_connect,
    "sa_disconnect": _handle_disconnect,
    "sa_identify": _handle_identify,
    "sa_get_status": _handle_get_status,
    # Frequency
    "sa_set_center_span": _handle_set_center_span,
    "sa_set_start_stop": _handle_set_start_stop,
    "sa_set_frequency_step": _handle_set_frequency_step,
    "sa_full_span": _handle_full_span,
    # Amplitude
    "sa_set_reference_level": _handle_set_reference_level,
    "sa_set_attenuation": _handle_set_attenuation,
    "sa_set_preamp": _handle_set_preamp,
    "sa_set_scale": _handle_set_scale,
    # Bandwidth
    "sa_set_rbw": _handle_set_rbw,
    "sa_set_vbw": _handle_set_vbw,
    "sa_set_sweep_time": _handle_set_sweep_time,
    "sa_auto_coupling": _handle_auto_coupling,
    # Trace
    "sa_get_trace_data": _handle_get_trace_data,
    "sa_set_trace_mode": _handle_set_trace_mode,
    "sa_set_averaging_count": _handle_set_averaging_count,
    "sa_clear_trace": _handle_clear_trace,
    "sa_set_detector": _handle_set_detector,
    # Markers
    "sa_set_marker": _handle_set_marker,
    "sa_get_marker": _handle_get_marker,
    "sa_peak_search": _handle_peak_search,
    "sa_next_peak": _handle_next_peak,
    "sa_marker_to_center": _handle_marker_to_center,
    "sa_marker_delta": _handle_marker_delta,
    "sa_marker_bandwidth": _handle_marker_bandwidth,
    # Measurements
    "sa_measure_channel_power": _handle_measure_channel_power,
    "sa_measure_aclr": _handle_measure_aclr,
    "sa_measure_obw": _handle_measure_obw,
    "sa_measure_sem": _handle_measure_sem,
    "sa_measure_evm": _handle_measure_evm,
    "sa_measure_ccdf": _handle_measure_ccdf,
    # Trigger/Sweep
    "sa_single_sweep": _handle_single_sweep,
    "sa_continuous_sweep": _handle_continuous_sweep,
    "sa_set_trigger": _handle_set_trigger,
    # Export
    "sa_save_trace_csv": _handle_save_trace_csv,
    "sa_save_screenshot": _handle_save_screenshot,
    "sa_export_trace_data": _handle_export_trace_data,
    # Raw SCPI
    "sa_scpi_send": _handle_scpi_send,
    "sa_scpi_query": _handle_scpi_query,
    "sa_reset": _handle_reset,
    "sa_preset": _handle_preset,
    # Templates
    "sa_list_templates": _handle_list_templates,
    "sa_load_template": _handle_load_template,
    "sa_apply_template": _handle_apply_template,
    # Limits
    "sa_define_limit": _handle_define_limit,
    "sa_check_limits": _handle_check_limits,
    "sa_clear_limits": _handle_clear_limits,
    "sa_list_limits": _handle_list_limits,
    # State
    "sa_save_state": _handle_save_state,
    "sa_load_state": _handle_load_state,
    "sa_get_full_state": _handle_get_full_state,
}
