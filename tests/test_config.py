"""Tests for configuration management."""



from rs_spectrum_analyzer_mcp.config import SASettings, get_settings, reload_settings
from rs_spectrum_analyzer_mcp.safety.validators import SafetyLimits


class TestSASettings:
    """Test SASettings configuration."""

    def test_defaults(self):
        settings = SASettings()
        assert settings.default_host == "192.168.1.100"
        assert settings.default_port == 5025
        assert settings.connection_timeout == 5.0
        assert settings.command_timeout == 30.0
        assert settings.max_input_power_dbm == 30.0
        assert settings.max_frequency_hz == 90e9
        assert settings.min_frequency_hz == 2.0
        assert settings.log_level == "INFO"

    def test_get_safety_limits(self):
        settings = SASettings()
        limits = settings.get_safety_limits()
        assert isinstance(limits, SafetyLimits)
        assert limits.max_input_power_dbm == 30.0
        assert limits.max_frequency_hz == 90e9

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("SA_DEFAULT_HOST", "10.0.0.1")
        monkeypatch.setenv("SA_DEFAULT_PORT", "5030")
        settings = SASettings()
        assert settings.default_host == "10.0.0.1"
        assert settings.default_port == 5030

    def test_configure_logging(self):
        settings = SASettings()
        # Should not raise
        settings.configure_logging()


class TestGetSettings:
    """Test settings singleton."""

    def test_returns_settings(self):
        settings = reload_settings()
        assert isinstance(settings, SASettings)

    def test_get_settings_caches(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_reload_creates_new(self):
        s1 = get_settings()
        s2 = reload_settings()
        assert s1 is not s2
