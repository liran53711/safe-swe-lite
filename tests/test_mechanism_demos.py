import json
import shutil
from pathlib import Path

from safe_swe_lite.agent.loop import Agent
from safe_swe_lite.agent.protocol import Action
from safe_swe_lite.guardrails import GuardrailChain
from safe_swe_lite.llm.mock import MockLLM
from safe_swe_lite.tools import Dispatcher

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_demo_1_guardrail_blocks_dangerous_action(tmp_path):
    """课程演示①：MockLLM 输出 rm -rf /，护栏拦截，命令未执行。

    agent 每次尝试都被 L1 拦截；拦截不计步（见 test_blocked_actions_do_not_consume_steps），
    连续 5 次（max_blocked）后以 guardrail_exhausted 终止——max_steps_exceeded 在
    所有动作都被拦截时不可达，故重复输出危险命令直至护栏耗尽，断言终止状态。
    """
    chain = GuardrailChain(workspace=tmp_path)
    executed = []

    class Tools:
        def execute(self, action):
            executed.append(action)
            return {"output": "ran", "exit_code": 0}

    model = MockLLM(outputs=[
        {"message": '{"action": "run_command", "parameters": {"command": "rm -rf /"}}'},
    ] * 10)
    agent = Agent(model=model, tools=Tools(), guardrail=chain, max_steps=5)
    result = agent.run("delete everything")
    assert result["exit_status"] == "guardrail_exhausted"
    assert executed == []  # 命令从未执行
    # trace 里记录了护栏拦截（课程自查项 4）：前 4 次拦截各有记录，
    # 第 5 次触发 guardrail_exhausted 直接返回，不再追加 trace 条目
    guardrail_entries = [t for t in result["trace"] if t.get("kind") == "guardrail"]
    assert len(guardrail_entries) == 4
    assert all(t["data"]["blocked"] for t in guardrail_entries)


def test_demo_2_feedback_loop_changes_next_action(tmp_path):
    """课程演示②：注入一次失败，agent 收到观察结果后进入下一步修改。

    边界说明：本演示验证的是观察通道（observation channel）——失败结果
    被记录并回灌，agent 据此执行下一步动作。动作序列由 mock 脚本编排
    （确定性要求），失败信息是手写替身而非真实 validators 输出；真实的
    validators 反馈闭环在 fix_bug demo（demo 4）中以真实 pytest 验证。
    """
    calls = []

    class FailingTools:
        def execute(self, action):
            calls.append(action)
            if action.name == "run_command":
                return {"output": "tests failed: AssertionError", "exit_code": 1}
            return {"output": "ok", "exit_code": 0}

    model = MockLLM(outputs=[
        {"message": '{"action": "run_command", "parameters": {"command": "pytest -q"}}'},
        {"message": '{"action": "edit_file", "parameters": {"path": "a.py", "old_string": "x", "new_string": "y"}}'},
        {"message": '{"action": "submit", "parameters": {"result": "fixed"}}'},
    ])
    agent = Agent(model=model, tools=FailingTools(), max_steps=10)
    result = agent.run("fix failing test")
    assert result["exit_status"] == "submitted"
    # 第 2 步必须是修改动作——收到失败反馈后改变了行为
    assert calls[1].name == "edit_file"


def test_demo_3_layered_guardrail_chain(tmp_path):
    """课程演示③（重点维度）：护栏四层完整链路。"""
    chain = GuardrailChain(workspace=tmp_path, banned_symbols=["eval"])
    # L1: 静态黑名单
    d1 = chain.check(Action(name="run_command", parameters={"command": "sudo rm -rf /"}))
    assert d1.blocked and d1.layer == 1
    # L2: 范围围栏
    d2 = chain.check(Action(name="read_file", parameters={"path": "/etc/passwd"}))
    assert d2.blocked and d2.layer == 2
    # L3: HITL 状态机（mock 自动批准放行）
    d3 = chain.check(Action(name="run_command", parameters={"command": "git push origin main"}), auto_approve=True)
    assert not d3.blocked and d3.hitl_state == "approved"
    # L4: 代码内容扫描
    d4 = chain.check(Action(name="write_file", parameters={"path": "x.py", "content": "eval('1')\n"}))
    assert d4.blocked and d4.layer == 4


def test_demo_fix_bug_task_file_runs(tmp_path):
    """任务文件驱动的完整 mock 运行（供 CLI 与 WebUI 复用）。

    边界：mock 脚本只编排动作序列（信任边界），但工具结果是真实的——
    pytest 真实失败、edit_file 真实改文件、二次 pytest 真实转绿。
    """
    sample = REPO_ROOT / "examples" / "sample_project"
    shutil.copytree(sample, tmp_path / "sample_project")
    workspace = tmp_path / "sample_project"
    task = json.loads((REPO_ROOT / "examples/tasks/fix_bug.json").read_text(encoding="utf-8"))
    task["workspace"] = str(workspace)
    model = MockLLM(outputs=task["mock_outputs"])
    tools = Dispatcher(workspace=workspace)
    agent = Agent(model=model, tools=tools, max_steps=task["max_steps"])
    result = agent.run(task["task"])
    assert result["exit_status"] == "submitted"
    # 真实验证：编辑发生过 + 文件被真实修复
    assert (workspace / "src" / "auth.py").read_text(encoding="utf-8").startswith(
        "def authenticate(username: str, password: str) -> bool:\n"
        "    if not username:\n"
        "        return False"
    )
    # trace 里有真实的失败与转绿信号
    trace_text = str(result.get("trace", []))
    assert "1 failed" in trace_text or "FAILED" in trace_text
    assert "3 passed" in trace_text
