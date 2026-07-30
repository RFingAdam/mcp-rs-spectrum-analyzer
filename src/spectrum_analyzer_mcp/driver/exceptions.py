"""Custom exceptions for spectrum analyzer driver.

This module re-exports exceptions from the package root for backwards compatibility.
Import from spectrum_analyzer_mcp.exceptions for new code.
"""

from ..exceptions import (
    CommunicationError,
    ConfigurationError,
    ConnectionError,
    DesyncError,
    MeasurementError,
    SafetyError,
    SpectrumAnalyzerError,
    TimeoutError,
)

__all__ = [
    "CommunicationError",
    "ConfigurationError",
    "ConnectionError",
    "DesyncError",
    "MeasurementError",
    "SafetyError",
    "SpectrumAnalyzerError",
    "TimeoutError",
]
