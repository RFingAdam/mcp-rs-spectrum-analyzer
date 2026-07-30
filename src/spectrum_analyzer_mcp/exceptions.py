"""Exceptions for spectrum analyzer operations.

Defined at the package root to avoid circular imports between the driver and
safety modules -- that reason still holds, so this module stays where it is even
though the class bodies now live in ``scpi_core.exceptions``.

``SpectrumAnalyzerError`` is an alias of ``scpi_core.InstrumentError``: nothing
in the hierarchy was analyzer-specific, and keeping a separate base class would
have meant a ``DesyncError`` raised by the shared transport was not catchable by
this server's own ``except SpectrumAnalyzerError``.

``MeasurementError`` stays a real class here. It is the one genuinely
analyzer-shaped failure in the set, and the core deliberately declined to model
measurements for instruments that do not have them.
"""

from scpi_core.exceptions import (
    CommunicationError,
    ConfigurationError,
    ConnectionError,
    DesyncError,
    InstrumentError,
    SafetyError,
    TimeoutError,
)

#: Historical name for this server's base exception.
SpectrumAnalyzerError = InstrumentError


class MeasurementError(InstrumentError):
    """Error during measurement."""


__all__ = [
    "CommunicationError",
    "ConfigurationError",
    "ConnectionError",
    "DesyncError",
    "InstrumentError",
    "MeasurementError",
    "SafetyError",
    "SpectrumAnalyzerError",
    "TimeoutError",
]
