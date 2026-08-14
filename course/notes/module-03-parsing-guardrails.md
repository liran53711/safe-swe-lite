# 第 3 节笔记：动作解析与护栏

> 教材：SWE-agent `tools/parsing.py`、`tools/tools.py`、`tools/commands.py`

## 直觉

不同的 LLM 用不同的方式表达"我要执行什么操作"——Claude 用 JSON tool call，老 GPT-4 用 markdown 代码块，有的模型用 XML。parser 的作用就是统一这些格式——不管 LLM 怎么输出，最终都变成 harness 能理解的 `(thought, action)`。

## 动作解析：11 种 Parser

SWE-agent 的 `parsing.py` 定义了 11 种 parser，核心职责：**把 LLM 的原始输出翻译成统一的 action 格式**。

### 关键 Parsers

| Parser | 输入格式 | 适用场景 |
|---|---|---|
| `ActionParser` | 纯命令 `ls -l` | 最简模型 |
| `ThoughtActionParser` | 讨论 + `` ```cmd``` `` | 老 GPT-4 |
| `XMLThoughtActionParser` | `<command>cmd</command>` | XML 输出模型 |
| `FunctionCallingParser` | JSON tool_call | Claude / 新 GPT-4 |
| `JsonParser` | `{"thought": ..., "command": {...}}` | JSON 模型 |
| `Identity` | 无解析，直接返回原文本 | 最宽 |

### FunctionCallingParser 核心流程（最贴近 SafeSWE-Lite）

```python
def __call__(self, model_response, commands):
    tool_call = model_response["tool_calls"][0]
    name = tool_call["function"]["name"]
    command = {c.name: c for c in commands}.get(name)    # 匹配已注册命令
    if not command:
        raise FunctionCallingFormatError(...)              # LLM 叫了不存在的工具
    self._parse_tool_call(tool_call, commands)            # 解析参数并格式化
    return message, action                                 # (thought, action)
```

### 参数校验（`_parse_tool_call` 内部）

```
LLM 返回 tool_call 参数
  → 类型检查 (JSON 解析)
  → 必填参数检查 (required_args)
  → 多余参数检查 (extra_args)
  → 引用处理 (_should_quote)
  → 模板渲染 (argument_format)
  → 最终 action 字符串
```

每一步失败都抛 `FunctionCallingFormatError`——agent loop 里的重试机制因此触发。

## 护栏：`should_block_action()`

```python
def should_block_action(self, action: str) -> bool:
    # 第1层：前缀匹配
    if any(action.startswith(f) for f in self.config.filter.blocklist):
        return True

    # 第2层：精确匹配
    if action in self.config.filter.blocklist_standalone:
        return True

    # 第3层：正则白名单
    name = action.split()[0]
    if name in self.config.filter.block_unless_regex and not re.search(...):
        return True

    return False
```

### 三层拦截机制

| 层 | 机制 | 默认拦截内容 | 覆盖场景 |
|---|---|---|---|
| 第1层 | 前缀匹配 | vim, vi, emacs, nano, nohup, gdb, less, tail -f, python -m venv, make | 交互式编辑器、长驻进程 |
| 第2层 | 精确匹配 | python, python3, ipython, bash, sh, /bin/bash, /bin/sh, su | 交互式 REPL 或 shell 逃逸 |
| 第3层 | 正则白名单 | radare2（除非带 -c 参数） | 需要特定条件才能放行的工具 |

### 护栏的黄金位置

```
model.query()   → LLM 决策
parse_actions() → 解析动作
should_block_action()  → ← 【护栏在这里】 解析之后、执行之前
env.execute()   → 执行动作
```

这个位置意味着护栏永远不会被 prompt 绕过——它读的是 action 字符串，不是 LLM 说了什么。

## 与 SafeSWE-Lite 的差异点

| 维度 | SWE-agent | SafeSWE-Lite |
|---|---|---|
| Parser 数量 | 11 种 | 1 种（`JSONParser`，基于 Pydantic） |
| Action 格式 | 字符串 | JSON Object（7 个工具各有 schema） |
| 护栏层数 | 1 层（3 种匹配） | 3 层（静态 + 正则 + HITL 状态机） |
| 工具定义 | `Command` 类 + YAML | Pydantic `Action` + `Tool` 类 |
| 可用工具告知 LLM | `{{command_docs}}` 模板变量 | 7 个 tool JSON Schema 传给 API |

## 关键洞察

SWE-agent 有 11 种 parser 是因为它在解决一个历史问题：不同 LLM 对 tool calling 的支持度参差不齐。2026 年这个情况已经大幅收敛——几乎所有主流 LLM 都支持 OpenAI 格式的 function calling。所以 SafeSWE-Lite 只需要一种 parser（JSON 格式，Pydantic 校验），省掉了 10 种 parser 的复杂度。

## 预习问题（第 4 节）

SWE-agent 的 `history_processors.py` 里有 `LastNObservations` 和 `ClosedWindowHistoryProcessor`。它们分别在解决什么样的上下文管理问题？各自如何降低传给 LLM 的消息体积？
