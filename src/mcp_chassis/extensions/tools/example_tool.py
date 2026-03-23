"""Example tool extension — echo back a message.

Copy this file as a starting point for your own tools.
See FORK_GUIDE.md for detailed instructions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_chassis.context import HandlerContext
    from mcp_chassis.server import ChassisServer


def register(server: ChassisServer) -> None:
    """Register the example_echo tool."""

    async def _handle(
        arguments: dict[str, Any], context: HandlerContext
    ) -> str:
        """Echo back the provided message.

        Args:
            arguments: Must contain ``message``.
            context: Handler context for logging.

        Returns:
            The message string.
        """
        await context.log_debug("example_echo called")
        return arguments["message"]

    server.register_tool(
        name="example_echo",
        description="Echo back the provided message. This is an example tool.",
        input_schema={
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message to echo back.",
                },
            },
            "required": ["message"],
        },
        handler=_handle,
    )
