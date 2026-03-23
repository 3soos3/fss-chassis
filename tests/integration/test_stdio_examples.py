"""Integration tests for the bundled example extensions.

DELETE THIS FILE when you remove the example extensions during forking.
These tests verify the example_echo tool, example_resource, and
example_prompt that ship with the template. They are automatically
skipped if the example extensions have been removed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Auto-skip this entire file when example extensions are absent
_EXAMPLE_TOOL = (
    Path(__file__).parent.parent.parent
    / "src"
    / "mcp_chassis"
    / "extensions"
    / "tools"
    / "example_tool.py"
)
pytestmark = pytest.mark.skipif(
    not _EXAMPLE_TOOL.exists(),
    reason="Example extensions removed (expected after forking)",
)


class TestExampleTool:
    """Tests for the example_echo tool."""

    @pytest.mark.asyncio
    async def test_tools_list_contains_example_echo(self, mcp_client):
        """tools/list should include the example_echo tool."""
        response = await mcp_client.send_request("tools/list")
        tools = response["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "example_echo" in tool_names

    @pytest.mark.asyncio
    async def test_call_example_echo(self, mcp_client):
        """Calling example_echo should echo back the message."""
        response = await mcp_client.send_request(
            "tools/call",
            {"name": "example_echo", "arguments": {"message": "hello from test"}},
        )
        assert "result" in response
        result = response["result"]
        assert result.get("isError") is not True
        content = result["content"]
        assert len(content) > 0
        assert content[0]["text"] == "hello from test"

    @pytest.mark.asyncio
    async def test_call_example_echo_missing_arg(self, mcp_client):
        """Calling example_echo without required 'message' should error."""
        response = await mcp_client.send_request(
            "tools/call",
            {"name": "example_echo", "arguments": {}},
        )
        assert "result" in response
        result = response["result"]
        assert result.get("isError") is True

    @pytest.mark.asyncio
    async def test_health_check_lists_example_echo(self, mcp_client):
        """Health check should list example_echo in tools_loaded."""
        response = await mcp_client.send_request(
            "tools/call",
            {"name": "__health_check", "arguments": {}},
        )
        data = json.loads(response["result"]["content"][0]["text"])
        assert "example_echo" in data["tools_loaded"]


class TestExampleResource:
    """Tests for the example_resource (template://example/info)."""

    @pytest.mark.asyncio
    async def test_resources_list_contains_example(self, mcp_client):
        """resources/list should include template://example/info."""
        response = await mcp_client.send_request("resources/list")
        resources = response["result"]["resources"]
        uris = [r["uri"] for r in resources]
        assert "template://example/info" in uris

    @pytest.mark.asyncio
    async def test_read_example_resource(self, mcp_client):
        """Reading template://example/info should return valid JSON."""
        response = await mcp_client.send_request(
            "resources/read",
            {"uri": "template://example/info"},
        )
        assert "result" in response
        contents = response["result"]["contents"]
        assert len(contents) > 0
        data = json.loads(contents[0]["text"])
        assert data["chassis"] == "mcp-chassis-server"
        assert data["status"] == "running"


class TestExamplePrompt:
    """Tests for the example_greeting prompt."""

    @pytest.mark.asyncio
    async def test_prompts_list_contains_example(self, mcp_client):
        """prompts/list should include example_greeting."""
        response = await mcp_client.send_request("prompts/list")
        prompts = response["result"]["prompts"]
        names = [p["name"] for p in prompts]
        assert "example_greeting" in names

    @pytest.mark.asyncio
    async def test_get_example_greeting(self, mcp_client):
        """Getting example_greeting should return messages with the name."""
        response = await mcp_client.send_request(
            "prompts/get",
            {"name": "example_greeting", "arguments": {"name": "Alice"}},
        )
        assert "result" in response
        messages = response["result"]["messages"]
        assert len(messages) > 0
        assert messages[0]["role"] == "user"
        assert "Alice" in messages[0]["content"]["text"]
