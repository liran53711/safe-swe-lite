"""Search tools: search_pattern (ripgrep with regex fallback), list_files."""

import subprocess
import sys
from pathlib import Path

from safe_swe_lite.tools import ToolResult

SEARCH_TIMEOUT = 10


def search_pattern(workspace: Path, params: dict) -> ToolResult:
    pattern = params["pattern"]
    try:
        proc = subprocess.run(
            ["rg", "-n", pattern, str(workspace)],
            capture_output=True, text=True, errors="replace", timeout=SEARCH_TIMEOUT,
        )
        if proc.returncode == 2:  # rg exit code 2 = invalid regex
            return ToolResult(success=False, error=f"invalid regex pattern: {proc.stderr.strip()}")
        output = proc.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        try:
            output = _regex_fallback(workspace, pattern)
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, error=f"search timed out after {SEARCH_TIMEOUT}s")
    if not output.strip():
        return ToolResult(success=True, output="(no matches)")
    return ToolResult(success=True, output=output)


def _regex_fallback(workspace: Path, pattern: str) -> str:
    """Pure-Python regex search in a subprocess so pathological patterns cannot hang the loop."""
    code = (
        "import re, sys, pathlib\n"
        "sys.stdout.reconfigure(encoding='utf-8', errors='replace')\n"
        "ws = pathlib.Path(sys.argv[1]); pat = sys.argv[2]\n"
        "out = []\n"
        "for p in sorted(ws.rglob('*')):\n"
        "    if not p.is_file() or any(x.startswith('.') for x in p.parts): continue\n"
        "    try: text = p.read_text(encoding='utf-8', errors='replace')\n"
        "    except OSError: continue\n"
        "    for i, line in enumerate(text.splitlines(), 1):\n"
        "        if re.search(pat, line): out.append(f'{p.relative_to(ws)}:{i}:{line}')\n"
        "print('\\n'.join(out))\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code, str(workspace), pattern],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=SEARCH_TIMEOUT,
    )
    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        detail = stderr.splitlines()[-1] if stderr else "fallback search failed"
        if "re.error" in detail or "re.PatternError" in detail:
            detail = detail.replace("re.error: ", "").replace("re.PatternError: ", "")
            raise RuntimeError(f"invalid regex pattern: {detail}")
        raise RuntimeError(f"regex fallback failed: {detail}")
    return proc.stdout


def list_files(workspace: Path, params: dict) -> ToolResult:
    entries = []
    for path in sorted(workspace.rglob("*")):
        if any(part.startswith(".") for part in path.parts):
            continue
        rel = path.relative_to(workspace)
        entries.append(f"{'d' if path.is_dir() else 'f'} {rel}")
    return ToolResult(success=True, output="\n".join(entries) or "(empty)")
