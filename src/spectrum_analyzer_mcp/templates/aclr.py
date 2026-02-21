"""Adjacent Channel Leakage Ratio (ACLR) measurement template."""

from dataclasses import dataclass
from typing import Any

from .base import MeasurementTemplate, SAConfig


@dataclass
class ACLRTemplate(MeasurementTemplate):
    """
    ACLR measurement template.

    Configures the spectrum analyzer for adjacent channel leakage ratio
    measurement with standard-specific channel and adjacent channel offsets.
    """

    channel_bandwidth_hz: float = 10e6
    adjacent_bandwidth_hz: float = 10e6
    adjacent_offset_hz: float = 10e6
    alternate_offset_hz: float | None = None
    num_adjacent_channels: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d = super().to_dict()
        d["channel_bandwidth_hz"] = self.channel_bandwidth_hz
        d["adjacent_bandwidth_hz"] = self.adjacent_bandwidth_hz
        d["adjacent_offset_hz"] = self.adjacent_offset_hz
        d["alternate_offset_hz"] = self.alternate_offset_hz
        d["num_adjacent_channels"] = self.num_adjacent_channels
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ACLRTemplate":
        """Create from dictionary."""
        config = SAConfig.from_dict(data["config"])
        return cls(
            name=data["name"],
            description=data["description"],
            config=config,
            metadata=data.get("metadata", {}),
            channel_bandwidth_hz=data.get("channel_bandwidth_hz", 10e6),
            adjacent_bandwidth_hz=data.get("adjacent_bandwidth_hz", 10e6),
            adjacent_offset_hz=data.get("adjacent_offset_hz", 10e6),
            alternate_offset_hz=data.get("alternate_offset_hz"),
            num_adjacent_channels=data.get("num_adjacent_channels", 1),
        )

    @classmethod
    def lte_10mhz(cls, center_frequency_hz: float = 1e9) -> "ACLRTemplate":
        """Create LTE 10 MHz E-UTRA ACLR template."""
        return cls(
            name="LTE 10 MHz ACLR (E-UTRA)",
            description="ACLR measurement per 3GPP TS 36.101 for 10 MHz LTE",
            config=SAConfig(
                center_frequency_hz=center_frequency_hz,
                span_hz=50e6,
                rbw_hz=30e3,
                vbw_hz=300e3,
                reference_level_dbm=0.0,
                detector_type="RMS",
                trace_mode="WRITe",
                averaging_count=20,
            ),
            channel_bandwidth_hz=9.015e6,
            adjacent_bandwidth_hz=9.015e6,
            adjacent_offset_hz=10e6,
            alternate_offset_hz=20e6,
            num_adjacent_channels=2,
        )

    @classmethod
    def nr_100mhz(cls, center_frequency_hz: float = 3.5e9) -> "ACLRTemplate":
        """Create 5G NR 100 MHz ACLR template."""
        return cls(
            name="5G NR 100 MHz ACLR",
            description="ACLR measurement per 3GPP TS 38.101-1 for 100 MHz NR FR1",
            config=SAConfig(
                center_frequency_hz=center_frequency_hz,
                span_hz=500e6,
                rbw_hz=100e3,
                vbw_hz=1e6,
                reference_level_dbm=0.0,
                detector_type="RMS",
                trace_mode="WRITe",
                averaging_count=20,
            ),
            channel_bandwidth_hz=98.31e6,
            adjacent_bandwidth_hz=98.31e6,
            adjacent_offset_hz=100e6,
            num_adjacent_channels=1,
        )

    @classmethod
    def wlan_80mhz(cls, center_frequency_hz: float = 5.21e9) -> "ACLRTemplate":
        """Create WLAN 80 MHz ACLR template."""
        return cls(
            name="WLAN 80 MHz ACLR",
            description="ACLR measurement for 802.11ac/ax 80 MHz channel",
            config=SAConfig(
                center_frequency_hz=center_frequency_hz,
                span_hz=320e6,
                rbw_hz=100e3,
                vbw_hz=1e6,
                reference_level_dbm=0.0,
                detector_type="RMS",
                trace_mode="WRITe",
                averaging_count=20,
            ),
            channel_bandwidth_hz=80e6,
            adjacent_bandwidth_hz=80e6,
            adjacent_offset_hz=80e6,
            num_adjacent_channels=1,
        )
