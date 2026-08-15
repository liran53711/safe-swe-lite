import json
from pathlib import Path

from safe_swe_lite.cli import run_task_from_file

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_run_fix_bug_task_with_mock(tmp_path):
    task_file = tmp_path / "task.json"
    task_file.write_text(json.dumps({
        "task": "fix the failing test",
        "workspace": str(tmp_path),
        "max_steps": 5,
        "mock_outputs": [
            {"message": '{"action": "submit", "parameters": {"result": "done"}}'},
        ],
    }))
    result = run_task_from_file(task_file)
    assert result["exit_status"] == "submitted"
    assert result["submission"] == "done"


def test_run_task_with_guardrail_blocks_rm(tmp_path):
    task_file = tmp_path / "task.json"
    task_file.write_text(json.dumps({
        "task": "delete everything",
        "workspace": str(tmp_path),
        "max_steps": 5,
        "mock_outputs": [
            {"message": '{"action": "run_command", "parameters": {"command": "rm -rf /"}}'},
            {"message": '{"action": "submit", "parameters": {"result": "gave up"}}'},
        ],
    }))
    result = run_task_from_file(task_file)
    # 护栏拦截 rm -rf /（不执行），agent 继续到 submit
    assert result["exit_status"] == "submitted"
    assert any(t.get("kind") == "guardrail" for t in result.get("trace", []))


def test_run_task_result_json_serializable(tmp_path):
    task_file = tmp_path / "task.json"
    task_file.write_text(json.dumps({
        "task": "simple",
        "workspace": str(tmp_path),
        "mock_outputs": [
            {"message": '{"action": "list_files", "parameters": {}}'},
            {"message": '{"action": "submit", "parameters": {"result": "ok"}}'},
        ],
    }))
    result = run_task_from_file(task_file)
    # trace 里有 ToolResult 对象，必须可 JSON 序列化（CLI 输出的前提）
    json.dumps(result)  # 无兜底，_jsonable 回归时测试必红


def test_missing_mock_outputs_returns_friendly_error(tmp_path):
    task_file = tmp_path / "task.json"
    task_file.write_text(json.dumps({"task": "do something", "workspace": str(tmp_path)}))
    result = run_task_from_file(task_file)
    assert result["exit_status"] == "mock_outputs_exhausted"
    assert "exhausted" in result["error"]


def test_missing_task_key_raises(tmp_path):
    task_file = tmp_path / "task.json"
    task_file.write_text(json.dumps({"workspace": str(tmp_path)}))
    try:
        run_task_from_file(task_file)
        assert False, "should raise"
    except ValueError as e:
        assert "task" in str(e)
