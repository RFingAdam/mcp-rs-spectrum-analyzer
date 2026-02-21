"""Occupied bandwidth measurement template."""

from dataclasses import dataclass
from typing import Any

from .base import MeasurementTemplate, SAConfig


@dataclass
class OccupiedBandwidthTemplate(MeasurementTemplate):
    """
    Occupied bandwidth measurement template.

    Configures the spectrum analyzer for occupied bandwidth measurement
    (typically 99% power bandwidth).
    """

    power_percentage: float = 99.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        d = super().to_dict()
        d["power_percentage"] = self.power_percentage
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OccupiedBandwidthTemplate":
        """Create from dictionary."""
        config = SAConfig.from_dict(data["config"])
        return cls(
            name=data["name"],
            description=data["description"],
            config=config,
            metadata=data.get("metadata", {}),
            power_percentage=data.get("power_percentage", 99.0),
        )

    @classmethod
    def lte_10mhz(cls, center_frequency_hz: float = 1e9) -> "OccupiedBandwidthTemplate":
        """Create OBW template for 10 MHz LTE."""
        return cls(
            name="LTE 10 MHz OBW",
            description="Occupied bandwidth measurement for 10 MHz LTE carrier",
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
            power_percentage=99.0,
        )

    @classmethod
    def generic(
        cls,
        center_frequency_hz: float,
        span_hz: float,
    ) -> "OccupiedBandwidthTemplate":
        """Create generic OBW template."""
        return cls(
            name="Generic OBW",
            description=f"OBW measurement at {center_frequency_hz / 1e6:.1f} MHz",
            config=SAConfig(
                center_frequency_hz=center_frequency_hz,
                span_hz=span_hz,
                rbw_hz=span_hz / 1000,
                vbw_hz=span_hz / 300,
                reference_level_dbm=0.0,
                detector_type="RMS",
                trace_mode="WRITe",
                averaging_count=10,
            ),
            power_percentage=99.0,
        )
