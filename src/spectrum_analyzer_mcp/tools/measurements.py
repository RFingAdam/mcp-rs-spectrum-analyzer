"""Measurement tools (channel power, ACLR, OBW, SEM, EVM, CCDF)."""

import logging
from collections.abc import Callable, Coroutine
from typing import Any

from mcp.types import TextContent, Tool

from ..exceptions import SpectrumAnalyzerError
from ..safety.validators import sanitize_scpi_param
from ._connection import _get_sa
from ._registry import _format_result

logger = logging.getLogger(__name__)


def get_measurement_tools() -> list[Tool]:
    """Get measurement tool definitions."""
    return [
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
                "Measure complementary cumulative distribution function (CCDF/crest factor)"
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
    ]


async def _handle_measure_channel_power(args: dict[str, Any]) -> list[TextContent]:
    """Measure channel power at a given frequency and bandwidth.

    Args:
        args: center_hz, bandwidth_hz, host, port.

    Returns:
        Channel power (dBm), power density (dBm/Hz), bandwidth.

    SCPI: SENS:POW:ACH:BWID, CALC:MARK:FUNC:POW:SEL CPOW, CALC:MARK:FUNC:POW:RES?.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    result = await sa.measure_channel_power(args["center_hz"], args["bandwidth_hz"])
    return _format_result(result.to_dict())


async def _handle_measure_aclr(args: dict[str, Any]) -> list[TextContent]:
    """Measure adjacent channel leakage ratio (ACLR).

    Args:
        args: center_hz, channel_bw_hz, adjacent_bw_hz, adjacent_offset_hz, host, port.

    Returns:
        Channel power, lower/upper adjacent power, ACLR values in dB.

    SCPI: SENS:POW:ACH:BWID, CALC:MARK:FUNC:POW:SEL ACP, CALC:MARK:FUNC:POW:RES?.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    result = await sa.measure_aclr(
        args["center_hz"],
        args["channel_bw_hz"],
        args.get("adjacent_bw_hz"),
        args.get("adjacent_offset_hz"),
    )
    return _format_result(result.to_dict())


async def _handle_measure_obw(args: dict[str, Any]) -> list[TextContent]:
    """Measure occupied bandwidth (power percentage method).

    Args:
        args: power_percentage (default 99.0), host, port.

    Returns:
        Occupied bandwidth (Hz), center frequency, power percentage.

    SCPI: CALC:MARK:FUNC:POW:SEL OBW, CALC:MARK:FUNC:POW:RES?.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    result = await sa.measure_obw(args.get("power_percentage", 99.0))
    return _format_result(result.to_dict())


async def _handle_measure_sem(args: dict[str, Any]) -> list[TextContent]:
    """Measure spectrum emission mask (SEM) with pass/fail result.

    Args:
        args: host, port.

    Returns:
        Pass/fail status, TX power, and any limit violations.

    SCPI: CALC:LIM:FAIL?, CALC:MARK:FUNC:POW:RES?.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    result = await sa.measure_sem()
    return _format_result(result.to_dict())


async def _handle_measure_evm(args: dict[str, Any]) -> list[TextContent]:
    """Measure error vector magnitude (requires digital demod option).

    Args:
        args: modulation (e.g. QPSK, 16QAM), host, port.

    Returns:
        EVM percentage for the specified modulation type.

    SCPI: SENS:DDEM:FORM, CALC:MARK:FUNC:DDEM:EVM?.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    modulation = sanitize_scpi_param(args.get("modulation", "QPSK"))
    await sa.scpi_send(f"SENS:DDEM:FORM {modulation}")
    await sa.single_sweep()
    try:
        evm_resp = await sa.scpi_query("CALC:MARK:FUNC:DDEM:EVM?")
        return _format_result(
            {
                "modulation": modulation,
                "evm_percent": float(evm_resp.strip()),
            }
        )
    except (SpectrumAnalyzerError, ValueError) as e:
        logger.warning("EVM measurement failed (may require digital demod option): %s", e)
        return _format_result(
            {
                "modulation": modulation,
                "error": f"EVM measurement requires digital demod option: {e}",
            }
        )


async def _handle_measure_ccdf(args: dict[str, Any]) -> list[TextContent]:
    """Measure complementary cumulative distribution function (CCDF/crest factor).

    Args:
        args: num_samples (default 1000000), host, port.

    Returns:
        Crest factor (dB), mean power (dBm), peak power (dBm).

    SCPI: CALC:STAT:CCDF ON, CALC:STAT:NSAM, CALC:STAT:RES?.
    """
    sa = await _get_sa(args.get("host"), args.get("port"))
    num_samples = args.get("num_samples", 1000000)
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
        return _format_result(
            {
                "error": f"CCDF measurement failed: {e}",
            }
        )


HANDLERS: dict[str, Callable[..., Coroutine]] = {
    "sa_measure_channel_power": _handle_measure_channel_power,
    "sa_measure_aclr": _handle_measure_aclr,
    "sa_measure_obw": _handle_measure_obw,
    "sa_measure_sem": _handle_measure_sem,
    "sa_measure_evm": _handle_measure_evm,
    "sa_measure_ccdf": _handle_measure_ccdf,
}
