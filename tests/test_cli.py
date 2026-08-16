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


def test_agent_on_step_callback_receives_steps(tmp_path):
    from safe_swe_lite.agent.loop import Agent
    from safe_swe_lite.llm.mock import MockLLM
    from safe_swe_lite.tools import Dispatcher

    steps = []
    model = MockLLM(outputs=[
        {"message": '{"action": "list_files", "parameters": {}}'},
        {"message": '{"action": "submit", "parameters": {"result": "done"}}'},
    ])
    agent = Agent(model=model, tools=Dispatcher(workspace=tmp_path), max_steps=5)
    result = agent.run("task", on_step=lambda action, result, decision: steps.append((action.name, decision)))
    assert result["exit_status"] == "submitted"
    assert [s[0] for s in steps] == ["list_files"]  # submit 不触发 on_step（循环在 submit 分支直接返回）
    assert steps[0][1] is None  # 无护栏拦截时 decision 为 None


def test_agent_on_step_callback_receives_guardrail_block(tmp_path):
    from safe_swe_lite.agent.loop import Agent
    from safe_swe_lite.guardrails import GuardrailChain
    from safe_swe_lite.llm.mock import MockLLM
    from safe_swe_lite.tools import Dispatcher

    steps = []
    model = MockLLM(outputs=[
        {"message": '{"action": "run_command", "parameters": {"command": "rm -rf /"}}'},
        {"message": '{"action": "submit", "parameters": {"result": "gave up"}}'},
    ])
    chain = GuardrailChain(workspace=tmp_path)
    agent = Agent(model=model, tools=Dispatcher(workspace=tmp_path), guardrail=chain, max_steps=5)
    agent.run("task", on_step=lambda a, r, d: steps.append(d))
    assert any(d is not None and d.blocked for d in steps)  # 拦截被回调到


def test_chat_command_exits_on_quit(monkeypatch, tmp_path, capsys):
    from safe_swe_lite.cli import chat_command

    inputs = iter(["exit"])
    monkeypatch.setattr("builtins.input", lambda *a: next(inputs))
    chat_command(workspace=tmp_path, use_mock=True)
    captured = capsys.readouterr()
    # 正常退出无异常即通过；mock 模式横幅走 stderr（与 run 子命令同一决策）
    assert "mock" in captured.err.lower()
