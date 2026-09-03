"""Re-export. Canonical implementation: mcp-servers/src/granite_mcp/argocd_tool.py"""

from granite_mcp.argocd_tool import argocd_get_app, argocd_sync_app

__all__ = ["argocd_get_app", "argocd_sync_app"]
