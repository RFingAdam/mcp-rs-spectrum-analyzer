"""Channel power measurement template."""

from dataclasses import dataclass
from typing import Any

from .base import MeasurementTemplate, SAConfig


@dataclass
class ChannelPowerTemplate(MeasurementTemplate):
    """
    Channel power measurement template.

    Configures the spectrum analyzer for channel power measurement
    with appropriate span, RBW, and detector settings.
    """

    channel_bandwidth_hz: float = 10e6
    channel_spacing_hz: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d = super().to_dict()
        d["channel_bandwidth_hz"] = self.channel_bandwidth_hz
        d["channel_spacing_hz"] = self.channel_spacing_hz
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChannelPowerTemplate":
        """Create from dictionary."""
        config = SAConfig.from_dict(data["config"])
        return cls(
            name=data["name"],
            description=data["description"],
            config=config,
            metadata=data.get("metadata", {}),
            channel_bandwidth_hz=data.get("channel_bandwidth_hz", 10e6),
            channel_spacing_hz=data.get("channel_spacing_hz"),
        )

    @classmethod
    def lte_10mhz(cls, center_frequency_hz: float = 1e9) -> "ChannelPowerTemplate":
        """Create LTE 10 MHz channel power template."""
        return cls(
            name="LTE 10 MHz Channel Power",
            description="Channel power measurement for 10 MHz LTE carrier",
            config=SAConfig(
                center_frequency_hz=center_frequency_hz,
                span_hz=20e6,
                rbw_hz=30e3,
                vbw_hz=300e3,
                reference_level_dbm=0.0,
                detector_type="RMS",
                trace_mode="WRITe",
                averaging_count=10,
            ),
            channel_bandwidth_hz=9.015e6,
        )

    @classmethod
    def nr_100mhz(cls, center_frequency_hz: float = 3.5e9) -> "ChannelPowerTemplate":
        """Create 5G NR 100 MHz channel power template."""
        return cls(
            name="5G NR 100 MHz Channel Power",
            description="Channel power measurement for 100 MHz NR carrier (FR1)",
            config=SAConfig(
                center_frequency_hz=center_frequency_hz,
                span_hz=200e6,
                rbw_hz=100e3,
                vbw_hz=1e6,
                reference_level_dbm=0.0,
                detector_type="RMS",
                trace_mode="WRITe",
                averaging_count=10,
            ),
            channel_bandwidth_hz=98.31e6,
        )

    @classmethod
    def wlan_80mhz(cls, center_frequency_hz: float = 5.21e9) -> "ChannelPowerTemplate":
        """Create WLAN 80 MHz channel power template."""
        return cls(
            name="WLAN 80 MHz Channel Power",
            description="Channel power measurement for 802.11ac/ax 80 MHz channel",
            config=SAConfig(
                center_frequency_hz=center_frequency_hz,
                span_hz=160e6,
                rbw_hz=100e3,
                vbw_hz=1e6,
                reference_level_dbm=0.0,
                detector_type="RMS",
                trace_mode="WRITe",
                averaging_count=10,
            ),
            channel_bandwidth_hz=80e6,
        )
