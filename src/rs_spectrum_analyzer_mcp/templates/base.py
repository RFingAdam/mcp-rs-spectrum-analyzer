"""Base measurement template class for spectrum analyzer configurations."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class SAConfig:
    """Spectrum analyzer configuration for a template."""

    center_frequency_hz: float
    span_hz: float
    rbw_hz: float
    vbw_hz: float
    reference_level_dbm: float = 0.0
    attenuation_db: float | None = None  # None = auto
    detector_type: str = "RMS"
    trace_mode: str = "WRITe"
    sweep_time_s: float | None = None  # None = auto
    averaging_count: int = 1
    preamp_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "center_frequency_hz": self.center_frequency_hz,
            "span_hz": self.span_hz,
            "rbw_hz": self.rbw_hz,
            "vbw_hz": self.vbw_hz,
            "reference_level_dbm": self.reference_level_dbm,
            "attenuation_db": self.attenuation_db,
            "detector_type": self.detector_type,
            "trace_mode": self.trace_mode,
            "sweep_time_s": self.sweep_time_s,
            "averaging_count": self.averaging_count,
            "preamp_enabled": self.preamp_enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SAConfig":
        """Create from dictionary."""
        return cls(
            center_frequency_hz=data["center_frequency_hz"],
            span_hz=data["span_hz"],
            rbw_hz=data["rbw_hz"],
            vbw_hz=data["vbw_hz"],
            reference_level_dbm=data.get("reference_level_dbm", 0.0),
            attenuation_db=data.get("attenuation_db"),
            detector_type=data.get("detector_type", "RMS"),
            trace_mode=data.get("trace_mode", "WRITe"),
            sweep_time_s=data.get("sweep_time_s"),
            averaging_count=data.get("averaging_count", 1),
            preamp_enabled=data.get("preamp_enabled", False),
        )


@dataclass
class MeasurementTemplate:
    """
    Base class for spectrum analyzer measurement configurations.

    Templates define a complete measurement setup including frequency,
    amplitude, bandwidth, and detector settings. They can be saved to
    and loaded from JSON files for reuse.
    """

    name: str
    description: str
    config: SAConfig
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert template to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "config": self.config.to_dict(),
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "template_type": self.__class__.__name__,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MeasurementTemplate":
        """Create template from dictionary."""
        config = SAConfig.from_dict(data["config"])

        created_at = datetime.now()
        if data.get("created_at"):
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except ValueError:
                pass

        return cls(
            name=data["name"],
            description=data["description"],
            config=config,
            created_at=created_at,
            metadata=data.get("metadata", {}),
        )

    def save(self, filepath: str | Path) -> None:
        """Save template to JSON file."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str | Path) -> "MeasurementTemplate":
        """Load template from JSON file."""
        filepath = Path(filepath)

        with open(filepath) as f:
            data = json.load(f)

        template_type = data.get("template_type", "MeasurementTemplate")

        type_map = {
            "ChannelPowerTemplate": "channel_power",
            "ACLRTemplate": "aclr",
            "EMIPrecomplianceTemplate": "emi",
            "SpuriousEmissionTemplate": "spurious",
            "OccupiedBandwidthTemplate": "obw",
            "HarmonicTemplate": "harmonics",
        }

        if template_type in type_map:
            # Import and use specialized template
            module_name = type_map[template_type]
            import importlib

            mod = importlib.import_module(f".{module_name}", package=__package__)
            template_cls = getattr(mod, template_type)
            return template_cls.from_dict(data)

        return cls.from_dict(data)

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the template configuration."""
        return {
            "name": self.name,
            "description": self.description,
            "center_frequency_hz": self.config.center_frequency_hz,
            "span_hz": self.config.span_hz,
            "rbw_hz": self.config.rbw_hz,
            "vbw_hz": self.config.vbw_hz,
            "reference_level_dbm": self.config.reference_level_dbm,
            "detector_type": self.config.detector_type,
            "template_type": self.__class__.__name__,
        }

    async def apply(self, sa) -> None:
        """
        Apply this template to a spectrum analyzer.

        Args:
            sa: RSSpectrumAnalyzerDriver instance
        """
        cfg = self.config
        await sa.set_center_span(cfg.center_frequency_hz, cfg.span_hz)
        await sa.set_reference_level(cfg.reference_level_dbm)
        await sa.set_rbw(cfg.rbw_hz)
        await sa.set_vbw(cfg.vbw_hz)

        if cfg.attenuation_db is not None:
            await sa.set_attenuation(cfg.attenuation_db)

        if cfg.sweep_time_s is not None:
            await sa.set_sweep_time(cfg.sweep_time_s)

        if cfg.averaging_count > 1:
            await sa.set_averaging_count(cfg.averaging_count)

        await sa.set_preamp(cfg.preamp_enabled)

        from ..models.sa_types import DetectorType, TraceMode

        try:
            trace_mode = TraceMode(cfg.trace_mode)
            await sa.set_trace_mode(trace_mode)
        except ValueError:
            pass

        try:
            detector = DetectorType(cfg.detector_type)
            await sa.set_detector(detector)
        except ValueError:
            pass
