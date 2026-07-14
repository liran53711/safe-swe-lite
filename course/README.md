# SafeSWE-Lite 源码研读课程

以 **mini-swe-agent**（入门）和 **SWE-agent**（深入）为教材，通过阅读源码建立 Coding Agent Harness 的知识框架。

## 教材

| 教材 | 路径 | 规模 |
|---|---|---|
| mini-swe-agent | `../mini-swe-agent/src/minisweagent/` | ~300 行核心 |
| SWE-agent | `../SWE-agent/sweagent/` | 完整工程级 |

## 课程模块

| # | 模块 | 核心文件 | 对应 SafeSWE-Lite 维度 |
|---|---|---|---|
| 1 | Agent 主循环 | mini: `agents/default.py` / SWE: `agent/agents.py` | 决策封装 |
| 2 | 动作解析 | SWE: `tools/parsing.py` | 动作协议 |
| 3 | 工具分发 | SWE: `tools/tools.py` (ToolHandler) | 工具系统 |
| 4 | 护栏机制 | SWE: `tools/tools.py` (`should_block_action`) | 治理护栏 |
| 5 | 反馈闭环 | SWE: `agent/agents.py` (`handle_action`, `step`) | 反馈闭环 |
| 6 | 上下文管理 | SWE: `agent/history_processors.py` | 记忆 |
| 7 | Mock LLM 测试 | SWE: `agent/models.py` (PredeterminedTestModel) / mini: `models/test_models.py` | LLM 抽象层 |

## 教学方式

**苏格拉底式提问驱动**——每节课我会让你先读一段源码，然后向你提问，你来解释这段代码做了什么、为什么这样设计。回答之后我再补充和纠正。

每节课的结构：

```
1. 课前提问（激活已有知识）
2. 源码精读（逐段讲解）
3. 检查理解（你解释给我听）
4. 关联 SafeSWE-Lite（这段代码我们怎么用）
```

## 开始

当你说 **"开始教学"** 时，我们从模块 1 开始。
