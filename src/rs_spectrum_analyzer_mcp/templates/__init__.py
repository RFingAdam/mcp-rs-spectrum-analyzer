"""Measurement templates for common spectrum analyzer test scenarios."""

from .aclr import ACLRTemplate
from .base import MeasurementTemplate
from .channel_power import ChannelPowerTemplate
from .emi import EMIPrecomplianceTemplate
from .harmonics import HarmonicTemplate
from .obw import OccupiedBandwidthTemplate
from .spurious import SpuriousEmissionTemplate

__all__ = [
    "ACLRTemplate",
    "ChannelPowerTemplate",
    "EMIPrecomplianceTemplate",
    "HarmonicTemplate",
    "MeasurementTemplate",
    "OccupiedBandwidthTemplate",
    "SpuriousEmissionTemplate",
]
