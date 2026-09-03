"""Re-export. Canonical implementation: mcp-servers/src/granite_mcp/ast_analyzer.py"""

from granite_mcp.ast_analyzer import analyze_python_source, extract_function, validate_python_source

__all__ = ["analyze_python_source", "extract_function", "validate_python_source"]
