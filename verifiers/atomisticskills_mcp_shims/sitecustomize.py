"""Runtime shims for AtomisticSkills MCP server compatibility."""

from __future__ import annotations

import os


def _disable_fastmcp_json_preparse() -> None:
    try:
        from mcp.server.fastmcp.utilities.func_metadata import FuncMetadata
    except Exception:
        return

    def _identity_pre_parse_json(self: FuncMetadata, data: dict) -> dict:
        return data.copy()

    FuncMetadata.pre_parse_json = _identity_pre_parse_json


if os.environ.get("ATOMISTICSKILLS_MCP_DISABLE_JSON_PREPARSE") == "1":
    _disable_fastmcp_json_preparse()
