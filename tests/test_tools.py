"""Tests for MCP tool definitions and handler routing."""

import json

import pytest

from rs_spectrum_analyzer_mcp.tools import _TOOL_HANDLERS, get_tools, handle_tool


class TestToolDefinitions:
    """Test that tool definitions are valid."""

    def test_get_tools_returns_list(self):
        tools = get_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_all_tools_have_names(self):
        tools = get_tools()
        for tool in tools:
            assert tool.name, f"Tool missing name: {tool}"
            assert tool.name.startswith("sa_"), f"Tool name must start with 'sa_': {tool.name}"

    def test_all_tools_have_descriptions(self):
        tools = get_tools()
        for tool in tools:
            assert tool.description, f"Tool {tool.name} missing description"

    def test_all_tools_have_schemas(self):
        tools = get_tools()
        for tool in tools:
            assert tool.inputSchema is not None, f"Tool {tool.name} missing schema"
            assert tool.inputSchema["type"] == "object"

    def test_tool_count(self):
        """Verify expected number of tools."""
        tools = get_tools()
        # We defined ~50 tools
        assert len(tools) >= 45

    def test_all_tools_have_handlers(self):
        """Every tool definition must have a handler registered."""
        tools = get_tools()
        tool_names = {t.name for t in tools}
        handler_names = set(_TOOL_HANDLERS.keys())

        missing_handlers = tool_names - handler_names
        assert not missing_handlers, f"Tools missing handlers: {missing_handlers}"

    def test_no_orphan_handlers(self):
        """No handler without a tool definition."""
        tools = get_tools()
        tool_names = {t.name for t in tools}
        handler_names = set(_TOOL_HANDLERS.keys())

        orphan_handlers = handler_names - tool_names
        assert not orphan_handlers, f"Handlers without tools: {orphan_handlers}"


class TestToolCategories:
    """Test that all expected tool categories are present."""

    def _tool_names(self) -> set[str]:
        return {t.name for t in get_tools()}

    def test_connection_tools(self):
        names = self._tool_names()
        assert "sa_discover" in names
        assert "sa_connect" in names
        assert "sa_disconnect" in names
        assert "sa_identify" in names
        assert "sa_get_status" in names

    def test_frequency_tools(self):
        names = self._tool_names()
        assert "sa_set_center_span" in names
        assert "sa_set_start_stop" in names
        assert "sa_set_frequency_step" in names
        assert "sa_full_span" in names

    def test_amplitude_tools(self):
        names = self._tool_names()
        assert "sa_set_reference_level" in names
        assert "sa_set_attenuation" in names
        assert "sa_set_preamp" in names
        assert "sa_set_scale" in names

    def test_bandwidth_tools(self):
        names = self._tool_names()
        assert "sa_set_rbw" in names
        assert "sa_set_vbw" in names
        assert "sa_set_sweep_time" in names
        assert "sa_auto_coupling" in names

    def test_trace_tools(self):
        names = self._tool_names()
        assert "sa_get_trace_data" in names
        assert "sa_set_trace_mode" in names
        assert "sa_set_averaging_count" in names
        assert "sa_clear_trace" in names
        assert "sa_set_detector" in names

    def test_marker_tools(self):
        names = self._tool_names()
        assert "sa_set_marker" in names
        assert "sa_get_marker" in names
        assert "sa_peak_search" in names
        assert "sa_next_peak" in names
        assert "sa_marker_to_center" in names
        assert "sa_marker_delta" in names
        assert "sa_marker_bandwidth" in names

    def test_measurement_tools(self):
        names = self._tool_names()
        assert "sa_measure_channel_power" in names
        assert "sa_measure_aclr" in names
        assert "sa_measure_obw" in names
        assert "sa_measure_sem" in names
        assert "sa_measure_evm" in names
        assert "sa_measure_ccdf" in names

    def test_sweep_tools(self):
        names = self._tool_names()
        assert "sa_single_sweep" in names
        assert "sa_continuous_sweep" in names
        assert "sa_set_trigger" in names

    def test_export_tools(self):
        names = self._tool_names()
        assert "sa_save_trace_csv" in names
        assert "sa_save_screenshot" in names
        assert "sa_export_trace_data" in names

    def test_scpi_tools(self):
        names = self._tool_names()
        assert "sa_scpi_send" in names
        assert "sa_scpi_query" in names
        assert "sa_reset" in names
        assert "sa_preset" in names

    def test_template_tools(self):
        names = self._tool_names()
        assert "sa_list_templates" in names
        assert "sa_load_template" in names
        assert "sa_apply_template" in names

    def test_limit_tools(self):
        names = self._tool_names()
        assert "sa_define_limit" in names
        assert "sa_check_limits" in names
        assert "sa_clear_limits" in names
        assert "sa_list_limits" in names

    def test_state_tools(self):
        names = self._tool_names()
        assert "sa_save_state" in names
        assert "sa_load_state" in names
        assert "sa_get_full_state" in names


class TestHandleToolRouting:
    """Test that handle_tool routes to correct handlers."""

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        result = await handle_tool("sa_nonexistent", {})
        assert len(result) == 1
        assert "Error" in result[0].text

    @pytest.mark.asyncio
    async def test_list_templates_no_connection_needed(self):
        """sa_list_templates doesn't need a connection."""
        result = await handle_tool("sa_list_templates", {})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "channel_power" in data
        assert "aclr" in data
        assert "emi" in data

    @pytest.mark.asyncio
    async def test_clear_limits_no_connection_needed(self):
        result = await handle_tool("sa_clear_limits", {})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert data["limits_cleared"] is True

    @pytest.mark.asyncio
    async def test_list_limits_no_connection_needed(self):
        result = await handle_tool("sa_list_limits", {})
        assert len(result) == 1
        data = json.loads(result[0].text)
        assert "limits" in data

    @pytest.mark.asyncio
    async def test_define_limit(self):
        result = await handle_tool("sa_define_limit", {
            "name": "test_limit",
            "segments": [
                {"start_freq_hz": 1e9, "stop_freq_hz": 2e9, "max_db": -30.0},
            ],
        })
        data = json.loads(result[0].text)
        assert data["limit_defined"] == "test_limit"

    @pytest.mark.asyncio
    async def test_load_template_builtin(self):
        result = await handle_tool("sa_load_template", {
            "template_name": "cispr_32_class_b",
        })
        data = json.loads(result[0].text)
        assert data["name"] == "CISPR 32 Class B Conducted"

    @pytest.mark.asyncio
    async def test_load_template_unknown(self):
        result = await handle_tool("sa_load_template", {
            "template_name": "nonexistent",
        })
        assert "Error" in result[0].text
