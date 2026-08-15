import pytest

from safe_swe_lite.feedback.loop import run_with_retry
from safe_swe_lite.feedback.validators import (
    PyCompileValidator,
    TestValidator,
    format_for_llm,
)


@pytest.fixture
def tmp_project(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "pyproject.toml").write_text("[project]\nname='sample'\n")
    return tmp_path


def test_compile_validator_passes_clean_file(tmp_project):
    (tmp_project / "src" / "ok.py").write_text("x = 1\n")
    results = PyCompileValidator().run(tmp_project)
    assert results == []  # 无错误


def test_compile_validator_detects_syntax_error(tmp_project):
    bad = tmp_project / "src" / "bad.py"
    bad.write_text("def f(:\n    pass\n")
    results = PyCompileValidator().run(tmp_project)
    assert len(results) == 1
    assert results[0].validator == "compile"
    assert results[0].passed is False
    assert results[0].line is not None


def test_test_validator_catches_failing_test(tmp_project):
    (tmp_project / "tests" / "test_x.py").write_text(
        "def test_truth():\n    assert 1 == 2\n")
    results = TestValidator().run(tmp_project)
    assert any(not r.passed and r.validator == "test" for r in results)


def test_test_validator_passes_when_tests_green(tmp_project):
    (tmp_project / "tests" / "test_x.py").write_text(
        "def test_truth():\n    assert 1 == 1\n")
    results = TestValidator().run(tmp_project)
    assert all(r.passed for r in results)


def test_format_for_llm_has_actionable_structure(tmp_project):
    bad = tmp_project / "src" / "bad.py"
    bad.write_text("def f(:\n    pass\n")
    results = PyCompileValidator().run(tmp_project)
    text = format_for_llm(results)
    assert "Fix all errors" in text
    assert "bad.py" in text
    assert "line" in text


def _failing_workspace(tmp_path):
    (tmp_path / "bad.py").write_text("def f(:\n    pass\n")
    return tmp_path


def test_retry_returns_immediately_when_all_pass(tmp_path):
    (tmp_path / "ok.py").write_text("x = 1\n")
    calls = []
    run_with_retry(lambda msg: calls.append(msg), tmp_path)
    assert calls == []  # execute_write 从未调用


def test_retry_calls_execute_write_exactly_three_times_when_always_failing(tmp_path):
    _failing_workspace(tmp_path)
    calls = []
    results = run_with_retry(lambda msg: calls.append(msg), tmp_path)
    assert len(calls) == 3
    assert results  # 返回最后验证结果


def test_retry_stops_when_execute_write_raises(tmp_path):
    _failing_workspace(tmp_path)
    calls = []
    def boom(msg):
        calls.append(msg)
        raise IndexError("mock outputs exhausted")
    results = run_with_retry(boom, tmp_path)
    assert len(calls) == 1  # 第一次就崩，不再重试
    assert any(r.validator == "loop" and "IndexError" in r.message for r in results)


def test_retry_recovers_after_first_fix(tmp_path):
    (tmp_path / "bad.py").write_text("def f(:\n    pass\n")
    calls = []
    def fix(msg):
        calls.append(msg)
        (tmp_path / "bad.py").write_text("x = 1\n")  # 修复语法错误
    results = run_with_retry(fix, tmp_path)
    assert len(calls) == 1  # 第一次修复后全过，不再重试
    assert all(r.passed for r in results if r.validator != "loop")
