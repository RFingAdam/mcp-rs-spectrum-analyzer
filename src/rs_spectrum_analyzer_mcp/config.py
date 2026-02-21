"""Configuration management using Pydantic settings."""

import logging

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .safety.validators import SafetyLimits


class SASettings(BaseSettings):
    """
    Spectrum Analyzer MCP server configuration.

    Settings can be configured via environment variables with SA_ prefix.
    """

    model_config = SettingsConfigDict(
        env_prefix="SA_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Connection defaults
    default_host: str = Field(default="192.168.1.100", description="Default SA host")
    default_port: int = Field(default=5025, description="Default SA port")
    connection_timeout: float = Field(default=5.0, description="Connection timeout in seconds")
    command_timeout: float = Field(default=30.0, description="Command timeout in seconds")

    # Safety limits
    max_input_power_dbm: float = Field(
        default=30.0, description="Maximum input power in dBm"
    )
    max_frequency_hz: float = Field(
        default=90e9, description="Maximum frequency in Hz"
    )
    min_frequency_hz: float = Field(
        default=2.0, description="Minimum frequency in Hz"
    )
    max_attenuation_db: float = Field(
        default=75.0, description="Maximum attenuation in dB"
    )
    min_attenuation_db: float = Field(
        default=0.0, description="Minimum attenuation in dB"
    )
    min_rbw_hz: float = Field(
        default=1.0, description="Minimum resolution bandwidth in Hz"
    )
    max_rbw_hz: float = Field(
        default=10e6, description="Maximum resolution bandwidth in Hz"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Log level")

    def get_safety_limits(self) -> SafetyLimits:
        """Create SafetyLimits from settings."""
        return SafetyLimits(
            max_input_power_dbm=self.max_input_power_dbm,
            max_frequency_hz=self.max_frequency_hz,
            min_frequency_hz=self.min_frequency_hz,
            max_attenuation_db=self.max_attenuation_db,
            min_attenuation_db=self.min_attenuation_db,
            min_rbw_hz=self.min_rbw_hz,
            max_rbw_hz=self.max_rbw_hz,
        )

    def configure_logging(self) -> None:
        """Configure logging based on settings."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )


# Global settings instance
_settings: SASettings | None = None


def get_settings() -> SASettings:
    """Get or create settings instance."""
    global _settings
    if _settings is None:
        _settings = SASettings()
    return _settings


def reload_settings() -> SASettings:
    """Reload settings from environment."""
    global _settings
    _settings = SASettings()
    return _settings
