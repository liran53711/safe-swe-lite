# Coding Agent Harness 源码研读课程

以 5 个开源项目为教材，通过阅读源码建立知识框架，最终产出 SafeSWE-Lite 的 SPEC.md。

## 教材

| # | 教材 | 本地路径 | 角色 |
|---|---|---|---|
| 1 | mini-swe-agent | `../../agent-references/mini-swe-agent/` | 最小可运行 harness 架构 |
| 2 | SWE-agent | `../../agent-references/SWE-agent/` | 完整 harness：解析/护栏/历史/配置 |
| 3 | Aider | `../../agent-references/aider/` | 反馈闭环参考（lint/test/retry） |
| 4 | AutoCodeRover | `../../agent-references/auto-code-rover/` | 上下文定位 → 补丁的思路 |
| 5 | Agentless | `../../agent-references/Agentless/` | 非 agent pipeline 作为设计对照 |

完整学习路线见 `../docs/research/REFERENCE_STUDY_PLAN.md`。

## 7 节课程

| 节 | 主题 | 主教材 | 对应 SafeSWE-Lite 维度 |
|---|---|---|---|
| 1 | Agent 主循环 | mini-swe-agent `agents/default.py` | 决策封装 |
| 2 | 模型抽象与环境 | mini-swe-agent `models/` + `environments/` | LLM 抽象层 |
| 3 | 动作解析与护栏 | SWE-agent `tools/parsing.py` + `tools/tools.py` | 动作协议 + 治理护栏 |
| 4 | 历史处理与配置 | SWE-agent `agent/history_processors.py` + `config/` | 记忆 + 配置 |
| 5 | 反馈闭环 | Aider `linter.py` + `commands.py` | 反馈闭环 |
| 6 | 上下文定位 | AutoCodeRover `app/search/` | 工具系统（搜索工具设计） |
| 7 | 对照反思 | Agentless 全项目 + 汇总 | 收尾：准备写 SPEC |

## 教学方式

**苏格拉底式提问驱动**——每节课你读一段源码，我来提问，你解释给我听，我补充纠正。节奏：

```
1. 读前问题（带问题读源码）
2. 源码精读（逐段讲解关键函数）
3. 检查理解（你解释设计意图）
4. 映射 SafeSWE-Lite（这段设计我们怎么用）
5. 笔记归档（写入 course/notes/）
```

## 每节课产出

- 笔记：`course/notes/module-0X-<topic>.md`
- 进度更新：`course/PROGRESS.md`
- 设计决策记录：哪些设计要借鉴、哪些要改进、哪些明确不学

## 最终产出

7 节课结束后，你应该能独立回答 REFERENCE_STUDY_PLAN.md 里的 10 个问题，并据此写出 SPEC.md。

## 开始

当你说 **"开始教学"** 时，从第 1 节开始。
