# REFLECTION — SafeSWE-Lite 项目反思

> 本文件为骨架 + 素材索引。正文由学生本人撰写（课程学术规范要求）。
> 素材来源：`AGENT_LOG.md`（每 task 的教训）、`SPEC_PROCESS.md`（冷启动验证）、`course/notes/`（源码研读）。
> 要求：1500-2500 字。

## 1. 哪些 Superpowers 技能发挥了最大作用、哪些"形式大于实质"？

素材：AGENT_LOG 各 task 条目；brainstorming 技能的表现与不足见 SPEC_PROCESS.md §4。

## 2. TDD 强制在 AI 协作下是阻碍还是放大器？

素材：Task 4 的 Critical（护栏循环不终止）——spec 逐字合规 ≠ 代码正确，测试缺口正是 bug 藏身处；Task 10 的"核心交付物 0 覆盖"教训；Task 8 状态机——"看起来像状态机"的测试全绿假象。

## 3. subagent-driven 工作流让智能体能自主运行多久而不偏离主题？

素材：18 个 task 的完整记录；implementer 提问次数与类型（冷启动 5 问、Task 5 Windows 引号实证、Task 9 pickle.loads 矛盾）。

## 4. 什么样的 task 颗粒度最优？

素材：Task 6（护栏 L1）三轮军备竞赛 vs Task 16（Docker）单轮通过——过大 task 的修复成本非线性增长。

## 5. SPEC / PLAN 质量如何影响实现质量（举一个"规约不清导致 subagent 偏离"的具体案例）？

素材：PLAN 自相矛盾案例合集——Task 6 vim 匹配表矛盾、Task 9 pickle.loads 矛盾、Task 14 fix_bug old_string 不匹配、Task 17 mask 格式矛盾、Task 4 护栏计步设计缺陷（Critical 根因在 PLAN）。

## 6. 你最有效的 prompt / context 策略是什么、为什么有效？

素材：implementer prompt 的构成（完整 task 文本 + 环境约束 + 已知 API + 禁止事项）；冷启动的"遇到不确定立即提问"指令。

## 7. 凭据与分发这两条工程要求，迫使你想清楚了哪些原本会忽略的问题？

素材：Task 12 打包路径（parents[3] 的 wheel 崩溃）、Task 15 打包回归、Task 17 keyring 降级、Docker 的 mock-only 部署决策。

## 8. 如果重做你会改变什么？

## 9. 你对 Superpowers 这套方法论的批判——它假设了什么，这些假设在你的项目里成立吗？

素材：SPEC_PROCESS.md §4（brainstorming 的不满之处）；冷启动验证是手工插入的环节（技能没有内置）；评审循环依赖"评审员比实现者强"的假设。
