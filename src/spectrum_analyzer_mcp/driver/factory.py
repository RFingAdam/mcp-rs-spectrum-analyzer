"""Driver factory for auto-detecting instrument vendor and creating drivers."""

import logging

from ..transport import SCPITransport
from .sa_driver import RSSpectrumAnalyzerDriver
from .scpi_dialect import detect_dialect

logger = logging.getLogger(__name__)


async def create_driver_from_transport(
    transport: SCPITransport,
    **kwargs,
) -> RSSpectrumAnalyzerDriver:
    """Create a driver by connecting via transport and auto-detecting the vendor.

    Connects, queries *IDN?, detects the SCPI dialect, and returns a
    configured driver instance.

    Args:
        transport: A pre-configured (but not yet connected) transport.
        **kwargs: Additional arguments passed to RSSpectrumAnalyzerDriver
            (e.g. safety_limits, family).

    Returns:
        Connected RSSpectrumAnalyzerDriver instance.
    """
    await transport.connect()

    # Query identification
    idn = await transport.query("*IDN?")
    parts = idn.strip().split(",")
    manufacturer = parts[0].strip() if parts else "Unknown"

    # Detect dialect
    dialect = detect_dialect(manufacturer)
    logger.info(
        "Detected %s instrument (dialect: %s)",
        manufacturer,
        dialect.vendor_name,
    )

    # Create driver with the transport
    driver = RSSpectrumAnalyzerDriver(
        transport=transport,
        **kwargs,
    )
    # The driver's connect() will re-query *IDN? which is fine
    # But since transport is already connected, it'll just proceed
    driver._dialect = dialect  # Store dialect for future use

    return driver
