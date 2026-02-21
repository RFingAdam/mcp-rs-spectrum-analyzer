"""Custom exceptions for spectrum analyzer driver.

This module re-exports exceptions from the package root for backwards compatibility.
Import from rs_spectrum_analyzer_mcp.exceptions for new code.
"""

from ..exceptions import (
    CommunicationError,
    ConfigurationError,
    ConnectionError,
    MeasurementError,
    SafetyError,
    SpectrumAnalyzerError,
    TimeoutError,
)

__all__ = [
    "CommunicationError",
    "ConfigurationError",
    "ConnectionError",
    "MeasurementError",
    "SafetyError",
    "SpectrumAnalyzerError",
    "TimeoutError",
]
