"""Command tool: run_command with timeout."""

import subprocess

from safe_swe_lite.tools import ToolResult

DEFAULT_TIMEOUT = 30


def run_command(workspace, params: dict) -> ToolResult:
    timeout = int(params.get("timeout", DEFAULT_TIMEOUT))
    try:
        proc = subprocess.run(
            params["command"],
            shell=True,
            cwd=workspace,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return ToolResult(success=False, exit_code=-1, error=f"timeout after {timeout}s")
    output = (proc.stdout or "") + (proc.stderr or "")
    return ToolResult(success=proc.returncode == 0, output=output, exit_code=proc.returncode)
