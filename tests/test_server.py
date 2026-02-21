"""Tests for MCP server creation."""

from spectrum_analyzer_mcp.server import create_server


class TestServer:
    """Test server creation."""

    def test_create_server(self):
        server = create_server()
        assert server is not None
        assert server.name == "spectrum-analyzer-mcp"
