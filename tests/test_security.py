"""Tests for Wave 1 security hardening: SCPI sanitization, path validation, raw SCPI guards."""

import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from rs_spectrum_analyzer_mcp.config import SASettings
from rs_spectrum_analyzer_mcp.safety.validators import sanitize_scpi_param, validate_safe_path

# =============================================================================
# Issue 1: sanitize_scpi_param tests
# =============================================================================


class TestSanitizeScpiParam:
    """Tests for SCPI parameter sanitization."""

    def test_clean_string_passes(self):
        """Normal strings should pass through unchanged."""
        assert sanitize_scpi_param("QPSK") == "QPSK"
        assert sanitize_scpi_param("16QAM") == "16QAM"
        assert sanitize_scpi_param("64QAM") == "64QAM"
        assert sanitize_scpi_param("hello_world") == "hello_world"

    def test_empty_string_passes(self):
        """Empty string is valid (no dangerous chars)."""
        assert sanitize_scpi_param("") == ""

    def test_numeric_string_passes(self):
        """Numeric strings are fine."""
        assert sanitize_scpi_param("1000") == "1000"
        assert sanitize_scpi_param("3.14159") == "3.14159"

    def test_filepath_string_passes(self):
        """File paths without dangerous chars should pass."""
        assert sanitize_scpi_param("C:/Data/screenshot.png") == "C:/Data/screenshot.png"

    def test_rejects_semicolon_injection(self):
        """Semicolon is the SCPI command separator -- must be rejected."""
        with pytest.raises(ValueError, match="SCPI injection rejected"):
            sanitize_scpi_param("QPSK;*RST")

    def test_rejects_semicolon_at_start(self):
        with pytest.raises(ValueError, match="SCPI injection rejected"):
            sanitize_scpi_param(";*RST")

    def test_rejects_semicolon_at_end(self):
        with pytest.raises(ValueError, match="SCPI injection rejected"):
            sanitize_scpi_param("QPSK;")

    def test_rejects_newline_injection(self):
        """Newlines could inject separate SCPI commands."""
        with pytest.raises(ValueError, match="SCPI injection rejected"):
            sanitize_scpi_param("QPSK\n*RST")

    def test_rejects_carriage_return_injection(self):
        with pytest.raises(ValueError, match="SCPI injection rejected"):
            sanitize_scpi_param("QPSK\r*RST")

    def test_rejects_crlf_injection(self):
        with pytest.raises(ValueError, match="SCPI injection rejected"):
            sanitize_scpi_param("QPSK\r\n*RST")

    def test_rejects_leading_star(self):
        """Leading * could trigger instrument commands like *RST, *CLS, *OPC."""
        with pytest.raises(ValueError, match="must not start with"):
            sanitize_scpi_param("*RST")

    def test_rejects_star_cls(self):
        with pytest.raises(ValueError, match="must not start with"):
            sanitize_scpi_param("*CLS")

    def test_rejects_star_opc(self):
        with pytest.raises(ValueError, match="must not start with"):
            sanitize_scpi_param("*OPC")

    def test_star_in_middle_is_ok(self):
        """Star in middle of string is not a command trigger."""
        assert sanitize_scpi_param("data*2") == "data*2"

    def test_rejects_non_string_type(self):
        """Must be a string, not int/float/etc."""
        with pytest.raises(ValueError, match="must be a string"):
            sanitize_scpi_param(123)  # type: ignore[arg-type]

    def test_rejects_none(self):
        with pytest.raises(ValueError, match="must be a string"):
            sanitize_scpi_param(None)  # type: ignore[arg-type]

    def test_complex_injection_payload(self):
        """Combined attack with semicolon + star command."""
        with pytest.raises(ValueError, match="SCPI injection rejected"):
            sanitize_scpi_param("QPSK;*RST;*CLS")

    def test_newline_only(self):
        with pytest.raises(ValueError, match="SCPI injection rejected"):
            sanitize_scpi_param("\n")

    def test_scpi_filepath_injection(self):
        """Filepath with injected SCPI command separator."""
        with pytest.raises(ValueError, match="SCPI injection rejected"):
            sanitize_scpi_param("test.png';*RST;'")


# =============================================================================
# Issue 2: validate_safe_path tests
# =============================================================================


class TestValidateSafePath:
    """Tests for file path validation against traversal and symlinks."""

    def test_simple_filename(self, tmp_path):
        """Simple filename resolves within base_dir."""
        result = validate_safe_path("state.json", tmp_path)
        assert result == tmp_path / "state.json"

    def test_nested_path(self, tmp_path):
        """Nested path resolves within base_dir."""
        result = validate_safe_path("sub/dir/state.json", tmp_path)
        assert result == tmp_path / "sub" / "dir" / "state.json"

    def test_dot_slash_path(self, tmp_path):
        """Current directory reference is fine."""
        result = validate_safe_path("./state.json", tmp_path)
        assert result == tmp_path / "state.json"

    def test_rejects_parent_traversal(self, tmp_path):
        """../ must be rejected."""
        with pytest.raises(ValueError, match="Path traversal denied"):
            validate_safe_path("../etc/passwd", tmp_path)

    def test_rejects_deep_traversal(self, tmp_path):
        """Multiple ../ levels must be rejected."""
        with pytest.raises(ValueError, match="Path traversal denied"):
            validate_safe_path("../../etc/shadow", tmp_path)

    def test_rejects_traversal_in_middle(self, tmp_path):
        """Traversal hidden in the middle of a path."""
        with pytest.raises(ValueError, match="Path traversal denied"):
            validate_safe_path("sub/../../../etc/passwd", tmp_path)

    def test_rejects_absolute_path_outside(self, tmp_path):
        """Absolute path outside base_dir must be rejected."""
        with pytest.raises(ValueError, match="Path traversal denied"):
            validate_safe_path("/etc/passwd", tmp_path)

    def test_absolute_path_inside_base(self, tmp_path):
        """Absolute path inside base_dir should work."""
        inner = tmp_path / "myfile.json"
        result = validate_safe_path(str(inner), tmp_path)
        assert result == inner

    def test_rejects_symlink_escape(self, tmp_path):
        """Symlink pointing outside base_dir must be rejected."""
        # Create a symlink inside tmp_path that points to /tmp
        link = tmp_path / "evil_link"
        link.symlink_to("/tmp")

        # May be caught by is_relative_to check or explicit symlink check
        with pytest.raises(ValueError, match="(Path traversal denied|Symlink escape denied)"):
            validate_safe_path("evil_link/data.json", tmp_path)

    def test_symlink_within_base_dir_is_ok(self, tmp_path):
        """Symlink within base_dir pointing to another location in base_dir is fine."""
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        link = tmp_path / "link"
        link.symlink_to(target_dir)

        result = validate_safe_path("link/file.json", tmp_path)
        assert result == target_dir / "file.json"

    def test_path_object_input(self, tmp_path):
        """Should accept Path objects as well as strings."""
        result = validate_safe_path(Path("state.json"), tmp_path)
        assert result == tmp_path / "state.json"

    def test_base_dir_as_string(self, tmp_path):
        """Should accept string base_dir."""
        result = validate_safe_path("state.json", str(tmp_path))
        assert result == tmp_path / "state.json"

    def test_dot_dot_normalized_still_inside(self, tmp_path):
        """sub/../file.json should resolve to base/file.json (inside base)."""
        result = validate_safe_path("sub/../file.json", tmp_path)
        assert result == tmp_path / "file.json"


# =============================================================================
# Issue 3: Raw SCPI guard tests
# =============================================================================


class TestRawScpiConfig:
    """Tests for the allow_raw_scpi configuration setting."""

    def test_default_allows_raw_scpi(self):
        """Default settings should allow raw SCPI for backwards compatibility."""
        settings = SASettings()
        assert settings.allow_raw_scpi is True

    def test_can_disable_raw_scpi(self):
        """Should be possible to disable raw SCPI via settings."""
        settings = SASettings(allow_raw_scpi=False)
        assert settings.allow_raw_scpi is False

    def test_env_var_disables_raw_scpi(self, monkeypatch):
        """SA_ALLOW_RAW_SCPI=false env var should disable raw SCPI."""
        monkeypatch.setenv("SA_ALLOW_RAW_SCPI", "false")
        settings = SASettings()
        assert settings.allow_raw_scpi is False

    def test_env_var_enables_raw_scpi(self, monkeypatch):
        """SA_ALLOW_RAW_SCPI=true env var should enable raw SCPI."""
        monkeypatch.setenv("SA_ALLOW_RAW_SCPI", "true")
        settings = SASettings()
        assert settings.allow_raw_scpi is True


class TestRawScpiGuard:
    """Tests for raw SCPI handler guards in tools.py."""

    @pytest.fixture
    def mock_settings_allow(self):
        """Settings with raw SCPI allowed."""
        settings = SASettings(allow_raw_scpi=True)
        return settings

    @pytest.fixture
    def mock_settings_deny(self):
        """Settings with raw SCPI denied."""
        settings = SASettings(allow_raw_scpi=False)
        return settings

    @pytest.mark.asyncio
    async def test_scpi_send_blocked_when_disabled(self, mock_settings_deny):
        """sa_scpi_send should return error when allow_raw_scpi=False."""
        from mcp.types import CallToolResult

        from rs_spectrum_analyzer_mcp.tools import _handle_scpi_send

        with patch("rs_spectrum_analyzer_mcp.tools.get_settings", return_value=mock_settings_deny):
            result = await _handle_scpi_send({"command": "*RST"})
            # _handle_scpi_send returns CallToolResult with isError=True when blocked
            if isinstance(result, CallToolResult):
                assert result.isError is True
                assert len(result.content) == 1
                assert "disabled" in result.content[0].text.lower()
            else:
                assert len(result) == 1
                assert "disabled" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_scpi_query_blocked_when_disabled(self, mock_settings_deny):
        """sa_scpi_query should return error when allow_raw_scpi=False."""
        from mcp.types import CallToolResult

        from rs_spectrum_analyzer_mcp.tools import _handle_scpi_query

        with patch("rs_spectrum_analyzer_mcp.tools.get_settings", return_value=mock_settings_deny):
            result = await _handle_scpi_query({"command": "*IDN?"})
            # _handle_scpi_query returns CallToolResult with isError=True when blocked
            if isinstance(result, CallToolResult):
                assert result.isError is True
                assert len(result.content) == 1
                assert "disabled" in result.content[0].text.lower()
            else:
                assert len(result) == 1
                assert "disabled" in result[0].text.lower()

    @pytest.mark.asyncio
    async def test_scpi_send_allowed_when_enabled(self, mock_settings_allow, mock_scpi_socket):
        """sa_scpi_send should execute when allow_raw_scpi=True."""
        from rs_spectrum_analyzer_mcp.tools import _handle_scpi_send

        mock_sa = AsyncMock()
        mock_sa.scpi_send = AsyncMock()

        with (
            patch("rs_spectrum_analyzer_mcp.tools.get_settings", return_value=mock_settings_allow),
            patch("rs_spectrum_analyzer_mcp.tools._get_sa", return_value=mock_sa),
        ):
            result = await _handle_scpi_send({"command": "SENS:FREQ:CENT?"})
            assert len(result) == 1
            assert "sent" in result[0].text.lower()
            mock_sa.scpi_send.assert_called_once_with("SENS:FREQ:CENT?")

    @pytest.mark.asyncio
    async def test_scpi_query_allowed_when_enabled(self, mock_settings_allow, mock_scpi_socket):
        """sa_scpi_query should execute when allow_raw_scpi=True."""
        from rs_spectrum_analyzer_mcp.tools import _handle_scpi_query

        mock_sa = AsyncMock()
        mock_sa.scpi_query = AsyncMock(return_value="1.0")

        with (
            patch("rs_spectrum_analyzer_mcp.tools.get_settings", return_value=mock_settings_allow),
            patch("rs_spectrum_analyzer_mcp.tools._get_sa", return_value=mock_sa),
        ):
            result = await _handle_scpi_query({"command": "*IDN?"})
            assert len(result) == 1
            assert "response" in result[0].text.lower()
            mock_sa.scpi_query.assert_called_once_with("*IDN?")

    @pytest.mark.asyncio
    async def test_scpi_send_logs_warning(self, mock_settings_allow, caplog):
        """Raw SCPI send should log WARNING with the command string."""
        from rs_spectrum_analyzer_mcp.tools import _handle_scpi_send

        mock_sa = AsyncMock()
        mock_sa.scpi_send = AsyncMock()

        with (
            patch("rs_spectrum_analyzer_mcp.tools.get_settings", return_value=mock_settings_allow),
            patch("rs_spectrum_analyzer_mcp.tools._get_sa", return_value=mock_sa),
            caplog.at_level(logging.WARNING, logger="rs_spectrum_analyzer_mcp.tools"),
        ):
            await _handle_scpi_send({"command": "SENS:FREQ:CENT 1e9"})
            assert any("Raw SCPI send" in record.message for record in caplog.records)
            assert any("SENS:FREQ:CENT 1e9" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_scpi_query_logs_warning(self, mock_settings_allow, caplog):
        """Raw SCPI query should log WARNING with the command string."""
        from rs_spectrum_analyzer_mcp.tools import _handle_scpi_query

        mock_sa = AsyncMock()
        mock_sa.scpi_query = AsyncMock(return_value="1.0")

        with (
            patch("rs_spectrum_analyzer_mcp.tools.get_settings", return_value=mock_settings_allow),
            patch("rs_spectrum_analyzer_mcp.tools._get_sa", return_value=mock_sa),
            caplog.at_level(logging.WARNING, logger="rs_spectrum_analyzer_mcp.tools"),
        ):
            await _handle_scpi_query({"command": "*IDN?"})
            assert any("Raw SCPI query" in record.message for record in caplog.records)
            assert any("*IDN?" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_scpi_send_blocked_logs_warning(self, mock_settings_deny, caplog):
        """Blocked raw SCPI send should also log WARNING."""
        from rs_spectrum_analyzer_mcp.tools import _handle_scpi_send

        with (
            patch("rs_spectrum_analyzer_mcp.tools.get_settings", return_value=mock_settings_deny),
            caplog.at_level(logging.WARNING, logger="rs_spectrum_analyzer_mcp.tools"),
        ):
            await _handle_scpi_send({"command": "*RST"})
            assert any("blocked" in record.message.lower() for record in caplog.records)


# =============================================================================
# Integration: sanitizer applied in tools.py handlers
# =============================================================================


class TestScpiSanitizationInHandlers:
    """Tests that SCPI sanitization is wired into tool handlers correctly."""

    @pytest.mark.asyncio
    async def test_evm_handler_rejects_injection(self):
        """_handle_measure_evm should reject modulation with semicolons."""
        from rs_spectrum_analyzer_mcp.tools import _handle_measure_evm

        mock_sa = AsyncMock()
        with patch("rs_spectrum_analyzer_mcp.tools._get_sa", return_value=mock_sa):
            # The handler should raise ValueError from sanitize_scpi_param
            # which gets caught by the outer handler and returned as error
            with pytest.raises(ValueError, match="SCPI injection rejected"):
                await _handle_measure_evm({
                    "modulation": "QPSK;*RST",
                    "host": "192.168.1.100",
                    "port": 5025,
                })

    @pytest.mark.asyncio
    async def test_screenshot_handler_rejects_injection(self):
        """_handle_save_screenshot should reject filepath with semicolons."""
        from rs_spectrum_analyzer_mcp.tools import _handle_save_screenshot

        mock_sa = AsyncMock()
        with patch("rs_spectrum_analyzer_mcp.tools._get_sa", return_value=mock_sa):
            with pytest.raises(ValueError, match="SCPI injection rejected"):
                await _handle_save_screenshot({
                    "filepath": "test.png';*RST;'",
                    "host": "192.168.1.100",
                    "port": 5025,
                })

    @pytest.mark.asyncio
    async def test_screenshot_handler_rejects_newline_injection(self):
        """_handle_save_screenshot should reject filepath with newlines."""
        from rs_spectrum_analyzer_mcp.tools import _handle_save_screenshot

        mock_sa = AsyncMock()
        with patch("rs_spectrum_analyzer_mcp.tools._get_sa", return_value=mock_sa):
            with pytest.raises(ValueError, match="SCPI injection rejected"):
                await _handle_save_screenshot({
                    "filepath": "test.png\n*RST",
                    "host": "192.168.1.100",
                    "port": 5025,
                })


class TestPathValidationInHandlers:
    """Tests that path validation is wired into tool handlers correctly."""

    @pytest.mark.asyncio
    async def test_save_state_rejects_traversal(self):
        """_handle_save_state should reject names with path traversal."""
        from rs_spectrum_analyzer_mcp.tools import _handle_save_state, _state_manager

        mock_sa = AsyncMock()
        mock_sa.scpi_query = AsyncMock(return_value="1000000000")
        mock_sa.info = None

        with (
            patch("rs_spectrum_analyzer_mcp.tools._get_sa", return_value=mock_sa),
            patch.object(
                _state_manager, "capture_state", new_callable=AsyncMock
            ) as mock_capture,
        ):
            mock_state = AsyncMock()
            mock_state.notes = ""
            mock_capture.return_value = mock_state

            with pytest.raises(ValueError, match="Path traversal denied"):
                await _handle_save_state({
                    "name": "../../etc/evil",
                    "host": "192.168.1.100",
                    "port": 5025,
                })

    @pytest.mark.asyncio
    async def test_load_state_rejects_traversal(self):
        """_handle_load_state should reject names with path traversal."""
        from rs_spectrum_analyzer_mcp.tools import _handle_load_state

        mock_sa = AsyncMock()
        with patch("rs_spectrum_analyzer_mcp.tools._get_sa", return_value=mock_sa):
            with pytest.raises(ValueError, match="Path traversal denied"):
                await _handle_load_state({
                    "name": "../../../etc/passwd",
                    "host": "192.168.1.100",
                    "port": 5025,
                })
