# 课程笔记索引

## 源码精读笔记

| 节 | 笔记文件 | 状态 |
|---|---|---|
| 1. Agent 主循环 | `module-01-agent-loop.md` | ✅ |
| 2. 模型抽象与环境 | `module-02-model-environment.md` | ⬜ |
| 3. 动作解析与护栏 | `module-03-parsing-guardrails.md` | ✅ |
| 4. 历史处理与配置 | `module-04-history-config.md` | ✅ |
| 5. 反馈闭环 | `module-05-feedback-loop.md` | ✅ |
| 6. 上下文定位 | `module-06-context-localization.md` | ✅ |
| 7. 对照反思 | `module-07-reflection-synthesis.md` | ✅ |

## 设计决策记录

每节课后记录对 SafeSWE-Lite 的设计影响：

| # | 决策 | 来源 | 日期 |
|---|---|---|---|
| 1 | 护栏四层架构：A动作拦截 + B代码内容扫描 + C范围围栏 + D LLM审核补充 | 第3节课讨论 | 2026-07-14 |
| 2 | 单独新增 `guardrails/policy.py` + `guardrails/code_scanner.py` + `guardrails/scope_fence.py` | 决策1衍生 | 2026-07-14 |
| 4 | 记忆：规则评分 + Embedding RAG 双层，粗筛 → 精捞 | 第4节课讨论 | 2026-07-14 |
| 5 | 记忆维度从"最低实现"升级为"第二深入维度"（与反馈闭环并列） | 决策4衍生 | 2026-07-14 |

## 可视化笔记

（暂无，课程开始后按需要生成）
