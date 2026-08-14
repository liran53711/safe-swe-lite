# 第 7 节笔记：对照反思 + SPEC 准备

> 教材：Agentless（UIUC）+ 六节课全部内容汇总

## Agentless 的主张与边界

Agentless：不做 agent 循环，只做 localization → repair → validation 三个固定阶段，SWE-bench 27.8%，超过当时大多数 agent 系统。

### 为什么它能赢

SWE-bench 任务是高度结构化的：给 issue → 修代码 → 跑测试。"定位→修补→验证"三阶段对这类任务够用。

### 为什么它有边界

| 任务特征 | Agentless 表现 |
|---|---|
| issue 清晰、bug 可定位 | 好 |
| 需要多轮调试（改→跑→看→再改） | 差——没有反馈迭代 |
| 需要运行时探索 | 不可能——没有执行工具 |
| 开放式任务（"重构这个模块"） | 无从下手 |

**核心洞察：agent 循环是 pipeline 的超集。** Agentless 能表达的流程 agent 循环都能表达；反过来不行。

### 课程为什么要求 agent 主循环

1. 课程命题是 harness 工程训练——没有主循环就没有 harness 内核可写
2. agent 循环是超集，能讲的故事更多
3. 提供批判性反思的机会（REFLECTION 的素材）

## 从 Agentless 吸收的三个设计（Y）

1. **分层定位**：先文件后行号 → SafeSWE-Lite 工具链顺序
2. **确定性验证作为核心信号**：validation 是纯代码 → 反馈闭环的三个校验器
3. **"能确定性的就不要 agentic"**：护栏/校验/工具分发全是确定性代码

## 面试话术模板

> "我知道 Agentless 主张很多修复任务不需要 agent 循环。我选择 agent 循环是因为它支持多轮自主探索——任务需要改→跑→看→再改的迭代时 pipeline 无能为力。同时我吸收了 Agentless 的分层定位、确定性验证、和'能确定性的就不要 agentic'这三个设计。"

## REFERENCE_STUDY_PLAN 10 问的答案（SPEC 骨架）

| # | 问题 | 答案 |
|---|---|---|
| 1 | 动作 JSON Schema | `{"action": "<tool>", "parameters": {...}}`，7 工具各 Pydantic schema |
| 2 | v1 允许的动作 | read_file / write_file / edit_file / run_command / search_pattern / list_files / submit |
| 3 | deny / allow / HITL | deny: rm -rf、sudo、读 .env、workspace 外；HITL: git push、curl pipe sh、删文件 |
| 4 | 拦截如何进 trace | `{"guardrail_decision": "blocked", "reason": ..., "layer": N}`，WebUI 红色标记 |
| 5 | write_file 后校验器 | ruff → mypy → pytest 链式，合并 ValidationResult 列表 |
| 6 | 重试轮数 | 3 轮，之后 observation 交回主循环 |
| 7 | 记忆持久化 | 会话内：全量消息 + 分级上下文（评分 + embedding）；跨会话：约定/修改/错误 → JSON |
| 8 | YAML 配置 | workspace、max_turns、timeout、provider、allow/block/ask 规则、校验器开关 |
| 9 | 机制演示 | ① rm -rf / 拦截 ② 失败注入→修正→通过 ③ 护栏三层完整链路 |
| 10 | WebUI 展示 | 两个 demo + 逐步 trace + guardrail 决策标记 + trace JSON 下载 |

## 七节课知识框架全景

```
┌─ 决策循环 ─────────────────────────────┐
│ while True: step() = query + execute   │
│ 停机: role=="exit" 结构化判断          │
│ 异常驱动的统一停机路径                  │
└────────────────────────────────────────┘
         ↓ 调用                    ↓ 执行
┌─ LLM 抽象 ───────┐      ┌─ 工具系统 ────────────┐
│ Model 协议       │      │ 7 个结构化工具          │
│ MockLLM 预录播放 │      │ 精确 schema + 文档      │
│ 真实 provider 适配│     │ 定位链: list→search→read│
└──────────────────┘      └───────────────────────┘
         ↓ 组装                    ↑ 校验
┌─ 记忆 ────────────────────────────────────┐
│ 全量消息 + 分级上下文                       │
│ 评分过滤 + embedding 检索                   │
│ 近10轮原始 + 远期摘要                       │
└───────────────────────────────────────────┘
         ↓ 拦截
┌─ 护栏（主贡献）─────────────────────────────┐
│ L1 静态黑名单   L2 正则白名单                │
│ L3 HITL 状态机  + scope fence              │
│ + code policy 扫描 + LLM 审核补充            │
└───────────────────────────────────────────┘
         ↓ 反馈
┌─ 反馈闭环 ────────────────────────────────┐
│ ruff → mypy → pytest 校验链               │
│ ValidationResult 结构化错误                │
│ 3 轮有界重试 → 交回主循环                   │
└───────────────────────────────────────────┘
```

## 下一步

课程完成 → 写 SPEC.md（含 §A.5 领域与机制设计）→ 写 PLAN.md → 冷启动验证 → 开发。
