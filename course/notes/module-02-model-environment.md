# 第 2 节笔记：模型抽象与环境

> 教材：mini-swe-agent `models/test_models.py`、`models/litellm_model.py`、`environments/local.py`

## 直觉

Model 类和 Environment 类是 Agent 的两只手——一只手（Model）跟外部大模型对话，另一只手（Environment）在本地执行操作。Agent 不关心左手是真人还是录音机，也不关心右手是 Docker 还是本机 shell。只要接口一样，换什么都能用。

## Model 协议

```python
class Model(Protocol):
    def query(self, messages: list[dict]) -> dict: ...
    def format_message(self, **kwargs) -> dict: ...
    def format_observation_messages(self, message, outputs, ...) -> list[dict]: ...
```

| 方法 | 谁调用 | 做什么 |
|---|---|---|
| `query(messages)` | Agent | 让 LLM 决策下一步，返回带 `extra.actions` 的消息 |
| `format_message(**kwargs)` | Agent | 把 role + content 包装成统一格式的消息 |
| `format_observation_messages(...)` | Agent | 把执行结果包装成 observation 消息回灌 |

## DeterministicModel：预录播放

```python
class DeterministicModel:
    def __init__(self, **kwargs):
        self.current_index = -1

    def query(self, messages, **kwargs) -> dict:
        self.current_index += 1                           # 每次 +1
        output = self.config.outputs[self.current_index]  # 按序取一条
        return output
```

核心机制：**预编程列表 + 顺序播放**。`query()` 不看传入的 `messages` 是什么，直接播放下一条预定义的回复。

这就是课程 `§A.4(C)` 的底层原理——测试用 `DeterministicModel` 替代真 LLM，每个测试用例预定义一组 actions，确定性地验证 harness 行为。

### make_output 辅助函数

```python
def make_output(content: str, actions: list[dict], cost: float = 1.0) -> dict:
    return {
        "role": "assistant",
        "content": content,
        "extra": {"actions": actions, "cost": cost, "timestamp": time.time()},
    }
```

一行创建一个完整的"LLM 回复"。测试用例的精简写法。

## LitellmModel：真实 LLM 适配器

`LitellmModel` 和 `DeterministicModel` 的 `query()` 接口完全相同。区别在于内部的 action 来源：

| 模型 | action 来源 |
|---|---|
| `DeterministicModel` | 初始化时硬编码的 `outputs` 列表 |
| `LitellmModel` | LLM 返回的 `tool_calls` → `_parse_actions()` 解析 |

### 关键的 _parse_actions

```python
def _parse_actions(self, response) -> list[dict]:
    tool_calls = response.choices[0].message.tool_calls or []
    return parse_toolcall_actions(tool_calls, ...)
```

LLM 返回 JSON 格式的函数调用 → 翻译成 harness 内部的统一动作列表。如果 LLM 调用了未注册的工具名，抛 `FormatError`——agent loop 里的重试机制因此被触发。

### retry 机制

```python
def query(self, messages, **kwargs) -> dict:
    for attempt in retry(logger=logger, abort_exceptions=self.abort_exceptions):
        with attempt:
            response = self._query(...)
```

`litellm_model.py` 有重试，`test_models.py` 没有。测试用模型如果也重试，反而会掩盖 harness 本身的错误处理逻辑。

## Environment 协议

```python
class Environment(Protocol):
    def execute(self, action: dict, cwd: str = "") -> dict: ...
```

## LocalEnvironment：subprocess 包装

```python
def execute(self, action: dict, cwd: str = "") -> dict:
    command = action.get("command", "")
    result = _run(command, cwd, env, timeout)
    return {"output": result.stdout, "returncode": result.returncode}
```

三个关键设计：

### 1. 超时保护

```python
except subprocess.TimeoutExpired:
    os.killpg(process.pid, signal.SIGKILL)   # 杀整个进程组
```

`wall_time_limit`（Agent层）限制整个 session，`timeout`（Environment层）限制单个命令。两层保护。

### 2. 结构化返回值

不管成功还是失败，都返回 `{"output": ..., "returncode": ..., "exception_info": ...}`。不做字符串拼接，保证 observation 可解析。

### 3. 特殊的停机方式

```python
def _check_finished(self, output):
    if output starts with "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT":
        raise Submitted({"role": "exit", ...})
```

LLM 不是调 `submit` 工具，而是输出一个特殊命名的 shell 命令。environment 检测到后抛异常 → agent loop 捕获 → 加入 exit 消息 → break。简陋但有效，SafeSWE-Lite 会用 `submit` 动作替代。

## 架构图

```
┌──────────────────────────────────────────────┐
│  Agent                                       │
│                                              │
│  调用: self.model.query(messages)            │
│  调用: self.env.execute(action)              │
│                                              │
│         ↑ 统一的接口（Protocol）               │
│    ┌────┴────┬──────────┬──────────┐         │
│    │         │          │          │         │
│  MockModel  Litellm    OpenAI    Claude      │
│  (预录播放) (litellm)  (SDK)     (SDK)       │
│                                              │
│  LocalEnv    DockerEnv   ...                 │
│  (subprocess)(docker)                        │
└──────────────────────────────────────────────┘
```

## 映射 SafeSWE-Lite

| mini-swe-agent | SafeSWE-Lite |
|---|---|
| 1 个工具 `BASH_TOOL` | 7 个结构化工具（read/write/edit/run/search/list/submit） |
| `DeterministicModel` | `MockLLM(outputs=[...])` 同机制 |
| `LitellmModel` | `LiteLLMProvider` 或 `OpenAICompatibleProvider` |
| `LocalEnvironment` | `LocalWorkspace`（加文件系统范围限制 + 护栏拦截） |
| `Submitted` 异常 | `submit` 动作，干净停机 |
| 单一超时 | 保留两层超时（session + 单命令） |
