"""Bounded retry loop: validate -> feed back -> retry, max 3 rounds."""

from safe_swe_lite.feedback.validators import (
    PyCompileValidator,
    TestValidator,
    ValidationResult,
    format_for_llm,
)


def run_with_retry(execute_write, workspace, max_retries: int = 3) -> list[ValidationResult]:
    """After a write action, validate; on failure feed errors back to the model.

    execute_write(correction_instruction: str) -> None re-invokes the model
    with the error feedback and applies its next edit. Returns the final
    validation results (possibly still failing after max_retries).
    execute_write 抛异常时停止重试并返回最后验证结果附错误标记——模型侧失败
    （输出耗尽/网络错误）不应伪装成验证失败。
    """
    results = _validate(workspace)
    for _ in range(max_retries):
        failed = [r for r in results if not r.passed]
        if not failed:
            return results
        try:
            execute_write(format_for_llm(failed))
        except Exception as e:  # noqa: BLE001 - 模型侧失败：不再重试，返回最后验证状态
            results = _validate(workspace)
            results.append(ValidationResult(
                passed=False, validator="loop",
                message=f"correction attempt failed: {type(e).__name__}: {e}",
            ))
            return results
        results = _validate(workspace)
    return results


def _validate(workspace):
    results = PyCompileValidator().run(workspace)
    results += TestValidator().run(workspace)
    return results
