# SafeSWE-Lite Git 与 CI/CD 开发流程规划

日期：2026-07-14

## 1. 目标

本文件规划 SafeSWE-Lite 的开发顺序，重点围绕 Git、分支、PR、CI/CD、部署和课程过程证据展开。

本项目的开发目标不是一次性写完代码，而是形成可检查的工程轨迹：

- 每个功能从 issue / task 开始。
- 每个 task 在独立分支或 worktree 中完成。
- 每个 task 先写失败测试，再写实现。
- 每个 PR 都有 CI 记录。
- 每次合并都更新 `PLAN.md` 和 `AGENT_LOG.md`。
- 最终 GitHub Actions pass，线上 WebUI 可访问。

## 2. 仓库初始化阶段

### 2.1 创建 GitHub 仓库

建议仓库名：

```text
safe-swe-lite
```

仓库描述：

```text
A lightweight SWE-agent-inspired coding agent harness with deterministic guardrails and test-feedback self-correction.
```

建议公开仓库，便于老师和面试官查看。如果必须私有，需要提前把老师或助教加入协作者。

### 2.2 本地初始化

推荐从一个干净目录开始，而不是直接在课程资料目录中写源码：

```bash
mkdir safe-swe-lite
cd safe-swe-lite
git init
git branch -M main
```

第一批文件只放项目骨架和文档：

```text
README.md
SPEC.md
PLAN.md
SPEC_PROCESS.md
AGENT_LOG.md
REFLECTION.md
.gitignore
.env.example
pyproject.toml
Dockerfile
.github/workflows/ci.yml
```

初始 commit：

```bash
git add .
git commit -m "chore: initialize SafeSWE-Lite project"
git remote add origin git@github.com:<user>/safe-swe-lite.git
git push -u origin main
```

如果 SSH 未配置，也可使用 HTTPS remote。

## 3. Git 工作流

### 3.1 分支策略

主分支：

```text
main
```

功能分支命名：

```text
task/<number>-<short-name>
```

示例：

```text
task/01-project-scaffold
task/02-action-protocol
task/03-mock-llm
task/04-agent-loop
task/05-guardrails
task/06-feedback-loop
task/07-cli
task/08-webui
task/09-docker-deploy
```

### 3.2 Worktree 策略

课程要求使用 git worktrees 隔离工作区。推荐每个独立 task 使用一个 worktree：

```bash
git worktree add ../safe-swe-lite-task-02 -b task/02-action-protocol main
```

完成 task 后：

```bash
git push -u origin task/02-action-protocol
```

然后在 GitHub 上开 PR。

PR 合并后清理 worktree：

```bash
git worktree remove ../safe-swe-lite-task-02
git branch -d task/02-action-protocol
```

### 3.3 Commit 规范

推荐使用 Conventional Commits：

```text
chore: initialize project scaffold
test: add action protocol parsing tests
feat: implement JSON action protocol
test: add guardrail denial cases
feat: block dangerous shell commands
docs: update agent log for task 05
ci: add GitHub Actions unit test workflow
```

每个 task 至少包含：

- 失败测试 commit。
- 实现 commit。
- 文档 / AGENT_LOG 更新 commit。

如果 task 很小，可以把测试和实现放在同一个 PR，但 `AGENT_LOG.md` 中必须写清 TDD 顺序和验证结果。

## 4. CI/CD 总体设计

### 4.1 GitHub Actions 作为主 CI

CI 文件：

```text
.github/workflows/ci.yml
```

触发条件：

```text
push 到 main
pull_request 指向 main
```

CI job 建议：

```text
unit-test
lint
docker-build
```

其中 `unit-test` 是核心 job，负责证明课程要求的 mock LLM 机制测试能通过。

### 4.2 CI 必跑内容

`unit-test` 应至少执行：

```bash
pytest -q
```

如果使用 `ruff`：

```bash
ruff check src tests
```

如果使用类型检查：

```bash
mypy src
```

Docker 构建验证：

```bash
docker build -t safe-swe-lite:ci .
```

### 4.3 兼容课程中的 GitLab CI 字面要求

课程通用文件提到 `.gitlab-ci.yml` 且必须包含名为 `unit-test` 的 job。但老师现在又说使用 GitHub 实现持续集成记录。

建议做法：

- GitHub Actions 作为主 CI 和最终检查记录。
- 额外保留 `.gitlab-ci.yml`，其中包含 `unit-test` job，作为课程文档要求的兼容文件。

这样可以同时满足：

- 老师在线检查 GitHub Actions。
- 课程文件中对 `.gitlab-ci.yml` 的字面要求。

## 5. 部署策略

### 5.1 推荐部署平台

推荐使用 Render 或 Railway：

- 能直接连接 GitHub 仓库。
- 支持 Dockerfile 或 Python Web Service。
- 自动从 main 分支部署。
- 能提供公开 URL。

### 5.2 部署对象

部署的不是完整 coding workspace，而是一个安全的 WebUI demo：

```text
FastAPI Web 服务
  /                 静态 WebUI
  /api/demo/fix-bug 运行 mock fixing demo
  /api/demo/blocked 运行 guardrail blocked demo
  /api/health       健康检查
```

线上环境默认只允许 mock 模式，避免老师检查时触发真实付费 LLM 或危险命令。

真实 LLM 模式可以保留在本地 CLI 或受保护配置中。

### 5.3 部署环境变量

线上 mock demo 不需要真实 key。

如果后续支持真实 LLM，应使用平台环境变量：

```text
SAFE_SWE_LITE_PROVIDER_BASE_URL
SAFE_SWE_LITE_API_KEY
SAFE_SWE_LITE_MODEL
```

不得把 key 写入：

- Git 仓库。
- Dockerfile。
- README。
- WebUI 日志。
- GitHub Actions 明文输出。

## 6. 开发顺序

### Phase PRE：源码研读课程（SPEC 的前置条件）

**在写 SPEC 之前，必须先吃透参考代码。** 否则 SPEC 是从想象出发的，不是从工程现实出发的。

课程文件：`course/README.md`、`course/PROGRESS.md`

学习路线：`docs/research/REFERENCE_STUDY_PLAN.md`

教材（5 个项目，存放在 `../agent-references/`，不进入本仓库）：

| # | 教材 | 用途 |
|---|---|---|
| 1 | mini-swe-agent | 最小可运行 harness 架构（入门） |
| 2 | SWE-agent | 完整 harness：解析/护栏/历史/配置 |
| 3 | Aider | 反馈闭环参考：lint/test/retry |
| 4 | AutoCodeRover | 上下文定位 → 补丁的思路 |
| 5 | Agentless | 非 agent pipeline 作为设计对照 |

七节课程（苏格拉底式提问驱动）：

| # | 主题 | 主教材 | 对应维度 |
|---|---|---|---|
| 1 | Agent 主循环 | mini-swe-agent `agents/default.py` | 决策封装 |
| 2 | 模型抽象与环境 | mini-swe-agent `models/` + `environments/` | LLM 抽象层 |
| 3 | 动作解析与护栏 | SWE-agent `tools/parsing.py` + `tools/tools.py` | 动作协议 + 治理护栏 |
| 4 | 历史处理与配置 | SWE-agent `agent/history_processors.py` + `config/` | 记忆 + 配置 |
| 5 | 反馈闭环 | Aider `linter.py` + `commands.py` | 反馈闭环 |
| 6 | 上下文定位 | AutoCodeRover `app/search/` | 工具系统 |
| 7 | 对照反思 + SPEC 准备 | Agentless 全项目 + 汇总 | 收尾 |

每节课产物：`course/notes/module-0X-*.md` 笔记 + PROGRESS.md 更新。

课程不产生 Git 操作（不写代码），纯学习。全部 7 节课结束后，进入 Phase 0。

### Phase 0：SPEC 与 PLAN（禁止写代码）

**这是课程最关键的纪律——在 SPEC 与 PLAN 完成并通过冷启动验证之前，禁止编写任何实现代码。**

目标：

```text
完成需求调研，产出完整的 SPEC.md 和 PLAN.md，创建 GitHub 仓库。
```

产物：

- `PROJECT_REQUIREMENTS_RESEARCH.md`（已完成）
- `SPEC.md` 完整版（含 §A.5 领域与机制设计章节）
- `PLAN.md` 完整版（每个 task 含文件路径、验证步骤、依赖关系）
- `SPEC_PROCESS.md`（brainstorming 关键节点记录）
- GitHub 仓库创建
- `README.md` 初稿、`.gitignore`、`pyproject.toml` 占位

Git 操作：

```bash
git checkout -b task/00-project-docs
git add PROJECT_REQUIREMENTS_RESEARCH.md SPEC.md PLAN.md SPEC_PROCESS.md README.md .gitignore
git commit -m "docs: complete SPEC and PLAN for SafeSWE-Lite"
git push -u origin task/00-project-docs
```

CI/CD：暂不创建，Phase 1 再做。

### Phase 0.5：冷启动验证（课程强制要求）

**这是规约工作中最关键的客观证据。** 课程 §4.5 要求：

- 用**一个与主开发 agent 不同的 agent 类型**（例如主开发用 Claude Code，冷启动用 Codex CLI 或 Gemini CLI）。
- **不提供任何对话历史**，仅提供 `SPEC.md` + `PLAN.md`。
- 让它从 PLAN 中选 1–2 个 task 自主实现（约 1–2 小时）。
- 记录它在哪里暂停提问、暴露了哪些 SPEC 缺陷、做出了哪些与原意不一致的解读。
- 据此修订 SPEC 和 PLAN。

产物：

- `SPEC_PROCESS.md` 中新增「冷启动验证」章节，记录：
  - 使用的第二个 agent 类型
  - 它在哪里暂停提问
  - 暴露了哪些 SPEC 缺陷
  - 修订前后关键 diff

**在冷启动验证通过之前，不得进入 Phase 1。**

### Phase 1：项目骨架与最小 CI

目标：

```text
创建 Python package、测试框架、最小 CI，让 GitHub Actions 第一次变绿。
```

产物：

- `pyproject.toml`
- `src/safe_swe_lite/__init__.py`
- `tests/test_smoke.py`
- `.github/workflows/ci.yml`

Git 操作：

```bash
git worktree add ../safe-swe-lite-task-01 -b task/01-project-scaffold main
```

PR 检查：

- GitHub Actions `unit-test` pass。
- README 有本地测试命令。

### Phase 2：Action Protocol

目标：

```text
定义 LLM 输出动作的 JSON 协议，并用测试约束解析和校验行为。
```

产物：

- `src/safe_swe_lite/agent/actions.py`
- `src/safe_swe_lite/agent/protocol.py`
- `tests/test_action_protocol.py`

Git/CI 要点：

- 先提交失败测试。
- 再提交最小实现。
- PR 中附上 CI pass 截图或链接。

### Phase 3：MockLLM 与 Agent Loop

目标：

```text
实现可注入 MockLLM 的 agent 主循环。
```

产物：

- `src/safe_swe_lite/llm/base.py`
- `src/safe_swe_lite/llm/mock.py`
- `src/safe_swe_lite/agent/loop.py`
- `tests/test_agent_loop.py`

Git/CI 要点：

- MockLLM 测试必须不依赖网络。
- 这是 A 类项目的核心评分证据之一。

### Phase 4：工具系统

目标：

```text
实现文件读取、文件写入、文本搜索、命令执行和工具分发。
```

产物：

- `src/safe_swe_lite/tools/dispatcher.py`
- `src/safe_swe_lite/tools/read_file.py`
- `src/safe_swe_lite/tools/write_file.py`
- `src/safe_swe_lite/tools/search.py`
- `src/safe_swe_lite/tools/run_command.py`
- `tests/test_tool_dispatcher.py`

Git/CI 要点：

- 所有工具默认限制在 workspace 内。
- 命令执行要有 timeout。
- CI 中测试不能依赖外部网络。

### Phase 5：Guardrail

目标：

```text
实现确定性的危险动作拦截。
```

产物：

- `src/safe_swe_lite/guardrails/policy.py`
- `src/safe_swe_lite/guardrails/checker.py`
- `tests/test_guardrails.py`
- `examples/tasks/blocked_dangerous_action.json`

必须测试：

- 阻止读取 `.env`。
- 阻止访问 workspace 外路径。
- 阻止 `rm -rf`、`git push --force`、`curl | sh` 等危险命令。
- 允许 `pytest`、`python -m pytest`、`ls`、`rg` 等安全命令。

Git/CI 要点：

- 这是重点机制，PR 描述要写清楚“这是代码机制，不是提示词”。
- AGENT_LOG 记录人工确认的规则边界。

### Phase 6：Feedback Loop

目标：

```text
实现测试失败 -> observation -> 下一轮修正的闭环。
```

产物：

- `src/safe_swe_lite/feedback/observation.py`
- `src/safe_swe_lite/feedback/test_runner.py`
- `tests/test_feedback_loop.py`
- `examples/sample_project/`
- `examples/tasks/fix_bug.json`

必须测试：

- MockLLM 第一次写错实现。
- Harness 运行测试并捕获失败。
- 失败信息进入下一轮 prompt / observation。
- MockLLM 第二次写正确实现。
- 最终测试通过并 finish。

Git/CI 要点：

- CI 中必须运行该 mock demo 测试。
- 这是老师检查 A 类项目”反馈闭环”的核心证据。

### Phase 7：Memory 与 Config（最低实现）

目标：

```text
实现六个维度中的记忆和配置两个维度的最低可用实现，补齐 harness 闭环。
```

产物：

- `src/safe_swe_lite/memory/store.py`
- `src/safe_swe_lite/config/` 配置加载模块
- `config/default.yaml`
- `tests/test_memory.py`
- `tests/test_config.py`

记忆最低实现：

- 消息列表存储（agent 运行期间的全量对话）
- 分级上下文 assemble：近 10 轮保留原始消息，更早轮次规则压缩为摘要
- 跨会话持久化：项目约定、最近修改文件列表保存到 JSON

配置最低实现：

- YAML 配置文件：workspace 路径、max_turns、timeout、model provider、allow/block/ask 规则
- 启动时校验配置合法性
- 配置注入到 Agent、Guardrail、Tools 各组件

### Phase 8：CLI

目标：

```text
提供本地可运行命令。
```

示例命令：

```bash
safe-swe-lite run examples/tasks/fix_bug.json --mock
safe-swe-lite run examples/tasks/blocked_dangerous_action.json --mock
```

产物：

- `src/safe_swe_lite/cli.py`
- `tests/test_cli.py`
- README 使用说明。

Git/CI 要点：

- CI 中运行 CLI smoke test。

### Phase 9：机制演示（课程 §A.6 三个硬性演示）

目标：

```text
实现课程要求的三个确定性机制演示，全部在 mock LLM 下运行。
```

产物：

- `tests/test_mechanism_demo_1_guardrail_block.py` —— 护栏拦截演示
- `tests/test_mechanism_demo_2_feedback_correction.py` —— 反馈闭环演示
- `tests/test_mechanism_demo_3_layered_guardrail.py` —— 重点维度演示
- 或合并为一个可运行脚本 `scripts/run_all_demos.py`

三个演示的具体内容（必须可重复运行、不依赖网络和真实 LLM）：

| # | 演示内容 | 验证方式 |
|---|---|---|
| ① 护栏拦截 | MockLLM 输出 `rm -rf /`，guardrail 三层拦截 | 断言 action blocked，命令未执行 |
| ② 反馈闭环 | 注入一次 pytest 失败，agent 收到失败信息后修改代码 | 断言第1次失败 → 第2次修改 → 第3次通过 |
| ③ 重点维度 | 护栏三层完整链路：静态 blocklist → 正则白名单放行安全变体 → HITL 状态机 pending→approved | 断言每层执行了正确的分支 |

Git/CI 要点：

- CI 必须运行这三个演示测试。
- 这些测试是 A 类项目的核心评分证据。

### Phase 10：WebUI

目标：

```text
提供老师可在线检查的 WebUI。
```

产物：

- `src/safe_swe_lite/web/app.py`
- `src/safe_swe_lite/web/static/index.html`
- `src/safe_swe_lite/web/static/style.css`
- `src/safe_swe_lite/web/static/app.js`
- `tests/test_web_app.py`

WebUI 功能：

- 运行 fix bug mock demo。
- 运行 blocked action mock demo。
- 展示 action / observation / guardrail trace。
- 提供 trace JSON 下载或复制。

Git/CI 要点：

- CI 中测试 `/api/health`。
- WebUI 默认 mock-only，降低部署风险。

### Phase 11：Docker 与部署

目标：

```text
实现容器分发，并部署到 Render / Railway / Fly.io。
```

产物：

- `Dockerfile`
- `.dockerignore`
- README Docker 运行说明。
- 部署平台配置。

命令：

```bash
docker build -t safe-swe-lite .
docker run -p 8000:8000 safe-swe-lite
```

Git/CI 要点：

- GitHub Actions `docker-build` pass。
- main 分支合并后触发部署平台自动部署。
- README 写入线上 URL。

### Phase 12：真实 LLM Provider 与凭据安全

目标：

```text
在不影响 mock 确定性测试的前提下，支持 OpenAI-compatible provider。
```

产物：

- `src/safe_swe_lite/llm/openai_compatible.py`
- `.env.example`
- README 凭据安全章节。

要求：

- key 从环境变量或 keyring 读取。
- 不在日志中回显 key。
- mock 模式无需 key。
- 测试默认不调用真实 LLM。

Git/CI 要点：

- CI 不需要真实 key。
- 真实 LLM 测试标记为 optional，不进入默认 unit-test。

### Phase 13：课程过程文件收尾

目标：

```text
补齐课程要求的过程证据和最终提交材料。
```

产物：

- `SPEC.md` 最终版（含修订标记）
- `PLAN.md` 最终版（所有 task 标记完成 + commit hash）
- `SPEC_PROCESS.md` 最终版（含冷启动验证记录）
- `AGENT_LOG.md` 完整版（每个 task、subagent、commit、人工干预）
- `REFLECTION.md`（1500-2500 字）
- `README.md` 最终版

Git/CI 要点：

- 所有最终文档通过 PR 合并。
- 最后一次 GitHub Actions 必须 pass。
- README 包含 Actions 链接和线上 URL。

## 7. 每个 PR 的检查清单

每个 PR 合并前检查：

- 是否有对应 task 编号。
- 是否先写了测试。
- 是否本地运行测试通过。
- 是否 GitHub Actions 通过。
- 是否更新 `AGENT_LOG.md`。
- 是否需要更新 `PLAN.md` 状态和 commit hash。
- 是否没有提交 `.env`、key、token、日志中的敏感信息。
- 是否 PR 描述写清楚使用的 agent / subagent 和人工修改。

## 8. 最终验收路线

最终提交前按顺序检查：

1. `pytest -q` 本地通过。
2. `docker build -t safe-swe-lite .` 本地通过。
3. `docker run -p 8000:8000 safe-swe-lite` 本地可打开 WebUI。
4. GitHub Actions 最后一次 workflow pass。
5. Render / Railway / Fly.io 线上 URL 可访问。
6. WebUI 能运行两个 mock demo。
7. README 包含安装、运行、Docker、CI、部署、凭据安全说明。
8. `SPEC.md`、`PLAN.md`、`SPEC_PROCESS.md`、`AGENT_LOG.md`、`REFLECTION.md` 全部完成。
9. Git 历史不是单次大提交，有可解释的 PR / commit 轨迹。
10. 仓库中没有真实 API key。

## 9. 推荐时间安排

如果以两周为开发周期：

```text
Day 1-3:  Phase PRE：源码研读课程（7 个模块，每模块约 30-60 分钟）
Day 4:    需求调研 + SPEC.md 完整版（含 §A.5 领域与机制设计）
Day 5:    PLAN.md + 冷启动验证准备
Day 6:    冷启动验证（换个 agent 读 SPEC+PLAN 试做 1-2 task）→ 修订 SPEC/PLAN
Day 7:    Phase 1 项目骨架 + Phase 2 Action Protocol
Day 8:    Phase 3 MockLLM + Agent Loop + Phase 4 工具系统
Day 9:    Phase 5 Guardrail（重点维度，多投入）
Day 10:   Phase 6 Feedback Loop + Phase 7 Memory/Config
Day 11:   Phase 8 CLI + Phase 9 三个机制演示
Day 12:   Phase 10 WebUI + Phase 11 Docker
Day 13:   Phase 12 真实 LLM Provider + 凭据安全 + 部署上线
Day 14:   REFLECTION + README + 最终检查 + 提交
```

如果时间更紧，优先级如下：

```text
必须完成（评分核心）：
  MockLLM + Agent Loop + Tool Dispatcher + Guardrail + Feedback Loop
  + 三个机制演示 + mock 单元测试 + CI pass + WebUI URL

可以简化：
  真实 LLM provider、漂亮前端、多 demo 场景

绝对不要做：
  多 agent 协作、大规模 benchmark、复杂沙箱、复杂向量数据库
```

