"""Custom exceptions for spectrum analyzer operations.

This module defines all exceptions at the package root level to avoid
circular import issues between driver and safety modules.
"""


class SpectrumAnalyzerError(Exception):
    """Base exception for spectrum analyzer errors."""

    def __init__(self, message: str, address: str | None = None):
        self.message = message
        self.address = address
        super().__init__(f"{message}" + (f" (address: {address})" if address else ""))


class ConnectionError(SpectrumAnalyzerError):
    """Error connecting to spectrum analyzer."""

    pass


class CommunicationError(SpectrumAnalyzerError):
    """Error communicating with spectrum analyzer."""

    pass


class ConfigurationError(SpectrumAnalyzerError):
    """Error configuring spectrum analyzer settings."""

    pass


class MeasurementError(SpectrumAnalyzerError):
    """Error during measurement."""

    pass


class SafetyError(SpectrumAnalyzerError):
    """Safety limit violation."""

    def __init__(
        self,
        message: str,
        parameter: str,
        value: float,
        limit: float,
        address: str | None = None,
    ):
        self.parameter = parameter
        self.value = value
        self.limit = limit
        super().__init__(message, address)


class TimeoutError(SpectrumAnalyzerError):
    """Operation timed out."""

    pass
