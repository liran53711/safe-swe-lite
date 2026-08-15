"""File tools: read_file, write_file, edit_file."""

from pathlib import Path

from safe_swe_lite.tools import ToolResult


def read_file(workspace: Path, params: dict) -> ToolResult:
    path = (workspace / params["path"]).resolve()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ToolResult(success=False, error=f"file not found: {params['path']}")
    lines = text.splitlines()
    offset = max(0, int(params.get("offset", 0)))
    limit = max(0, int(params.get("limit", len(lines))))
    shown = lines[offset:offset + limit]
    return ToolResult(success=True, output="\n".join(shown))


def write_file(workspace: Path, params: dict) -> ToolResult:
    path = (workspace / params["path"]).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(params["content"], encoding="utf-8")
    return ToolResult(success=True, output=f"wrote {params['path']} ({len(params['content'])} chars)")


def edit_file(workspace: Path, params: dict) -> ToolResult:
    path = (workspace / params["path"]).resolve()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ToolResult(success=False, error=f"file not found: {params['path']}")
    old = params["old_string"]
    new = params["new_string"]
    count = text.count(old)
    if count == 0:
        return ToolResult(success=False, error="old_string not found")
    if count > 1:
        return ToolResult(success=False, error=f"old_string not unique ({count} matches)")
    path.write_text(text.replace(old, new), encoding="utf-8")
    return ToolResult(success=True, output=f"edited {params['path']}")
