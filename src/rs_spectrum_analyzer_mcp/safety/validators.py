"""Safety validators for spectrum analyzer parameters."""

import logging
from dataclasses import dataclass

from ..exceptions import SafetyError

logger = logging.getLogger(__name__)


@dataclass
class SafetyLimits:
    """
    Safety limits for spectrum analyzer parameters.

    All limits are configurable via environment variables.
    """

    max_input_power_dbm: float = 30.0
    max_frequency_hz: float = 90e9  # 90 GHz (FSW max)
    min_frequency_hz: float = 2.0  # 2 Hz
    min_rbw_hz: float = 1.0  # 1 Hz
    max_rbw_hz: float = 10e6  # 10 MHz
    min_attenuation_db: float = 0.0
    max_attenuation_db: float = 75.0
    min_reference_level_dbm: float = -130.0
    max_reference_level_dbm: float = 30.0


class SafetyValidator:
    """
    Validates spectrum analyzer parameters against safety limits.

    Prevents accidental damage to equipment by enforcing
    configurable limits on frequency, attenuation, and other parameters.
    """

    def __init__(self, limits: SafetyLimits | None = None):
        """
        Initialize validator with limits.

        Args:
            limits: Safety limits (uses defaults if None)
        """
        self.limits = limits or SafetyLimits()

    def validate_frequency(self, frequency_hz: float) -> None:
        """
        Validate frequency.

        Args:
            frequency_hz: Frequency in Hz

        Raises:
            SafetyError: If frequency exceeds limits
        """
        if frequency_hz > self.limits.max_frequency_hz:
            raise SafetyError(
                f"Frequency {frequency_hz / 1e9:.3f} GHz exceeds maximum "
                f"{self.limits.max_frequency_hz / 1e9:.3f} GHz",
                parameter="frequency_hz",
                value=frequency_hz,
                limit=self.limits.max_frequency_hz,
            )

        if frequency_hz < self.limits.min_frequency_hz:
            raise SafetyError(
                f"Frequency {frequency_hz} Hz below minimum "
                f"{self.limits.min_frequency_hz} Hz",
                parameter="frequency_hz",
                value=frequency_hz,
                limit=self.limits.min_frequency_hz,
            )

        logger.debug(f"Frequency {frequency_hz / 1e6:.3f} MHz validated")

    def validate_frequency_range(
        self, start_freq_hz: float, stop_freq_hz: float
    ) -> None:
        """
        Validate frequency range.

        Args:
            start_freq_hz: Start frequency in Hz
            stop_freq_hz: Stop frequency in Hz

        Raises:
            SafetyError: If frequencies exceed limits
            ValueError: If start >= stop
        """
        self.validate_frequency(start_freq_hz)
        self.validate_frequency(stop_freq_hz)

        if start_freq_hz >= stop_freq_hz:
            raise ValueError(
                f"Start frequency ({start_freq_hz / 1e6:.3f} MHz) must be less than "
                f"stop frequency ({stop_freq_hz / 1e6:.3f} MHz)"
            )

    def validate_reference_level(self, reference_level_dbm: float) -> None:
        """
        Validate reference level.

        Args:
            reference_level_dbm: Reference level in dBm

        Raises:
            SafetyError: If reference level exceeds limits
        """
        if reference_level_dbm > self.limits.max_reference_level_dbm:
            raise SafetyError(
                f"Reference level {reference_level_dbm} dBm exceeds maximum "
                f"{self.limits.max_reference_level_dbm} dBm",
                parameter="reference_level_dbm",
                value=reference_level_dbm,
                limit=self.limits.max_reference_level_dbm,
            )

        if reference_level_dbm < self.limits.min_reference_level_dbm:
            raise SafetyError(
                f"Reference level {reference_level_dbm} dBm below minimum "
                f"{self.limits.min_reference_level_dbm} dBm",
                parameter="reference_level_dbm",
                value=reference_level_dbm,
                limit=self.limits.min_reference_level_dbm,
            )

        logger.debug(f"Reference level {reference_level_dbm} dBm validated")

    def validate_attenuation(self, attenuation_db: float) -> None:
        """
        Validate input attenuation.

        Args:
            attenuation_db: Attenuation in dB

        Raises:
            SafetyError: If attenuation exceeds limits
        """
        if attenuation_db > self.limits.max_attenuation_db:
            raise SafetyError(
                f"Attenuation {attenuation_db} dB exceeds maximum "
                f"{self.limits.max_attenuation_db} dB",
                parameter="attenuation_db",
                value=attenuation_db,
                limit=self.limits.max_attenuation_db,
            )

        if attenuation_db < self.limits.min_attenuation_db:
            raise SafetyError(
                f"Attenuation {attenuation_db} dB below minimum "
                f"{self.limits.min_attenuation_db} dB",
                parameter="attenuation_db",
                value=attenuation_db,
                limit=self.limits.min_attenuation_db,
            )

        logger.debug(f"Attenuation {attenuation_db} dB validated")

    def validate_rbw(self, rbw_hz: float) -> None:
        """
        Validate resolution bandwidth.

        Args:
            rbw_hz: Resolution bandwidth in Hz

        Raises:
            SafetyError: If RBW exceeds limits
        """
        if rbw_hz > self.limits.max_rbw_hz:
            raise SafetyError(
                f"RBW {rbw_hz / 1e3:.1f} kHz exceeds maximum "
                f"{self.limits.max_rbw_hz / 1e3:.1f} kHz",
                parameter="rbw_hz",
                value=rbw_hz,
                limit=self.limits.max_rbw_hz,
            )

        if rbw_hz < self.limits.min_rbw_hz:
            raise SafetyError(
                f"RBW {rbw_hz} Hz below minimum {self.limits.min_rbw_hz} Hz",
                parameter="rbw_hz",
                value=rbw_hz,
                limit=self.limits.min_rbw_hz,
            )

        logger.debug(f"RBW {rbw_hz / 1e3:.1f} kHz validated")

    def validate_input_power(self, power_dbm: float) -> None:
        """
        Validate expected input power (for attenuation recommendations).

        Args:
            power_dbm: Expected input power in dBm

        Raises:
            SafetyError: If power exceeds max input
        """
        if power_dbm > self.limits.max_input_power_dbm:
            raise SafetyError(
                f"Input power {power_dbm} dBm exceeds maximum "
                f"{self.limits.max_input_power_dbm} dBm. "
                f"Use external attenuation to protect the input!",
                parameter="input_power_dbm",
                value=power_dbm,
                limit=self.limits.max_input_power_dbm,
            )

        logger.debug(f"Input power {power_dbm} dBm validated")
