"""Example resource extension — server info.

Copy this file as a starting point for your own resources.
See FORK_GUIDE.md for detailed instructions.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_chassis.context import HandlerContext
    from mcp_chassis.server import ChassisServer


def register(server: ChassisServer) -> None:
    """Register the example info resource."""

    async def _handle(uri: str, context: HandlerContext) -> str:
        """Return basic server info as JSON.

        Args:
            uri: The resource URI.
            context: Handler context.

        Returns:
            JSON string with server info.
        """
        await context.log_debug("example info resource read")
        data = {
            "chassis": server._config.server.name,
            "version": server._config.server.version,
            "status": "running",
        }
        return json.dumps(data)

    server.register_resource(
        uri="template://example/info",
        handler=_handle,
        name="Server Info",
        description="Basic server information (name, version, status).",
        mime_type="application/json",
    )
