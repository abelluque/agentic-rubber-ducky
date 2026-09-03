Canonical tool implementations live in `mcp-servers/src/granite_mcp/`.

Llama Stack registers them as MCP toolgroups (`mcp::ast`, `mcp::github`, `mcp::argocd`, `mcp::ocp`) using [`../config.yaml`](../config.yaml). The orchestrator calls the same processes over REST `POST /invoke`.
