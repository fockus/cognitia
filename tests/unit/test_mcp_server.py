"""Tests for MCP server assembly."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestCreateServer:
    def test_create_server_headless_mode(self):
        mock_fastmcp_cls = MagicMock()
        mock_server = MagicMock()
        mock_fastmcp_cls.return_value = mock_server
        mock_server.tool = MagicMock(return_value=lambda f: f)

        with patch.dict(
            "sys.modules", {"fastmcp": MagicMock(FastMCP=mock_fastmcp_cls)}
        ):
            from cognitia.mcp._server import create_server

            server = create_server(mode="headless")
            assert server is mock_server
            mock_fastmcp_cls.assert_called_once()

    def test_create_server_full_mode(self):
        mock_fastmcp_cls = MagicMock()
        mock_server = MagicMock()
        mock_fastmcp_cls.return_value = mock_server
        mock_server.tool = MagicMock(return_value=lambda f: f)

        with patch.dict(
            "sys.modules", {"fastmcp": MagicMock(FastMCP=mock_fastmcp_cls)}
        ):
            from cognitia.mcp._server import create_server

            server = create_server(mode="full")
            assert server is mock_server

    def test_create_server_without_fastmcp_raises(self):
        with patch.dict("sys.modules", {"fastmcp": None}):
            import importlib
            from cognitia.mcp import _server

            importlib.reload(_server)
            with pytest.raises(ImportError, match="FastMCP is required"):
                _server.create_server(mode="headless")
