# SPEC: SafeSWE-Lite

> 版本：1.0
> 日期：2026-08-15
> 项目类型：AI4SE 期末项目 A 类 · Coding Agent Harness

## 1. 问题陈述

### 1.1 要解决的问题

现代 LLM（如 Claude、GPT-4）已经能写出高质量的单段代码，但**能写代码 ≠ 能完成软件工程任务**。一个真实的修复任务需要：理解项目结构 → 定位相关代码 → 修改 → 运行测试 → 失败后修正 → 循环直到通过。这个"循环"需要工程系统来支撑——LLM 只负责每一步的决策，其余（工具执行、安全拦截、结果校验、上下文管理）必须由代码完成。

**SafeSWE-Lite 解决的问题：** 如何把一个只会"下一步做什么"的 LLM，封装成一个能稳定、安全、可验证地完成小型代码修复任务的系统。

### 1.2 目标用户

| 用户 | 场景 |
|---|---|
| 课程教师 / 助教 | 通过 WebUI 在线检查 harness 机制演示（mock 模式下确定性运行） |
| 面试官 / 技术同行 | 通过 README + CLI 理解 harness 架构，验证机制可测试性 |
| LLM 应用开发者 | 参考本项目学习如何从零实现 agent harness 内核（不依赖 LangChain 等框架） |

### 1.3 为什么值得做

- **教育价值**：课程命题是"当 LLM 能完成大部分编码时，工程师的价值在 harness 这层工程"。本项目是对此命题的第一手实践。
- **对照价值**：以 SWE-agent（NeurIPS 2024）为基线，在其单层 blocklist 护栏之上实现分层护栏（静态 → 正则 → HITL）+ 代码内容扫描 + 范围围栏，是可直接讨论的改进点。
- **面试辨识度**：所有核心机制均可用 mock LLM 做确定性单测——这是"编码了机制"与"只写了提示词"的硬性分界。

## 2. 用户故事

> 遵循 INVEST 原则（Independent, Negotiable, Valuable, Estimable, Small, Testable）

| # | 用户故事 | 验收要点 |
|---|---|---|
| US-1 | 作为课程教师，我在 WebUI 点击"Fix Bug Demo"按钮，就能看到 agent 在 mock LLM 驱动下逐步修复 failing test 的完整 trace，以便检查反馈闭环机制是否真实实现 | trace 展示每一步 action / observation / 校验结果；全程无网络请求 |
| US-2 | 作为课程教师，我在 WebUI 点击"Blocked Demo"按钮，就能看到 agent 尝试执行 `rm -rf /` 时被护栏拦截，trace 中明确标注拦截层级和原因 | 拦截是确定性代码行为，重复运行 100 次结果一致 |
| US-3 | 作为开发者，我运行 `pytest` 一条命令就能跑完全部单元测试，且测试不依赖网络和真实 LLM，以便 CI 验证 harness 核心机制 | 全部测试用 MockLLM；`pytest -q` 离线通过 |
| US-4 | 作为用户，我在一台新机器上 `git clone` + `docker build` + `docker run` 三条命令就能启动 SafeSWE-Lite 的 WebUI，不需要安装 Python 环境 | Docker 镜像自包含所有依赖 |
| US-5 | 作为使用真实 LLM 的开发者，我首次运行 CLI 时被引导安全录入 API key，key 不落盘明文、不进 Git、不出现在日志中 | key 存储在系统钥匙串；`.env` 仅作 fallback 且被 gitignore |
| US-6 | 作为研究者，我写 `MockLLM(outputs=[...])` 一行代码就能编排一段确定性的 agent 对话，以便复现任意场景 | MockLLM 按序播放预编程回复，与真实 LLM 实现同一接口 |
| US-7 | 作为面试者，我在终端运行 `docker run safe-swe-lite cli fix_bug --mock` 就能演示完整 harness 运行过程 | CLI 输出结构化 trace，含护栏决策和校验结果 |

## 3. 功能规约

### 3.1 模块总览

```
src/safe_swe_lite/
├── agent/          # 主循环、动作协议
├── llm/            # LLM 抽象层（base/mock/litellm）
├── tools/          # 7 个工具 + 分发器
├── guardrails/     # 四层护栏（主贡献）
├── feedback/       # 校验器链 + 重试循环
├── memory/         # 分级上下文 + 评分 + embedding
├── config/         # YAML 配置加载与校验
├── cli.py          # 命令行入口
└── web/            # FastAPI + 静态 WebUI
```

### 3.2 Agent 主循环（决策封装）

**输入**：任务描述（字符串）、配置（Config）
**行为**：

```
初始化消息列表 → 加 system + user 消息
while 未停机:
    1. memory.assemble() 组装上下文（分级裁剪 + 检索）
    2. model.query(context) 调用 LLM（或 MockLLM）
    3. parse_action(response) 解析动作（Pydantic 校验）
    4. 若 action == submit → 停机，返回结果
    5. guardrail.check(action) → 拦截则记录并回灌 blocked observation
    6. tools.execute(action) 执行动作
    7. 若 action 是 write_file/edit_file → 触发校验器链 + 有界重试
    8. memory.record(turn) 记录本轮
    9. 检查步数/时间/花费上限
```

**输出**：`{"exit_status": "submitted" | "max_steps_exceeded" | "time_exceeded" | ..., "submission": str, "trace": [...]}`

**边界条件**：
- 步数上限（默认 50）、时间上限（默认 600s）、花费上限可配置
- LLM 输出格式错误：连续 3 次 → 停机（`RepeatedFormatError`）
- 工具执行超时：单命令默认 30s，超时 SIGKILL 整个进程组

**错误处理**：所有异常路径统一为"构造 exit 消息 → break"，与 mini-swe-agent 的异常驱动停机一致。

### 3.3 动作协议（Action Protocol）

**LLM 与 harness 之间的唯一接口**是 JSON 动作：

```json
{
  "action": "read_file",
  "parameters": {"path": "src/auth.py", "offset": 0, "limit": 50}
}
```

7 个工具（Action 由 Pydantic 模型定义；参数级校验由各工具函数在调用时自行处理）：

| 工具 | 参数 | 说明 |
|---|---|---|
| `read_file` | path, offset?, limit? | 读文件，默认最多 2000 行 |
| `write_file` | path, content | 创建或覆盖文件 |
| `edit_file` | path, old_string, new_string | 精确查找替换，old_string 不唯一则报错 |
| `run_command` | command, timeout? | 执行 shell 命令，返回 exit_code/stdout/stderr |
| `search_pattern` | pattern, path?, glob? | ripgrep 正则搜索，返回文件:行号:内容 |
| `list_files` | path?, glob? | 列目录，按 mtime 排序 |
| `submit` | result | 提交结果并停机 |

**边界条件**：
- 所有文件操作路径必须落在 workspace 内（由 scope fence 强制）
- `edit_file` 的 old_string 必须唯一匹配
- `run_command` 超时后返回结构化错误而非崩溃

**错误处理**：LLM 输出无法解析为上述任一动作 → `FormatError` → 回灌格式错误提示 → 重试（最多连续 3 次）。

### 3.4 护栏系统（主贡献）

四层护栏，全部在动作执行前生效：

**L1 静态黑名单（`guardrails/checker.py`）**

- 输入：action（Pydantic 对象）
- 行为：检查命令前缀/精确匹配/正则白名单（吸收 SWE-agent `should_block_action` 的三层匹配）
- 输出：`GuardrailDecision(blocked: bool, layer: int, reason: str)`
- 默认规则：拦截 `rm -rf /`、`sudo`、`chmod 777`、`git push --force`、读 `.env`、`curl | sh` 等

**L2 范围围栏（`guardrails/scope_fence.py`）**

- 输入：file 操作类 action（read/write/edit/list/search）
- 行为：路径规范化（resolve）后校验是否在 `config.allowed_dirs` 前缀内；符号链接解析
- 输出：越界即拦截，reason 包含请求路径与允许范围

**L3 HITL 状态机（`guardrails/hitl.py`）**

- 输入：L1/L2 判定为"需确认"的动作（如 `git push`、删除文件、`pip install`）
- 状态机：`NO_INTERVENTION → PENDING_APPROVAL → APPROVED | REJECTED`
- CLI 模式：终端 `y/n` 交互；WebUI 模式：trace 中挂起，等用户在界面点击批准/拒绝
- mock 模式：预编程决策（测试用），不阻塞

**L4 代码内容扫描（`guardrails/code_scanner.py`）**

- 输入：write_file/edit_file 的写入内容
- 行为：用 `ast` 模块解析（Python）或正则（其他语言），扫描禁用符号列表（用户可配置，如 `eval`、`exec`、`subprocess`）
- 输出：命中即拦截，reason 含符号名和行号

**补充层（可选，非 main contribution）**：LLM-as-Judge 风险评分——独立 LLM 调用给动作打风险分。默认关闭。不参与单测（不可确定性测试），仅在 REFLECTION 中讨论其边界。

**验收判据**：移除真实 LLM 后，L1-L4 全部可用 mock 测试验证——直接构造 action 对象传入，断言拦截结果。

### 3.5 反馈闭环（次要深入）

**校验器链**（`feedback/validators.py`）：

```
write_file/edit_file 触发 →
  LintValidator    (ruff check --fix 不启用，仅检测)
  TypeCheckValidator (mypy)
  TestValidator     (pytest -q)
```

三个校验器**链式执行**，结果合并为 `ValidationResult` 列表：

```python
@dataclass
class ValidationResult:
    passed: bool
    validator: str          # "lint" | "typecheck" | "test"
    file: str | None
    line: int | None
    message: str
    context: str | None     # 出错位置周围代码
    details: dict | None    # 校验器特有信息
```

**有界重试循环**：校验失败 → 格式化 ValidationResult 为修复指令回灌 LLM → LLM 修改 → 重新校验，最多 3 轮。3 轮后仍失败 → 最终结果作为 observation 交回主循环（LLM 自主决定换策略或 submit 认输）。

**边界条件**：重试循环内的 LLM 调用不经过护栏豁免——每轮修改都重新走 L1-L4。

### 3.6 记忆与上下文（升级为第二深入维度）

**会话内分级上下文**（`memory/store.py`）：

```
全量消息（轨迹持久化用，不裁剪）
    ↓ assemble()
近 10 轮：原始消息
    ↓
更早轮次：规则压缩摘要（"第N轮：修改 auth.py，lint 通过"）
    ↓
重要性评分过滤：按消息类型打分（测试失败=9，护栏拦截=10，安装日志=1）
    ↓
embedding 检索（可选层）：向量召回被评分误裁的相关历史
```

**评分规则**（纯代码、确定性、可单测）：

| 消息特征 | 分数 |
|---|---|
| 护栏拦截记录 | 10 |
| 测试失败 / 类型错误 | 9 |
| 文件读取（架构级信息） | 5 |
| 测试通过 / 安装日志 | 1 |

**跨会话持久化**（`memory/persistence.py`）：项目约定、最近修改文件列表、错误历史 → `~/.safe-swe-lite/memory.json`。

**Embedding 检索层**（`memory/retrieval.py`）：用 sentence-transformers 本地模型（或可选 API）将历史 observation 向量化，assemble 时用当前任务查询 top-k 相关历史。Embedding 模型固定 seed、离线可用；单测用预计算向量 mock。

### 3.7 配置系统

`config/default.yaml`：

```yaml
workspace: "./examples/sample_project"
max_turns: 50
timeout_seconds: 600
command_timeout: 30

model:
  provider: "mock"            # mock | litellm
  mock_outputs: []            # mock 模式的预编程输出

guardrails:
  blocklist: ["rm -rf /", "sudo", ...]
  blocklist_standalone: [...]
  block_unless_regex: {...}
  allowed_dirs: ["./src", "./tests"]
  require_approval: ["git push", "pip install", ...]
  banned_symbols: ["eval", "exec", ...]

feedback:
  validators: ["lint", "typecheck", "test"]
  max_retries: 3

memory:
  recent_window: 10
  embedding: false            # 可选层开关
```

启动时 Pydantic 校验配置合法性；非法配置报错退出并说明原因。

### 3.8 CLI 与 WebUI

**CLI**（`cli.py`）：

```bash
safe-swe-lite run examples/tasks/fix_bug.json --mock
safe-swe-lite run examples/tasks/blocked_dangerous_action.json --mock
safe-swe-lite web --port 8000
```

**WebUI**（FastAPI + 静态页）：
- `GET /` 单页应用：两个 demo 按钮 + trace 展示区 + guardrail 决策标记 + trace JSON 下载
- `POST /api/demo/fix-bug` 运行 fix bug demo（mock）
- `POST /api/demo/blocked` 运行 blocked demo（mock）
- `GET /api/health` 健康检查
- 线上环境强制 mock 模式（环境变量 `SAFE_SWE_LITE_ALLOW_REAL_LLM=false`）

## 4. 非功能性需求

### 4.1 性能

- mock demo 完整运行 < 5 秒（无网络等待）
- CLI 启动 < 1 秒（导入开销可接受）
- 单命令执行超时上限 30 秒（防卡死）

### 4.2 安全（含凭据威胁模型）

**威胁模型**：

| 威胁 | 对策 |
|---|---|
| API key 硬编码进源码被提交 | 代码审查纪律 + `.gitignore` + CI 扫描 |
| API key 出现在日志/终端 history | key 只经 keyring 读取，日志脱敏 |
| `.env` 明文文件被误提交 | `.env` 进 `.gitignore`；keyring 优先，`.env` 仅 fallback |
| agent 通过工具读取 `.env` | L1 护栏拦截 `.env` 路径读取 |
| agent 越权访问 workspace 外文件 | L2 范围围栏强制 |
| agent 执行危险 shell 命令 | L1 + L3（HITL） |
| WebUI 线上部署被滥用跑真实 LLM | 线上强制 mock 模式环境变量 |

**凭据存储方案**：keyring（Windows Credential Manager / macOS Keychain / Linux Secret Service）为主，`.env` 为 fallback。首次运行 `safe-swe-lite auth` 引导隐藏输入；`safe-swe-lite auth --status` 只显示"已配置/未配置"，不回显明文。

### 4.3 可用性

- 新机器 3 条命令启动（clone / build / run）
- 所有 demo 离线可跑（mock 模式零 API 依赖）
- 错误信息面向开发者：说明"哪个组件、什么错误、怎么修"

### 4.4 可观测性

- trace 是**一等公民**：每步 action / observation / guardrail 决策 / 校验结果均入 trace
- trace 可序列化为 JSON 下载（WebUI）或输出（CLI）
- 轨迹文件持久化到 `output/` 目录，含 agent 配置快照

## 5. 系统架构

### 5.1 组件图

```
┌─────────────────────────────────────────────────────────┐
│                       Agent (agent/loop.py)              │
│                                                          │
│  while not done:                                         │
│    context = memory.assemble()        ┌──────────────┐   │
│    response = model.query(context)    │  Config      │   │
│    action = protocol.parse(response)  │  (YAML)      │   │
│    if guardrail.blocked(action): ─────→│ 注入各组件    │   │
│       record + continue               └──────────────┘   │
│    result = tools.execute(action)                         │
│    if action is write:                                    │
│       feedback = validators.run(path)  ← retry ≤ 3 轮     │
│    memory.record(turn)                                    │
└───────┬──────────────┬──────────────┬────────────────────┘
        │              │              │
┌───────▼──────┐ ┌─────▼─────┐ ┌──────▼───────┐
│ Model 抽象   │ │ Guardrail │ │  Tools       │
│ (llm/)       │ │ (guardr/) │ │  (tools/)    │
│              │ │           │ │              │
│ MockLLM      │ │ L1 黑名单  │ │ read_file    │
│ LiteLLM      │ │ L2 围栏    │ │ write_file   │
│ (同接口)     │ │ L3 HITL    │ │ edit_file    │
│              │ │ L4 扫描    │ │ run_command  │
└──────────────┘ │            │ │ search       │
                 └────────────┘ │ list_files   │
                                │ submit       │
                                └──────┬───────┘
                                ┌──────▼───────┐
                                │ Feedback     │
                                │ (feedback/)  │
                                │ ruff/mypy/   │
                                │ pytest 链    │
                                └──────────────┘
```

### 5.2 数据流（一次完整 step）

```
LLM 回复 ──→ protocol.parse ──→ Action 对象
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
               L1 黑名单      L2 范围围栏    L4 内容扫描
                    │              │              │
                    └──────┬───────┘              │
                           ▼                      │
                    全部放行？ ──否──→ L3 HITL ──→ 拦截/批准
                           │是
                           ▼
                    tools.execute
                           │
                           ▼
               write/edit 动作？ ──是──→ 校验器链 ──→ 失败？ ──→ 重试循环(≤3)
                           │否
                           ▼
                    memory.record + trace 追加
                           │
                           ▼
                    下一轮 LLM 调用
```

### 5.3 外部依赖

| 依赖 | 用途 | 可选性 |
|---|---|---|
| litellm | 真实 LLM API 调用 | mock 模式不需要 |
| FastAPI + uvicorn | WebUI 后端 | CLI-only 使用不需要 |
| ripgrep (rg) | search_pattern 工具 | 可降级为 Python 正则 |
| ruff / mypy / pytest | 反馈闭环校验器 | 可配置关闭单个 |
| sentence-transformers | embedding 检索层 | 可选层，默认关闭 |
| keyring | 凭据安全存储 | 仅真实 LLM 模式需要 |

## 6. 数据模型

### 6.1 Action

```python
class Action(BaseModel):
    name: str                      # 7 工具之一
    parameters: dict               # 工具特定参数（Pydantic 校验）
```

### 6.2 TraceEvent

```python
class TraceEvent(BaseModel):
    turn: int
    kind: str                      # "llm_call" | "action" | "observation" | "guardrail" | "validation" | "exit"
    data: dict                     # 具体内容
    timestamp: float
```

### 6.3 GuardrailDecision

```python
class GuardrailDecision(BaseModel):
    blocked: bool
    layer: int                     # 1-4，0 表示放行
    reason: str
    hitl_state: str | None         # "pending" | "approved" | "rejected"
```

### 6.4 ValidationResult（见 3.5）

### 6.5 消息与记忆

```python
class Message(BaseModel):
    role: str                      # system | user | assistant | observation
    content: str
    extra: dict                    # actions, cost, tags 等
    tags: list[str]                # keep_output / remove_output 等
    score: int                     # 重要性评分（memory 层计算）
```

**约束**：trace 与 messages 的关系——messages 是全量历史（轨迹源），trace 是给人和 WebUI 看的精简事件流。

## 7. 凭据与分发设计

### 7.1 凭据

- **存储**：keyring 优先；`.env` 文件（gitignored）作为 fallback；环境变量只读不入库
- **录入**：`safe-swe-lite auth` 命令，`getpass` 隐藏输入，不落 shell history
- **查看**：`safe-swe-lite auth --status` 只显示配置状态
- **更新/清除**：`safe-swe-lite auth --update` / `--clear`
- **威胁模型**：见 §4.2

### 7.2 分发

**主分发形态：Docker 容器**

```bash
docker build -t safe-swe-lite .
docker run -p 8000:8000 safe-swe-lite              # WebUI
docker run safe-swe-lite cli fix_bug --mock        # CLI
```

镜像内容：Python 3.11 + 依赖 + 源码 + sample project。不含任何 key。

**次分发形态：pip 可编辑安装**（开发者使用）

```bash
pip install -e ".[dev]"
safe-swe-lite run examples/tasks/fix_bug.json --mock
```

### 7.3 线上部署

Render 托管：GitHub push main → 自动构建 Dockerfile → 分配 `https://safe-swe-lite.onrender.com`。线上环境强制 mock 模式（无 key、无付费调用、确定性行为）。

## 8. 技术选型与理由

| 决策 | 选择 | 理由 |
|---|---|---|
| 语言 | Python 3.11+ | 与 SWE-agent 生态一致；ast/ripgrep 绑定成熟；课程不限语言 |
| LLM 调用 | litellm | 一个接口兼容 OpenAI / DeepSeek / Anthropic，与 SWE-agent 相同选型 |
| 数据校验 | Pydantic | Action 协议与配置的运行时类型校验，格式错误即抛可重试异常 |
| Web 框架 | FastAPI + uvicorn | 异步、自动 OpenAPI、静态页托管简单 |
| 测试 | pytest | mock LLM 确定性测试的事实标准 |
| lint | ruff | 比 pylint 快 10-100 倍，CI 时间友好 |
| 类型检查 | mypy | 反馈闭环校验器之一 |
| 搜索 | ripgrep | search_pattern 工具的后端 |
| 凭据 | keyring + dotenv | OS 钥匙串优先，.env 兜底 |
| 分发 | Docker | 课程要求 + 新机器零配置启动 |
| CI | GitHub Actions | 课程要求 + push 自动测试 |
| 部署 | Render | 免费额度、GitHub 自动部署、Dockerfile 原生支持 |
| embedding | sentence-transformers | 可选层，本地离线运行 |

## 9. 验收标准

| # | 功能 | 完成的客观判定 |
|---|---|---|
| AC-1 | 主循环 | `pytest tests/test_agent_loop.py` 通过：MockLLM 编排下正确停机（submit / 步数上限 / 格式错误） |
| AC-2 | 动作协议 | 7 种动作全部可解析；非法动作抛 FormatError 并回灌重试 |
| AC-3 | 护栏 L1 | `guardrail.check(run_command("rm -rf /"))` 返回 blocked，100 次结果一致 |
| AC-4 | 护栏 L2 | `read_file("../../etc/passwd")` 被拦截；`read_file("./src/x.py")` 放行 |
| AC-5 | 护栏 L3 | mock 决策下 HITL 状态机完整走 pending → approved / rejected 路径 |
| AC-6 | 护栏 L4 | `write_file` 内容含 `eval(` 被拦截，reason 含符号名和行号 |
| AC-7 | 反馈闭环 | 注入 1 次测试失败 → agent 收到 ValidationResult → 修改 → 复测通过（机制演示②） |
| AC-8 | 记忆 | 评分函数对 4 类消息返回正确分数；assemble 输出 ≤ 窗口限制 |
| AC-9 | MockLLM | `MockLLM(outputs=[...])` 不联网、按序播放、与真实 LLM 同接口 |
| AC-10 | 机制演示 | 三个演示脚本（§A.6）全部可重复运行且结果确定 |
| AC-11 | CI | GitHub Actions `unit-test` job 在 push 后自动跑 `pytest -q` 且 pass |
| AC-12 | Docker | `docker build && docker run` 后 `curl localhost:8000/api/health` 返回 200 |
| AC-13 | 线上部署 | Render URL 可访问，两个 demo 均可在浏览器运行 |
| AC-14 | 凭据 | 仓库全文搜索无真实 key；`auth --status` 不回显明文 |

## 10. 风险与未决问题

| # | 风险 | 缓解 |
|---|---|---|
| R-1 | embedding 层开发超时 | 默认关闭；规则评分已满足记忆维度要求，embedding 作为可选增强 |
| R-2 | mock demo 与真实 LLM 行为差异大 | mock 演示的价值在机制验证而非任务完成度；README 明确此边界 |
| R-3 | Render 免费实例冷启动慢（首次访问 ~30s） | README 说明；课程检查时预热一次 |
| R-4 | ripgrep 在 Windows 上的可用性 | 提供 Python 正则 fallback；CI 跑 Linux |
| R-5 | HITL 在 mock 模式下的交互设计 | mock 模式用预编程决策（不阻塞）；真实模式才需要人工确认 |
| R-6 | 冷启动验证暴露 SPEC 缺陷 | Phase 0.5 用不同 agent 验证，修订后再开发 |

## 11. 领域与机制设计（课程 §A.5 额外章节）

### 11.1 Coding 领域的四要素

| 要素 | Coding 领域的具体形态 |
|---|---|
| **反馈信号** | 测试通过/失败、lint 错误、类型检查错误、编译错误——客观、确定、可回灌 |
| **危险动作** | 删除文件、`rm -rf`、越权读写（workspace 外）、执行任意下载脚本、推送代码 |
| **所需工具** | 读/写/改文件、搜索代码、列目录、执行命令（跑测试/lint）、提交结果 |
| **记忆需求** | 项目结构认知、已修改文件清单、失败历史、跨会话项目约定 |

### 11.2 重点维度选择：治理护栏

**为什么是护栏**：

1. 护栏是"代码 vs 提示词"分界最清晰的维度——`guardrail.check(action)` 的拦截结果不依赖 LLM 智能，每次调用确定性成立
2. SWE-agent 的护栏只有单层 blocklist，SafeSWE-Lite 的四层（黑名单 → 围栏 → HITL → 内容扫描）是直接可讨论的改进
3. 面试辨识度最高：可当场演示"LLM 想删数据库，我的代码拦住了它"

**如何编码实现**：

- L1：`should_block_action()` 移植 SWE-agent 的三重匹配（前缀/精确/正则白名单）并扩展规则集
- L2：`scope_fence.check()` 用 `Path.resolve()` 规范化路径后前缀匹配，处理符号链接
- L3：`HitlStateMachine` 枚举状态转换，CLI/WebUI/mock 三种决策源实现同一接口
- L4：`code_scanner.scan()` 用 `ast.walk()` 收集调用点，匹配禁用符号表

**测试策略**：每个 layer 一个测试文件，直接构造 action 对象断言拦截结果，不经过真实 LLM。

### 11.3 次要深入维度：反馈闭环

- 校验器链：ruff → mypy → pytest，每个都是独立进程调用、独立解析、独立 ValidationResult
- 有界重试：3 轮上限，之后交回主循环
- 与 Aider 的差异：Aider 单校验器（lint）+ 用户驱动重试；SafeSWE-Lite 三校验器链 + 自动有界重试

### 11.4 各维度最低实现清单

| 维度 | 最低实现 |
|---|---|
| 决策循环 | while + 结构化停机 + 异常驱动 |
| 工具 | 7 工具 + dispatcher 按名分发 |
| 记忆 | 全量消息 + 近10轮原始 + 规则评分 + 远期摘要 |
| 护栏 | 四层（主贡献，见 11.2） |
| 反馈 | 校验器链 + 3 轮重试（见 11.3） |
| 配置 | YAML + Pydantic 校验 |
