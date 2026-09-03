"""Re-export. Canonical implementation: mcp-servers/src/granite_mcp/target_ocp_checker.py"""

from granite_mcp.target_ocp_checker import ocp_deployment_status, ocp_list_pods

__all__ = ["ocp_deployment_status", "ocp_list_pods"]
