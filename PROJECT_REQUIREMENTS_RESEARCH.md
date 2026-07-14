# A 类 Coding Agent Harness 项目前期需求调研

日期：2026-07-14

## 1. 调研目的

本文件用于把课程外部要求、参考项目调研和本项目初步定位固化下来。当前阶段不写实现代码，目标是先回答三个问题：

1. 课程到底要求交付什么。
2. A 类 Coding Agent Harness 的硬性边界是什么。
3. 我们应该做一个什么形态的 agent，既能满足课程检查，也能作为简历项目讲清楚。

## 2. 课程外部要求解析

### 2.1 项目类型

本项目选择 A 类：Coding Agent Harness。

课程中的核心定义是：

```text
Agent = LLM + Harness
```

因此本项目不是做一个普通聊天机器人，也不是做一个简单代码生成器，而是实现一套能把 LLM 包装成 coding agent 的工程系统。

项目产物必须包含自己实现的 harness 内核，包括：

- agent 主循环：组织上下文、调用 LLM、解析动作、执行工具、回灌结果、判断停止。
- LLM 抽象层：支持真实 LLM，也支持 MockLLM / StubLLM。
- 动作协议：定义 LLM 可以输出哪些动作，以及动作如何被解析和校验。
- 工具系统：让 agent 能读取文件、搜索代码、写文件、运行命令、运行测试。
- 治理护栏：危险动作执行前必须被确定性代码拦截或要求人工确认。
- 反馈闭环：测试、lint、命令结果等客观信号必须能回灌给 agent。
- 上下文与记忆：能保存项目规则、历史观察、最近决策或简化会话轨迹。
- 配置系统：通过配置声明工作区、最大步数、允许命令、阻止规则、模型 provider 等。

### 2.2 重点维度选择

课程要求六个维度都有可运行的最低实现，但必须**选择其中一个维度深入实现**作为主要贡献。

本项目选择 **治理护栏** 作为 main contribution。理由：

- 护栏的实现天然是"代码机制而非提示词机制"，最符合课程 §A.4 的判定标准。
- 分层护栏（静态匹配 → 正则白名单 → HITL 状态机）每层都可独立单测，不依赖真实 LLM。
- 面试辨识度高——"我写了一个三层拦截系统，能确定性地阻止危险命令"比"我做了上下文管理"有更强的故事性。
- SWE-agent 的护栏只有一层 blocklist，本项目加入 HITL 状态机和正则白名单是其直接改进点。

反馈闭环作为**次要深入维度**——做到多验证器链 + 3 轮重试，但不作为 main contribution 来论述。其余四个维度（决策循环、工具、记忆、配置）保持可运行的最低实现。

### 2.3 禁止事项

课程明确要求交付物不能寄生于现成 agent 框架。允许使用底层 API 或库，但不能用现成 agent loop 代替自己的实现。

允许：

- OpenAI-compatible / DeepSeek / Qwen 等单次对话补全 API。
- HTTP 客户端、JSON schema、Pydantic、pytest、FastAPI、Docker 等基础库。
- Superpowers、OpenCode、Claude Code 等作为开发工具。

不允许把以下内容作为项目核心：

- LangChain `AgentExecutor`。
- AutoGen / CrewAI / LlamaIndex agent runner。
- Claude Code / OpenCode 自带 agent loop。
- 只写 prompt 或配置文件来冒充治理、记忆、反馈机制。

### 2.4 机制必须可确定性测试

A 类项目最重要的判定标准是：

```text
移除真实 LLM 后，核心机制还能不能用 mock / stub LLM 进行确定性单元测试。
```

因此项目必须能用 MockLLM 证明：

- 工具分发能按动作类型调用正确工具。
- 危险命令或危险路径会被 guardrail 拦截。
- 测试失败信息能作为 observation 回灌给 agent。
- agent 收到失败反馈后能进入下一步修正。
- 达到成功、失败或最大步数时能正确停止。

### 2.5 过程与文档交付

课程不只检查代码，也检查工程过程。必须交付：

- `SPEC.md`：设计文档。
- `PLAN.md`：实现计划。
- `SPEC_PROCESS.md`：需求和计划生成过程记录。
- `AGENT_LOG.md`：每个 task 的 agent 使用、prompt、输出、人工干预、commit hash。
- `REFLECTION.md`：1500-2500 字反思报告。
- `README.md`：项目介绍、安装、运行、分发、安全边界、key 配置。
- CI 配置和执行记录。
- 分发产物：Docker / 二进制 / 包管理器至少一种。
- 在线部署 URL：老师可通过 WebUI 检查项目。

### 2.6 GitHub、CI/CD 与在线检查要求

老师要求使用 GitHub 实现持续集成记录，并部署到网上提供 URL。

因此推荐采用：

- GitHub 仓库作为主仓库。
- GitHub Actions 作为主 CI。
- Docker 作为分发方式。
- Render / Railway / Fly.io 作为 WebUI 部署平台。
- README 中提供 GitHub Actions 页面和线上 WebUI URL。

课程通用文件中还提到 `.gitlab-ci.yml` 和 `unit-test` job。如果最终老师坚持 GitHub，可以以 GitHub Actions 为主；为兼容书面要求，也可以额外保留一个 `.gitlab-ci.yml`，其中包含 `unit-test` job。

## 3. 参考项目调研结论

已有调研文件：`reference_projects_analysis.md`。

### 3.1 主参考：SWE-agent / mini-SWE-agent

适合作为主参考。

借鉴点：

- agent 主循环的基本结构：query -> parse -> execute -> observe -> repeat。
- 模型层、环境层、agent 层的分离。
- 轨迹记录和 observation 回灌。
- mock / predetermined model 的测试方式。

本项目取舍：

- 不追求 SWE-bench 高分。
- 不复刻完整 SWE-agent。
- 保留 mini harness 思路，重点实现课程要求的可测试治理和反馈闭环。

### 3.2 进阶参考：AutoCodeRover

借鉴点：

- 先定位上下文，再生成 patch。
- 不把整个仓库粗暴塞给 LLM。

本项目取舍：

- 只实现轻量 `list_files`、`search_text`、`read_file`。
- 不做完整 AST 分析和大规模代码定位。

### 3.3 对照参考：Agentless

借鉴点：

- coding problem 不一定都要完全自由的多轮 agent。
- localization -> repair -> validation 的 pipeline 很有工程稳定性。

本项目取舍：

- 因课程 A 类要求实现 harness 主循环，本项目保留 agent loop。
- 但将测试验证、护栏拦截、动作解析做成确定性模块，而不是交给 LLM 自由发挥。

### 3.4 背景参考：ChatDev

借鉴点：

- 多 agent 软件开发协作流程。

本项目取舍：

- 暂不做多 agent。
- 避免项目范围膨胀，先把单 agent harness 做扎实。

### 3.5 缝合参考：Claude Code / Aider 的机制借鉴

借鉴点：

- Claude Code 的 hooks 系统——PreToolUse / PostToolUse 拦截点，在工具执行前后注入确定性逻辑。
- Claude Code 的权限分层——deny 优先于 allow，即使 allow 更具体。
- Aider 的 lint + test + 3 轮重试——每次编辑后自动运行校验器，失败信息回灌给 LLM。
- Claude Code 的上下文压缩（compaction）——达到窗口上限前用规则生成摘要，保留最近 N 轮原始消息。

本项目取舍：

- 护栏缝合 Claude Code 的分层拦截思路（第1层静态匹配 → 第2层正则白名单 → 第3层 HITL 状态机）。
- 反馈闭环缝合 Aider 的多验证器链思路（lint → typecheck → test，失败自动回灌）。
- 记忆缝合 Claude Code 的 compaction 思路（近期原始消息 + 远期规则摘要）。
- 不做 hooks 插件系统（复杂度超范围），但护栏的 HITL 拦截点在概念上和 PreToolUse hook 等价，面试时可以讲。

## 4. 本项目初步定位

暂定项目名：

```text
SafeSWE-Lite
```

一句话定义：

```text
SafeSWE-Lite 是一个受 SWE-agent / mini-SWE-agent 启发的轻量级 Coding Agent Harness。
它通过 JSON Action Protocol 驱动文件和命令工具，使用确定性 guardrail 拦截危险动作，
并通过测试反馈闭环让 agent 在 MockLLM 或真实 LLM 下完成小型代码修复任务。
```

## 5. 推荐展示形态

### 5.1 核心展示场景

主 demo：

```text
修复一个 sample project 里的 failing test。
```

示例流程：

1. 用户在 WebUI 或 CLI 中选择 `fix_bug` demo。
2. Harness 初始化 sample workspace。
3. MockLLM 第一步读取失败测试或源文件。
4. Harness 执行工具并回灌 observation。
5. MockLLM 写入一个修复。
6. Harness 运行测试。
7. 如果测试失败，失败信息回灌给 MockLLM。
8. MockLLM 根据反馈再次修复。
9. 测试通过后 agent 输出 finish。
10. WebUI 展示完整 action / observation trace。

辅助 demo：

```text
危险动作拦截。
```

示例流程：

1. MockLLM 输出 `run_command: rm -rf /` 或读取 `.env`。
2. Guardrail 在执行前拦截。
3. WebUI 展示 blocked action、policy rule、reason。
4. 测试用例断言该动作不会被执行。

### 5.2 展示界面

项目应同时提供：

- CLI：适合本地开发、测试和简历讲解。
- WebUI：适合老师通过线上 URL 检查。

WebUI 最小功能：

- 选择 demo：`fix failing test` / `blocked dangerous action`。
- 选择模式：`mock`。本地开发可通过配置启用 `real LLM`，线上部署默认禁用真实 LLM，避免课程检查时触发付费调用或凭据风险。
- 运行 agent。
- 展示每一步 action、observation、guardrail 决策、最终状态。
- 展示本次运行的 trace JSON。

### 5.3 不做的范围

为控制风险，第一版不做：

- 多 agent 协作。
- 大规模 SWE-bench 自动评测。
- 复杂 IDE 插件。
- 浏览器自动操作。
- 自研容器沙箱。
- 复杂向量数据库记忆。

这些可作为后续扩展写进 README 或 REFLECTION。

## 6. 初步模块边界

推荐文件结构：

```text
safe-swe-lite/
  README.md
  SPEC.md
  PLAN.md
  SPEC_PROCESS.md
  AGENT_LOG.md
  REFLECTION.md

  pyproject.toml
  Dockerfile
  .env.example
  .gitignore

  .github/
    workflows/
      ci.yml

  src/
    safe_swe_lite/
      agent/
        loop.py
        actions.py
        protocol.py
      llm/
        base.py
        mock.py
        openai_compatible.py
      tools/
        dispatcher.py
        read_file.py
        write_file.py
        run_command.py
        search.py
      guardrails/
        policy.py
        checker.py
      feedback/
        test_runner.py
        observation.py
      memory/
        store.py
      cli.py
      web/
        app.py
        static/
          index.html
          style.css
          app.js

  tests/
    test_agent_loop.py
    test_action_protocol.py
    test_tool_dispatcher.py
    test_guardrails.py
    test_feedback_loop.py
    test_memory.py
    test_mock_demo.py

  examples/
    sample_project/
    tasks/
      fix_bug.json
      blocked_dangerous_action.json
```

## 7. 当前建议

当前最稳的项目策略是：

```text
主贡献（深入）：治理护栏 —— 三层拦截 + HITL状态机
次要深入：反馈闭环 —— 多验证器链 + 3轮重试
最低实现：决策循环、工具分发、上下文记忆、配置系统
主场景：修复 failing test。
展示形式：CLI + WebUI。
分发方式：Docker。
CI/CD：GitHub Actions + Render/Railway/Fly.io 自动部署。
开发流程：Superpowers + TDD + 小 task + 高频 commit + PR 合并。
```

这个方案的优点：

- 完全符合 A 类 Coding Agent Harness。
- 可以用 MockLLM 做确定性测试，满足课程硬性要求。
- 有线上 WebUI，方便老师检查。
- 有 GitHub Actions 记录，满足 CI 要求。
- 可以在简历中讲清楚参考 SWE-agent，但不是简单复刻。

## 8. 工程工具链与运行路径

### 8.1 技术选型总览

```
┌─────────────────────────────────────────────────┐
│                  分发 & 部署                      │
│  Docker · Render · GitHub Actions               │
├─────────────────────────────────────────────────┤
│                  开发框架 & 方法                   │
│  Superpowers · pytest · ruff · mypy             │
├─────────────────────────────────────────────────┤
│                  Python 核心                      │
│  Python 3.11+ · litellm · FastAPI · Pydantic    │
├─────────────────────────────────────────────────┤
│                  协作 & 版本                       │
│  Git · GitHub · git worktree                    │
├─────────────────────────────────────────────────┤
│                  安全 & 凭据                       │
│  keyring · python-dotenv · .gitignore           │
└─────────────────────────────────────────────────┘
```

### 8.2 逐层选型与理由

**协作 & 版本：**

| 工具 | 用途 | 选型理由 |
|---|---|---|
| Git + GitHub | 版本控制、PR 工作流、commit 历史 | 课程硬性要求 |
| git worktree | 每个独立 task 隔离开发 | 课程硬性要求 |

**Python 核心：**

| 工具 | 用途 | 选型理由 |
|---|---|---|
| Python 3.11+ | 运行环境 | `pyproject.toml` 管理元数据、依赖、入口点 |
| litellm | 统一 LLM API 调用层 | 与 SWE-agent 一致，一个接口兼容 OpenAI / DeepSeek / Qwen / Anthropic |
| FastAPI + uvicorn | WebUI 后端 | 自带 async、自动 OpenAPI doc、Pydantic 原生集成 |
| Pydantic | Action Protocol 类型校验 + 配置模型 | 课程要求 JSON Action Protocol，Pydantic 做 schema 校验最合适 |

**开发框架 & 方法：**

| 工具 | 用途 | 选型理由 |
|---|---|---|
| Superpowers | 全流程管理（brainstorming → plan → TDD → review） | 课程硬性要求 |
| pytest | 单元测试 + mock LLM 确定性测试 | Python 生态标准 |
| ruff | lint + 格式化 | 比 pylint 快 10-100 倍，CI 里不浪费时间 |
| mypy | 静态类型检查 | 反馈闭环三个校验器之一：ruff → mypy → pytest |

**分发 & 部署：**

| 工具 | 用途 | 选型理由 |
|---|---|---|
| Docker | 容器分发 | 课程要求的分发方式之一，单条 `docker build` + `docker run` 一键启动 |
| Render | WebUI 线上部署 | 免费额度够用（750h/月），自动连 GitHub 拉 Dockerfile 构建部署，无需手动配服务器 |
| GitHub Actions | CI/CD | 每次 push/PR 自动跑 unit-test、lint、docker-build |

**安全 & 凭据：**

| 工具 | 用途 | 选型理由 |
|---|---|---|
| keyring | 操作系统级凭据存储 | Windows Credential Manager / macOS Keychain，比纯 .env 更安全 |
| python-dotenv | `.env` 文件加载 | 兜底方案，兼容无 GUI 环境或 CI |
| .gitignore + .dockerignore | 防止凭据泄露 | `.env`、key 文件绝不进仓库或镜像 |

### 8.3 三种运行路径

```
你写代码                   别人用                     老师看
┌──────────┐     ┌──────────────────┐     ┌──────────────────┐
│ pip      │     │ git clone        │     │ 浏览器打开 URL    │
│ pytest   │ ──→ │ docker build     │ ──→ │ 点按钮看 demo    │
│ ruff     │     │ docker run       │     │ trace 动画展示   │
│ localhost│     │ localhost:8000   │     │ onrender.com     │
└──────────┘     └──────────────────┘     └──────────────────┘
   开发态             本地分发态              远端部署态
```

**路径一：本地开发（你）**

不依赖 Docker，直接 pip 装依赖，写完代码立刻跑测试，迭代速度快：

```bash
pip install -e ".[dev]"
pytest -q
python -m safe_swe_lite web   # 本地启动 WebUI 调试
```

**路径二：本地分发（别人 clone 后）**

不需要装 Python、不需要配环境、不需要 pip install。Dockerfile 自包含：Python 3.11、所有依赖、harness 源码、sample project 全打包：

```bash
git clone https://github.com/<user>/safe-swe-lite
cd safe-swe-lite
docker build -t safe-swe-lite .
docker run -p 8000:8000 safe-swe-lite
```

支持两种启动模式：

```bash
docker run safe-swe-lite              # 启动 WebUI（默认）
docker run safe-swe-lite cli fix_bug  # 跑 CLI demo（面试用）
```

**路径三：远端部署（老师在线看）**

GitHub push main → Render 自动拉 Dockerfile 构建 → 分配公开 URL：

```
https://safe-swe-lite.onrender.com
```

不需要 SSH、不需要配 nginx、不需要管进程。免费额度 750h/月。线上环境默认只允许 mock 模式，不接真实 LLM——不花钱、不泄露 key、结果确定可重复。

### 8.4 装机清单

用户在新机器上跑 SafeSWE-Lite 需要的唯一前提：

```text
Python 3.11+          （本地开发用）
Git                   （本地开发用）
Docker Desktop        （分发 / 部署用）
```

其余依赖全部在 `pyproject.toml` 或 Dockerfile 里声明，一条命令装完。

### 8.5 展示形态

**WebUI（老师在线检查）：**

一个单页，三个区域：

```
┌──────────────────────────────────────────────┐
│  SafeSWE-Lite                                │
│  ───────────────────────────────────────     │
│  [Run: Fix Bug Demo]  [Run: Blocked Demo]    │
│                                              │
│  ┌─ Trace ────────────────────────────────┐  │
│  │ Step 1: read_file("src/auth.py")       │  │
│  │   → lines 1-45                         │  │
│  │ Step 2: run_command("pytest -q")       │  │
│  │   → FAILED test_login                  │  │
│  │ Step 3: edit_file(...)                 │  │
│  │   → patched line 23                    │  │
│  │ Step 4: run_command("pytest -q")       │  │
│  │   → 4 passed                           │  │
│  │ Step 5: submit("bug fixed")            │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  [Download trace JSON]                       │
└──────────────────────────────────────────────┘
```

**CLI（面试演示）：**

终端一条命令，输出完整 trace，比点网页更有说服力：

```bash
docker run safe-swe-lite cli fix_bug --mock
```

两个 demo 与课程评分点的对应：

| Demo | 演示内容 | 对应评分点 |
|---|---|---|
| Fix Bug | MockLLM 修复 failing test 全流程 | 反馈闭环 + 主循环 + 工具分发 + 记忆 |
| Blocked | 危险命令被护栏拦截 | 三层护栏 + HITL 状态机 |

## 9. 课程额外要求的提醒

### 8.1 SPEC 额外章节：领域与机制设计（§A.5）

课程要求 SPEC 额外加入「领域与机制设计」章节，必须回答：

- coding 领域的反馈信号、危险动作、所需工具、记忆需求分别是什么？
- 选择哪个维度作为重点？为什么？
- 这些机制将如何编码实现？

写 SPEC 时不能漏掉这一节。

### 8.2 机制演示的三个硬性要求（§A.6）

课程要求提交三个确定性的机制演示（mock LLM 下运行）：

| 演示 | 要求 |
|---|---|
| ① 护栏拦截 | MockLLM 输出 `rm -rf /`，guardrail 拦截，断言动作未执行 |
| ② 反馈闭环 | 注入一次测试失败，agent 收到失败信息后改变下一步动作 |
| ③ 重点维度行为 | 护栏分层拦截的完整链路：静态→正则→HITL |

这三个演示必须在 `tests/` 中有对应的测试用例或可重复运行的脚本。

### 8.3 凭据安全（§3.1）

凭据安全是必做项，不是可选项：
- key 绝不硬编码、不提交 Git、不写进日志
- 至少实现一种安全存储（推荐 keyring + .env 组合）
- 首次运行引导用户安全录入 key
- SPEC 中写清凭据威胁模型

### 8.4 配置与记忆的最低实现

虽然主贡献选了护栏，但配置和记忆两个维度也需要可运行的最低实现：

- 配置：YAML 配置文件，声明 workspace、max_turns、allow/block/ask 规则、model provider
- 记忆：消息列表 + 分级上下文（近期原始消息 + 远期规则摘要），持久化到 JSON 文件
