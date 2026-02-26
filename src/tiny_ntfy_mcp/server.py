"""tiny-ntfy-mcp server entrypoint.

Implementation lives in :pymod:`ntfy_mcp.server` (tools are `ntfy_*`).
"""

from ntfy_mcp.server import run_stdio

__all__ = ["run_stdio"]
