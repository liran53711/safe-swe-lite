# SafeSWE-Lite

A lightweight coding agent harness inspired by [SWE-agent](https://github.com/princeton-nlp/SWE-agent) (NeurIPS 2024), with deterministic layered guardrails and a test-feedback self-correction loop. Built from scratch — no LangChain, no AutoGen, no agent frameworks.

**All core mechanisms are verifiable with mock-LLM unit tests — no network, no API key, fully deterministic.**

## What it does

```
用户任务 → Agent 主循环 → LLM 决策（mock 或真实）
                ↓
      L1 静态黑名单 → L2 范围围栏 → L3 HITL → L4 代码扫描
                ↓
     7 个结构化工具（read/write/edit/run/search/list/submit）
                ↓
     校验器链（pytest）→ 3 轮有界重试 → 反馈回灌
```

- **Main contribution: 四层护栏** — L1 任意位置正则黑名单（三轮对抗性测试硬化）、L2 workspace 范围围栏（symlink/跨盘符/尾随点防护）、L3 HITL 状态机（真状态机，终态记忆）、L4 AST 代码内容扫描（import 别名解析）
- **Secondary contribution: 反馈闭环** — 确定性校验器 + 3 轮有界重试，失败信息格式化为可执行修复指令回灌
- **Memory**: 评分制分级上下文（护栏拦截=10 分，安装日志=1 分），非时间序裁剪

## Installation

```bash
git clone https://github.com/liran53711/safe-swe-lite
cd safe-swe-lite
pip install -e ".[dev,web]"     # 开发 + WebUI
# 真实 LLM 模式额外需要：
pip install -e ".[llm]"
```

Requirements: Python 3.11+.

## Running

### CLI（mock 模式，零依赖）

```bash
# 修复 bug 演示：真实 pytest 失败 → 编辑 → 转绿 → submit
safe-swe-lite run examples/tasks/fix_bug.json

# 危险动作拦截演示
safe-swe-lite run examples/tasks/blocked_dangerous_action.json

# 真实 LLM 模式（需先配置 key）
safe-swe-lite run examples/tasks/fix_bug.json --real
```

### WebUI

```bash
safe-swe-lite web
# 打开 http://localhost:8000
```

两个 demo 按钮：Fix Bug（反馈闭环全流程）和 Blocked（护栏拦截）。全部 mock 模式，线上环境强制 mock-only。

### Docker

```bash
docker build -t safe-swe-lite .
docker run -p 8000:8000 safe-swe-lite          # WebUI
docker run safe-swe-lite run examples/tasks/fix_bug.json  # CLI（覆盖 CMD）
```

镜像自包含 Python 3.11 + 依赖 + 源码 + sample project。无需 Docker 的用户可走 pip 路径。

## Testing

```bash
pytest -q          # 148 tests，全部离线（MockLLM 驱动）
ruff check src tests examples
```

CI（GitHub Actions）在每次 push/PR 运行三个 job：`unit-test`（pytest）、`lint`（ruff）、`docker-build`（含运行态 smoke 测试）。

## 目录结构

```
src/safe_swe_lite/
├── agent/          # 主循环、Action Protocol
├── llm/            # Model 抽象（MockLLM / LiteLLMProvider）
├── tools/          # 7 工具 + Dispatcher
├── guardrails/     # 四层护栏 + GuardrailChain
├── feedback/       # 校验器 + 3 轮重试
├── memory/         # 评分制分级上下文
├── config/         # YAML 配置（fail-fast 校验）
├── cli.py          # run / web / auth
└── web/            # FastAPI + 静态页
examples/
├── sample_project/ # 含一个真 bug 的示例项目
└── tasks/          # 两个 demo 任务文件
tests/              # 148 tests
```

## 安全边界

### 护栏四层（各层均有文档化边界）

| 层 | 机制 | 文档化边界 |
|---|---|---|
| L1 | 任意位置正则黑名单 + rm 语义检查 + radare2 payload 转义检查 + .env 保护 | grep/sed 读 .env、eval 包装器、深度混淆委托后续层 |
| L2 | workspace 范围围栏（resolve + is_relative_to） | 符号链接、跨盘符、尾随空格/点均有测试 |
| L3 | HITL 状态机（软复核层） | 前缀匹配可被空格/引号绕过——硬安全由 L1/L4 兜底 |
| L4 | AST 代码内容扫描（含 import 别名解析） | 赋值别名（`f = subprocess.run`）是静态分析经典局限 |

### 凭据（真实 LLM 模式）

- **威胁模型**：key 绝不硬编码、不进 Git、不写日志；keyring（OS 钥匙串）优先；`.env` 为明文兜底（已被 .gitignore 排除）；litellm 错误消息可能含 key 末 4 位（供应商行为）
- **录入**：`safe-swe-lite auth`（隐藏输入）
- **更新**：重跑 `auth`
- **清除**：OS 凭据管理器手动删除（Windows：凭据管理器 → Windows 凭据 → safe-swe-lite）
- **回退链**：keyring → SAFE_SWE_LITE_API_KEY → OPENAI_API_KEY → ANTHROPIC_API_KEY

### 线上部署（mock-only）

线上环境（`SAFE_SWE_LITE_ALLOW_REAL_LLM` 默认 false）强制 mock 模式：无 key、无付费调用、结果确定可重复。

## 已知限制

- embedding 检索层（SPEC 可选层）默认关闭，当前为评分制过滤
- L3 的 HITL 在 CLI/WebUI 无交互批准通道（auto_approve=True），人工批准留待未来
- 单槽 HITL 记忆（只记一个待决动作），多动作队列需升级
- 本机开发时无 Docker 验证环境，镜像构建由 CI 的 docker-build job 验证

## 在线部署

Render：`https://safe-swe-lite.onrender.com`（部署说明见下方）

## CI/CD

- GitHub Actions：[Actions 页面](https://github.com/liran53711/safe-swe-lite/actions)
- 三个 job：unit-test / lint / docker-build（含 smoke）

## 第三方代码许可引用

本项目为课程项目，未复制任何第三方源码。架构设计参考以下项目（学习其设计，独立实现）：

- [SWE-agent](https://github.com/princeton-nlp/SWE-agent)（MIT License）— agent 主循环结构、护栏三匹配模式
- [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent)（MIT License）— Model/Environment 协议、MockLLM 测试模式
- [Aider](https://github.com/Aider-AI/aider)（Apache-2.0）— lint/test 反馈闭环设计
- [AutoCodeRover](https://github.com/AutoCodeRoverSG/auto-code-rover)（MIT License）— 上下文定位原则
- [Agentless](https://github.com/OpenAutoCoder/Agentless)（MIT License）— 分层定位与确定性验证思想

## 开发过程

本项目按 Superpowers 全流程开发：brainstorming → SPEC/PLAN → 冷启动验证（Codex CLI 独立验证 SPEC）→ 18 个 task 的 subagent 驱动实现 → 每个 task 双阶段评审（spec 合规 + 代码质量）。完整记录见 `AGENT_LOG.md`、`SPEC_PROCESS.md`、`PLAN.md`。
