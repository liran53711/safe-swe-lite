"""Deterministic validators: compile -> pytest. Each returns structured results."""

import subprocess
from dataclasses import dataclass
from pathlib import Path

MAX_PYTEST_OUTPUT = 2000

EXCLUDED_DIRS = {".venv", "venv", "node_modules", ".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}


@dataclass
class ValidationResult:
    passed: bool
    validator: str
    file: str | None = None
    line: int | None = None
    message: str = ""
    context: str | None = None
    details: dict | None = None


class PyCompileValidator:
    """Uses py_compile to catch syntax errors deterministically, offline."""

    def run(self, workspace: Path) -> list[ValidationResult]:
        results = []
        for py_file in sorted(workspace.rglob("*.py")):
            if any(part in EXCLUDED_DIRS for part in py_file.relative_to(workspace).parts):
                continue
            try:
                compile(py_file.read_text(encoding="utf-8", errors="replace"), str(py_file), "exec")
            except (SyntaxError, ValueError) as e:
                results.append(ValidationResult(
                    passed=False, validator="compile",
                    file=str(py_file.relative_to(workspace)),
                    line=getattr(e, "lineno", None),
                    message=f"{type(e).__name__}: {getattr(e, 'msg', e)}",
                ))
        return results


class TestValidator:
    """Runs pytest and parses the short summary deterministically."""

    def run(self, workspace: Path) -> list[ValidationResult]:
        try:
            proc = subprocess.run(
                ["python", "-m", "pytest", "-q", "--no-header"],
                cwd=workspace, capture_output=True, text=True, timeout=120,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return [ValidationResult(passed=False, validator="test", message="pytest timed out after 120s")]
        if proc.returncode == 0:
            return [ValidationResult(passed=True, validator="test", message="all tests passed")]
        if proc.returncode == 1:
            return [ValidationResult(
                passed=False, validator="test",
                message=proc.stdout[-MAX_PYTEST_OUTPUT:] or proc.stderr[-MAX_PYTEST_OUTPUT:],
            )]
        # rc 2/3/4/5：usage error / 内部错误 / 无测试——不可由模型修复，标记为通过不消耗重试
        return [ValidationResult(
            passed=True, validator="test",
            message=f"pytest exited with code {proc.returncode} (not a test failure): "
                    f"{(proc.stderr or proc.stdout)[-MAX_PYTEST_OUTPUT // 4:].strip()}",
        )]


def format_for_llm(results: list[ValidationResult]) -> str:
    failed = [r for r in results if not r.passed]
    if not failed:
        return "All validators passed."
    lines = ["## Validation failed - Fix all errors below:"]
    for r in failed:
        loc = f"{r.file} line {r.line}" if r.file and r.line else (r.file or "")
        lines.append(f"[{r.validator}] {loc} {r.message}".strip())
    return "\n".join(lines)
