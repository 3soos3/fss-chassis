"""FSS MCP — FSS-compliant MCP server chassis."""

from importlib.metadata import PackageNotFoundError, version
try:
    __version__ = version("fss-mcp")
except PackageNotFoundError:
    __version__ = "unknown"
