# 第 1 节笔记：Agent 主循环

> 教材：mini-swe-agent `agents/default.py`
> 核心文件 189 行，本节课覆盖全文。

## 直觉

agent 循环就像一个自动答录机转接系统——每次 LLM 说出"我要做X"，系统执行 X 并把结果告诉 LLM，来回往复直到 LLM 说"做完了"。LLM 只管决策，执行全由你的代码完成。

## 三层协议（`__init__.py`）

| 协议 | 方法 | 职责 |
|---|---|---|
| `Model` | `query(messages) → dict` | 接收消息列表，返回一个带 `role` + `extra` 的消息 |
| `Environment` | `execute(action) → dict` | 执行动作（读写文件、跑命令），返回结构化输出 |
| `Agent` | `run(task) → dict` | 驱动主循环，返回 `{"exit_status": ..., "submission": ...}` |

## 核心流程

```
run(task)
  │
  ├─ 1. 清空 self.messages
  ├─ 2. 加 system + user 消息（模板渲染 + Jinja2）
  │
  └─ while True:
       ├─ step()
       │    ├─ query()           ─→ self.messages 追加 assistant 消息
       │    └─ execute_actions() ─→ self.messages 追加 observation 消息
       │
       ├─ 异常处理
       │    ├─ FormatError      → 重试（有限次）
       │    ├─ InterruptAgentFlow → 异常里携带的 exit 消息加入 messages
       │    └─ Exception         → 记录 + 保存轨迹 + 重新抛出
       │
       ├─ self.save(trajectory)   ← 每轮结束都存一次轨迹
       └─ if last_message.role == "exit": break
```

## 关键设计决策

### 1. 共享的消息列表

`self.messages` 是 agent 唯一的共享状态。`query()` 追加 assistant 消息，`execute_actions()` 追加 observation 消息。下一轮 LLM 调用直接传整个列表。不需要单独的反馈管道。

### 2. 异常驱动的停机

三种停机路径完全统一：

| 停机原因 | 实现方式 | 最后一条消息 |
|---|---|---|
| LLM 主动 submit | `InterruptAgentFlow` 异常 | `role="exit", exit_status="submitted"` |
| 步数/花费超限 | `LimitsExceeded` 异常 | `role="exit", exit_status="LimitsExceeded"` |
| 超时 | `TimeExceeded` 异常 | `role="exit", exit_status="TimeExceeded"` |

异常不是用来报错的——异常里携带的是完整消息体。回到循环后统一走 `self.messages[-1].get("role") == "exit"`。

### 3. 结构化停机判断

停机的判断不是匹配字符串 "done"，而是检查 `role == "exit"`。字符串匹配是脆的（LLM 可能说 "I'm almost done"），结构化的字段检查是可靠的。

### 4. step() = query() + execute_actions()

```python
def step(self) -> list[dict]:
    return self.execute_actions(self.query())
```

单步 = 一次 LLM 问答 + 一次动作执行。两件事压缩在一行，强制每个 step 都有一个操作被实际执行。

## 映射 SafeSWE-Lite

| mini-swe-agent | SafeSWE-Lite |
|---|---|
| `while True` + `break` | 同结构，但增加 HITL 暂停点 |
| `role == "exit"` 判定停机 | 改用 `action.name == "submit"` 判定停机 |
| `LimitsExceeded` / `TimeExceeded` | 保留步数上限和时间上限 |
| 所有消息在 `self.messages` | 同结构，但挂一个 Memory 做上下文压缩 |
| `query()` 里查三个限制 | 同结构，增加令牌预算检查 |
| `PredeterminedTestModel` 替换 `Model` | MockLLM 实现相同的 `query()` 协议 |

## SafeSWE-Lite 的主循环草案

```python
class Agent:
    def __init__(self, model, tools, guardrail, validators, memory):
        self.model = model
        self.tools = tools
        self.guardrail = guardrail
        self.validators = validators
        self.memory = memory

    def run(self, task: str) -> dict:
        self.memory.add_system_message(SYSTEM_PROMPT)
        self.memory.add_user_message(task)
        while self.step_count < self.config.max_steps:
            context = self.memory.assemble()
            response = self.model.query(context)
            action = self.parse_action(response)
            if action.name == "submit":
                return {"exit_status": "submitted", "result": action.result}
            if not self.guardrail.check(action):
                self.memory.add_observation({"blocked": True, "reason": self.guardrail.last_reason})
                continue
            result = self.tools.execute(action)
            feedback = self.validators.validate(result)
            self.memory.add_observation(result, feedback)
            self.step_count += 1
        return {"exit_status": "max_steps_exceeded"}
```

## 预习问题（第 2 节）

mini-swe-agent 的 `Model` 协议里有一个 `query(messages) → dict` 方法。`DeterministicModel`（test_models.py）是如何实现这个方法的？它用什么机制让每个测试用例确定性地获得预定义的 LLM 回复？
