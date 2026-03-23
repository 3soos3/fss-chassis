"""Example prompt extension — greeting prompt.

Copy this file as a starting point for your own prompts.
See FORK_GUIDE.md for detailed instructions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_chassis.context import HandlerContext
    from mcp_chassis.server import ChassisServer

_ARGUMENTS = [
    {"name": "name", "description": "Name of the person to greet.", "required": True},
]


def register(server: ChassisServer) -> None:
    """Register the example_greeting prompt."""

    async def _handle(
        arguments: dict[str, Any], context: HandlerContext
    ) -> list[dict[str, str]]:
        """Generate a greeting prompt.

        Args:
            arguments: Must contain ``name``.
            context: Handler context.

        Returns:
            List of message dicts.
        """
        await context.log_debug("example_greeting called")
        name = arguments.get("name", "World")
        return [
            {
                "role": "user",
                "content": f"Please greet {name} warmly and ask how they are doing.",
            }
        ]

    server.register_prompt(
        name="example_greeting",
        handler=_handle,
        description="Generate a friendly greeting for someone.",
        arguments=_ARGUMENTS,
    )
