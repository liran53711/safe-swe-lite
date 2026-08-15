"""Submit tool: the structured stop signal."""

from safe_swe_lite.tools import ToolResult


def submit(workspace, params: dict) -> ToolResult:
    return ToolResult(success=True, output=str(params.get("result", "")))
