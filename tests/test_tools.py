from pathlib import Path

import pytest

from safe_swe_lite.agent.protocol import Action
from safe_swe_lite.tools import Dispatcher


@pytest.fixture
def dispatcher(tmp_path: Path):
    return Dispatcher(workspace=tmp_path)


def test_read_file_roundtrip(dispatcher, tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
    result = dispatcher.execute(Action(name="read_file", parameters={"path": "a.py"}))
    assert result.success and "x = 1" in result.output


def test_write_file_roundtrip(dispatcher, tmp_path):
    dispatcher.execute(Action(name="write_file", parameters={"path": "b.py", "content": "y = 2\n"}))
    result = dispatcher.execute(Action(name="read_file", parameters={"path": "b.py"}))
    assert "y = 2" in result.output


def test_edit_file_replaces_unique_string(dispatcher, tmp_path):
    (tmp_path / "c.py").write_text("hello world\n")
    result = dispatcher.execute(Action(name="edit_file", parameters={
        "path": "c.py", "old_string": "hello", "new_string": "goodbye"}))
    assert result.success
    assert "goodbye world" in (tmp_path / "c.py").read_text()


def test_edit_file_non_unique_old_string_fails(dispatcher, tmp_path):
    (tmp_path / "c.py").write_text("hello hello\n")
    result = dispatcher.execute(Action(name="edit_file", parameters={
        "path": "c.py", "old_string": "hello", "new_string": "x"}))
    assert not result.success and "unique" in result.error


def test_run_command_captures_output(dispatcher, tmp_path):
    result = dispatcher.execute(Action(name="run_command", parameters={"command": "echo hi"}))
    assert result.success and "hi" in result.output
    assert result.exit_code == 0


def test_run_command_nonzero_exit(dispatcher, tmp_path):
    # double quotes: stripped by both cmd.exe (Windows) and POSIX sh
    result = dispatcher.execute(Action(name="run_command", parameters={"command": 'python -c "import sys; sys.exit(3)"'}))
    assert not result.success and result.exit_code == 3


def test_search_pattern_finds_matches(dispatcher, tmp_path):
    (tmp_path / "auth.py").write_text("def login():\n    pass\n")
    result = dispatcher.execute(Action(name="search_pattern", parameters={"pattern": "login"}))
    assert result.success and "auth.py" in result.output


def test_list_files_lists_tree(dispatcher, tmp_path):
    (tmp_path / "x.py").write_text("")
    result = dispatcher.execute(Action(name="list_files", parameters={}))
    assert "x.py" in result.output


def test_unknown_tool_returns_error(dispatcher):
    result = dispatcher.execute(Action(name="nope", parameters={}))
    assert not result.success and "unknown tool" in result.error


def test_submit_returns_result(dispatcher):
    result = dispatcher.execute(Action(name="submit", parameters={"result": "fixed"}))
    assert result.success and result.output == "fixed"


def test_read_file_negative_offset_clamped(dispatcher, tmp_path):
    (tmp_path / "n.py").write_text("a\nb\nc\n")
    result = dispatcher.execute(Action(name="read_file", parameters={"path": "n.py", "offset": -2}))
    assert result.success and "a\nb\nc" in result.output  # clamp 到 0，全文返回


def test_write_file_creates_nested_dirs(dispatcher, tmp_path):
    result = dispatcher.execute(Action(name="write_file", parameters={
        "path": "pkg/sub/mod.py", "content": "x = 1\n"}))
    assert result.success and (tmp_path / "pkg" / "sub" / "mod.py").exists()


def test_search_invalid_regex_returns_error(dispatcher, tmp_path):
    (tmp_path / "z.py").write_text("hello\n")
    result = dispatcher.execute(Action(name="search_pattern", parameters={"pattern": "("}))
    assert not result.success and "invalid" in result.error


def test_output_truncated_when_too_long(dispatcher, tmp_path):
    (tmp_path / "big.py").write_text("x = 1\n" * 3000)  # ~18KB < 32KB 上限，不改动
    (tmp_path / "big2.py").write_text("y = 2\n" * 20000)  # ~120KB > 32KB
    result = dispatcher.execute(Action(name="read_file", parameters={"path": "big2.py"}))
    assert "truncated" in result.output
