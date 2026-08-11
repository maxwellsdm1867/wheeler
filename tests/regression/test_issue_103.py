"""Regression test for issue 103: graph_health incorrectly diagnoses auth failures.

Issue: graph_health reports a password mismatch in wheeler.yaml even when no
wheeler.yaml was found and defaults are in use. It also never reports which
config file was loaded or explicitly states that defaults are in use.

This test verifies that the diagnosis distinguishes between:
1. No config file found (using built-in defaults)
2. Config file found but authentication rejected
3. Server unreachable vs. credentials rejected
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


class TestGraphHealthDiagnosis:
    """Test graph_health's diagnosis logic for various failure modes."""

    @pytest.mark.asyncio
    async def test_graph_health_auth_error_with_no_config_file(self):
        """When no config file is found, diagnosis should indicate defaults are in use.

        This is the core bug reported in issue 103: when the MCP server runs from
        a subdirectory where no wheeler.yaml exists, it uses built-in defaults.
        If those defaults don't match the running Neo4j, the diagnosis should NOT
        blame "the password in wheeler.yaml" (which was correct) but instead say
        that no config file was found and defaults are in use.
        """
        from wheeler.config import find_config_file

        repo_root = Path(__file__).resolve().parents[2]
        with patch("wheeler.config.find_config_file", return_value=None):
            from wheeler.mcp_core import graph_health

            mock_error = "The client is unauthorized due to authentication failure."
            mock_counts = {"_status": "offline", "_error": mock_error}
            with patch("wheeler.mcp_core.schema.get_status", new_callable=AsyncMock, return_value=mock_counts):
                result = await graph_health()

        assert result["status"] == "offline"
        assert result["blocking"] is True

        assert "diagnosis" in result
        assert "cause" in result
        assert "remediation" in result

        cause = result["cause"].lower()

        assert "wheeler.yaml" not in cause or "no " in cause or "not found" in cause or "default" in cause, (
            f"When no config file is found, diagnosis should not blame 'the password in wheeler.yaml'. "
            f"Got: {result['cause']}"
        )

        assert "default" in cause.lower() or "no config" in cause.lower() or "not found" in cause.lower(), (
            f"When no config file is found, diagnosis should mention defaults or absence of config. "
            f"Got: {result['cause']}"
        )

    @pytest.mark.asyncio
    async def test_graph_health_auth_error_distinguishes_server_vs_credentials(self):
        """Authentication errors should be reported differently from connection errors.

        Server-unreachable (connection error) is a different problem from
        credentials-rejected (authentication error), even though both result in
        an offline status.
        """
        from wheeler.mcp_core import graph_health

        auth_error = "The client is unauthorized due to authentication failure."
        conn_error = "Connection refused"

        auth_result = {"_status": "offline", "_error": auth_error}
        with patch("wheeler.mcp_core.schema.get_status", new_callable=AsyncMock, return_value=auth_result):
            auth_health = await graph_health()

        conn_result = {"_status": "offline", "_error": conn_error}
        with patch("wheeler.mcp_core.schema.get_status", new_callable=AsyncMock, return_value=conn_result):
            conn_health = await graph_health()

        auth_diag = auth_health.get("diagnosis", "").lower()
        conn_diag = conn_health.get("diagnosis", "").lower()

        assert auth_diag != conn_diag, (
            "Authentication and connection errors should have different diagnoses. "
            f"Auth: {auth_health.get('diagnosis')}, Conn: {conn_health.get('diagnosis')}"
        )

        assert "authentication" in auth_diag, f"Auth diagnosis should mention authentication: {auth_diag}"
        assert "authentication" not in conn_diag, f"Connection diagnosis should not mention authentication: {conn_diag}"

    @pytest.mark.asyncio
    async def test_graph_health_auth_error_no_destructive_remediation(self):
        """No remediation step should suggest destructive actions without evidence.

        The original issue showed a suggested fix: 'delete the DBMS in Neo4j
        Desktop'. This is destructive and should never be suggested unless the
        diagnosis can actually show the credential is unrecoverable.
        """
        from wheeler.mcp_core import graph_health

        mock_error = "The client is unauthorized due to authentication failure."
        mock_counts = {"_status": "offline", "_error": mock_error}
        with patch("wheeler.mcp_core.schema.get_status", new_callable=AsyncMock, return_value=mock_counts):
            result = await graph_health()

        fix_list = result.get("fix", [])
        if isinstance(fix_list, list):
            fix_text = " ".join(fix_list).lower()
        else:
            fix_text = result.get("remediation", "").lower()

        assert "delete" not in fix_text or "database" not in fix_text, (
            "Remediation should never suggest deleting the database without evidence "
            f"that the credential is unrecoverable. Got: {fix_text}"
        )
