"""Tool system: 7 structured tools + dispatcher."""

from dataclasses import dataclass

from safe_swe_lite.agent.protocol import Action


@dataclass
class ToolResult:
    success: bool
    output: str = ""
    exit_code: int = 0
    error: str = ""

    def __str__(self) -> str:
        if self.success:
            return self.output or "ok"
        return f"error: {self.error or 'failed'} (exit_code={self.exit_code})"


MAX_OUTPUT_CHARS = 32_000


def _truncate_result(result: ToolResult) -> ToolResult:
    for field_name in ("output", "error"):
        value = getattr(result, field_name)
        if len(value) > MAX_OUTPUT_CHARS:
            setattr(result, field_name, value[:MAX_OUTPUT_CHARS] + f"\n... truncated ({len(value)} chars total)")
    return result


class Dispatcher:
    def __init__(self, workspace):
        from safe_swe_lite.tools import command_tools, file_tools, search_tools, submit_tool
        self.workspace = workspace
        self._handlers = {
            "read_file": file_tools.read_file,
            "write_file": file_tools.write_file,
            "edit_file": file_tools.edit_file,
            "run_command": command_tools.run_command,
            "search_pattern": search_tools.search_pattern,
            "list_files": search_tools.list_files,
            "submit": submit_tool.submit,
        }

    def execute(self, action: Action) -> ToolResult:
        handler = self._handlers.get(action.name)
        if handler is None:
            return ToolResult(success=False, error=f"unknown tool '{action.name}'")
        try:
            result = handler(self.workspace, action.parameters)
        except Exception as e:  # tool errors become observations, never crash the loop
            return ToolResult(success=False, error=f"{type(e).__name__}: {e}")
        return _truncate_result(result)
