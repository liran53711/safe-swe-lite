# SPEC_PROCESS — 规约与计划生成过程记录

## 1. Brainstorming 关键节点

### 1.1 起点：调研名校成熟项目

需求调研（`PROJECT_REQUIREMENTS_RESEARCH.md`）覆盖：

- 学术项目：SWE-agent（Princeton, NeurIPS 2024）、AutoCodeRover（NUS, ICSE 2025）、Agentless（UIUC）
- 开源项目：OpenHands（CMU 系）、Aider
- 工业实现：Claude Code、Codex CLI

关键决策链：

1. 用户提出"调研名校项目、跟做、面试有辨识度" → 展开为 5 个参考项目的对比
2. 选定 **SWE-agent 为主要参考骨架**，缝合 Claude Code（分层护栏、hooks 思想）与 Aider（lint+test+重试反馈）
3. 主贡献从"护栏+反馈并列"收窄为**护栏为主、反馈为次**（课程要求单选一个 main contribution）
4. 记忆维度从"最低实现"升级为**评分+embedding 双层**（用户时间充裕、追求含金量）

### 1.2 智能体追问的好问题（brainstorming 阶段）

| 问题 | 对设计的影响 |
|---|---|
| "agent 设计得好是不是取决于动作丰富程度？" | 引出 ACI 概念：工具是 agent 的用户界面，质量>数量 |
| "LLM 为什么不会误解工具？是不是要写文档？" | 引出 JSON Schema description 即 LLM 的 API 文档 |
| "护栏硬编码代码量永远不够，引入辩论式 LLM 护栏？" | 明确 LLM-as-Judge 只能作补充层，不可单测，不进入 main contribution |
| "LastNObservations 按时间过滤不精确，靠前的关键信息会丢" | 记忆维度升级为评分过滤 + embedding 检索 |
| "如果用户说不准用某个 C 函数，护栏怎么拦？" | 引出护栏第四层：代码内容扫描（AST 禁用符号） |

### 1.3 源码研读课程（7 节）

以 mini-swe-agent 和 SWE-agent 等 5 个仓库为教材，苏格拉底式提问驱动，产出 7 份笔记（`course/notes/module-0X-*.md`），建立 harness 知识框架后才有能力写 SPEC。

## 2. 冷启动验证记录（课程 §4.5）

### 2.1 实验设置

- **主开发智能体**：Claude Code
- **冷启动智能体**：另一个 CLI agent（全新会话，无对话历史）
- **输入**：仅 `SPEC.md` + `PLAN.md`
- **任务**：实现 PLAN Task 2（Action Protocol）
- **指令**：遇到不确定立即暂停提问，不凭猜测继续

### 2.2 冷启动智能体提出的问题与答复

**Q1：Task 2 是否只做 action 名称和 JSON 格式校验，参数级 Pydantic 校验留到后续 task？**

→ 是。Task 2 只校验名称与格式；参数级校验由 Task 5 各工具函数在调用时处理。SPEC 原句"7 个工具及其参数均由 Pydantic 模型定义"是最终形态的过度描述，已修订为"Action 由 Pydantic 模型定义；参数级校验由各工具函数在调用时自行处理"。

**Q2：缺少 `parameters` 是允许并默认空字典，还是抛 ProtocolError？**

→ 允许，默认 `{}`。`submit` 和 `list_files` 天然无参数，强制必填会污染协议。

**Q3：`parameters` 存在但不是对象（如字符串），是否抛 ProtocolError？**

→ 是，抛 `ProtocolError("'parameters' must be an object")`。**这是 PLAN 的真实缺陷**——原实现会把字符串直接传进 Action 导致下游工具静默出错。已修订 PLAN 测试与实现。

**Q4：`response` 缺少 `"message"` key，应报 "missing message" 还是当作无效 JSON？**

→ 应明确报 `ProtocolError("LLM output missing 'message' key")`。**PLAN 缺陷**：原实现 `response.get("message", "")` 会让空串走 JSON 解析失败路径，错误信息误导。已修订。

**Q5：SPEC.md 在冷启动智能体环境中显示乱码，是否以 PLAN.md 为准？**

→ 已用 `file` + `xxd` 验证 SPEC.md 磁盘上是合法 UTF-8（无 BOM）。乱码是冷启动智能体会话的编码问题（Windows 默认 GBK 读 UTF-8）。答复：以 PLAN.md Task 2 代码为准继续，SPEC.md 本体无需修改。

### 2.3 暴露的 SPEC/PLAN 缺陷清单

| # | 缺陷 | 位置 | 修订 |
|---|---|---|---|
| 1 | `parameters` 非对象未校验 | PLAN Task 2 | 增加校验 + 2 个测试（test_parse_non_dict_parameters_raises） |
| 2 | `message` key 缺失时错误信息误导 | PLAN Task 2 | 显式检查 + 1 个测试（test_parse_missing_message_key_raises） |
| 3 | SPEC 参数校验措辞过度承诺 | SPEC §3.3 | 修订措辞 |
| 4 | sample project 的 bug 不 bug（三个测试全通过） | PLAN Task 14 | 自查发现并修复：`if not username: return True  # BUG` |

### 2.4 预判 vs 实际

主智能体在冷启动运行前做了预判（5 项）。对比结果：

| 预判 | 实际 |
|---|---|
| Model 响应格式未在 Task 2 显式定义（高，可能提问） | ✅ 命中（Q1 间接涉及） |
| GuardrailDecision 跨模块导入 | 未发生（Task 2 不涉及护栏） |
| Task 4 memory vs _messages 不一致 | 未发生（未做到 Task 4） |
| Dispatcher 函数内 import | 未发生 |
| MockLLM IndexError 太粗糙 | 未发生 |
| **parameters 非对象校验缺失** | ❌ **漏判**（Q3，真实缺陷） |
| **message key 缺失错误信息** | ❌ **漏判**（Q4，真实缺陷） |

**教训**：预判聚焦在"跨文件一致性"和"代码品味"上，漏掉了"输入边界条件未穷举"这一类最容易被冷启动 agent 抓到的缺陷。以后自审 SPEC 时优先做边界条件穷举，而不是代码风格审查。

### 2.5 冷启动结论

SPEC 与 PLAN 在修订后通过冷启动验证。Task 2 的测试用例数从 5 增至 8，协议边界条件完整覆盖：缺 message、非法 JSON、缺 action、未知 action、缺 parameters（默认）、parameters 非对象。

**冷启动 agent 最终产出验证（主 agent 复核）：**

- `src/safe_swe_lite/agent/protocol.py`：与修订后 PLAN 的实现逐行一致
- `tests/test_protocol.py`：8 个测试覆盖全部边界条件
- TDD 纪律：transcript 记录了完整的 RED→RED→GREEN 过程（含真实命令输出）
- 测试结果：`PYTHONPATH=src` 下 `8 passed in 0.21s`
- 附加发现：裸 `pytest` 因缺 Task 1 骨架（pyproject.toml）失败——执行顺序问题，非 spec 缺陷；开发从 Task 1 开始即可
- 完整实验记录：`docs/spec_process/cold_start_codex_transcript.md`

**冷启动验证：通过。可以进入实现阶段。**

## 3. SPEC / PLAN 修订记录

| 日期 | 修订 | 触发 |
|---|---|---|
| 2026-08-15 | PLAN Task 2 增加 2 个边界校验 + 3 个测试 | 冷启动 Q3/Q4 |
| 2026-08-15 | SPEC §3.3 参数校验措辞 | 冷启动 Q1 |
| 2026-08-15 | PLAN Task 14 sample project 修正为真 bug | 主智能体自查 |
| 2026-08-15 | PLAN 增加冷启动阶段插入课程 | 用户需求变更 |

## 4. 反思：brainstorming 技能的表现

**做得好的**：

- 一个问题一次提问的节奏，让模糊想法逐步收敛为可签字的设计
- 对"主贡献单选"的坚持纠正了初始"两个都深入"的倾向

**不满意的**：

- 技能默认把 SPEC 存到 `docs/superpowers/specs/`，与课程要求的根目录 `SPEC.md` 冲突，需人工覆盖
- 技能假设 spec 完成后直接进实现，没有内置"冷启动验证"环节——课程的 Phase 0.5 是手工插入的
