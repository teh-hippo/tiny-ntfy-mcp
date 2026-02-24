"""Primary package name for tiny-ntfy-mcp.

Implementation lives in :pymod:`ntfy_mcp`; this package exists to satisfy
packaging expectations and to provide a stable module name matching the
distribution name.
"""

from ntfy_mcp import __version__

__all__ = ["__version__"]
