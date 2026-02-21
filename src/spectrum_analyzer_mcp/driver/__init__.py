"""Spectrum analyzer driver components."""

from .exceptions import (
    CommunicationError,
    ConfigurationError,
    ConnectionError,
    MeasurementError,
    SafetyError,
    SpectrumAnalyzerError,
    TimeoutError,
)
from .sa_driver import RSSpectrumAnalyzerDriver
from .scpi_dialect import SCPIDialect, detect_dialect
from .scpi_socket import SCPISocket  # backward compat alias

__all__ = [
    "CommunicationError",
    "ConfigurationError",
    "ConnectionError",
    "MeasurementError",
    "RSSpectrumAnalyzerDriver",
    "SafetyError",
    "SCPIDialect",
    "SCPISocket",
    "SpectrumAnalyzerError",
    "TimeoutError",
    "detect_dialect",
]
