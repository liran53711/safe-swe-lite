# AGENT_LOG — SafeSWE-Lite 开发过程记录

> 按时间顺序记录每个 task 的：时间戳、触发的技能、关键 prompt/context 配置、subagent 输出、人工干预、commit hash、教训。

## Phase 0.5 — 冷启动验证（2026-08-15）

- **主 agent**: Claude Code（brainstorming → SPEC/PLAN）
- **冷启动 agent**: Codex CLI，全新会话，仅提供 SPEC.md + PLAN.md
- **任务**: PLAN Task 2（Action Protocol）
- **结果**: 提出 5 个问题（2 个暴露真实 PLAN 缺陷：parameters 非对象校验缺失、message key 缺失时错误信息误导），TDD 完整（红→红→绿），8 tests passed
- **SPEC/PLAN 修订**: Task 2 测试 5→8 个；SPEC §3.3 参数校验措辞修订
- **完整记录**: `docs/spec_process/cold_start_codex_transcript.md`、`SPEC_PROCESS.md`
- **Commit**: `520c20f`

**教训**: 冷启动 agent 抓到的缺陷集中在"输入边界条件未穷举"，而不是预判的"跨文件一致性"。以后自审 SPEC 优先做边界条件穷举。

## Task 1 — 项目骨架 + 最小 CI（2026-08-15）

- **Worktree**: `../safe-swe-lite-task-01`，分支 `task/01-project-scaffold`
- **Implementer**: executor subagent，prompt 含完整 Task 1 文本 + 环境约束（Python 3.13、清华 pip 镜像、禁 git 命令）
- **产出**: pyproject.toml、8 个包 `__init__.py`、test_smoke.py、ci.yml（unit-test + lint 双 job）
- **验证**: `pytest -q` → 9 passed（1 smoke + 8 protocol）；ruff 干净
- **Spec 评审**: ✅ 与 PLAN 逐字一致，无缺失无多余（code-reviewer subagent）
- **质量评审**: APPROVE + 1 Important（console script 悬空引用）+ 3 Minor
- **修复**: cli.py 占位 stub、CI lint job 安装统一、.gitignore 追加缓存目录
- **最终验证**: 9 passed、ruff 干净、`safe-swe-lite` 命令输出友好提示
- **Merge**: PR #1 → main，commit `4315483`

**教训**:
1. editable install 不校验 entry point 目标模块，console script 悬空只能靠 stub 或推迟声明
2. 冷启动 agent 没建 `__init__.py`（Python 3.13 namespace package 也能跑），PLAN 里"已存在，跳过"的假设不成立——implementer 补建了
3. main 仓库的未提交文件（AGENT_LOG.md 初版）在 `git reset --hard origin/main` 时丢失——**在 main 仓库写文件后必须立即提交**

## Task 2 — Action Protocol（2026-08-15，冷启动 agent 完成）

- **实现者**: Codex CLI（冷启动验证 agent）
- **产出**: `src/safe_swe_lite/agent/protocol.py`、`tests/test_protocol.py`（8 tests）
- **包含**: 缺 message / 非法 JSON / 缺 action / 未知 action / 缺 parameters（默认 {}）/ parameters 非对象 六类边界
- **Commit**: `520c20f`

## Task 3 — LLM 抽象层 + MockLLM（2026-08-15）

- **Worktree**: `../safe-swe-lite-task-03`，分支 `task/03-mock-llm`
- **Implementer**: executor subagent，完整 Task 3 文本 + TDD 要求
- **产出**: `llm/base.py`（Model Protocol）、`llm/mock.py`（MockLLM 预录播放）、`tests/test_mock_llm.py`（4 tests）
- **验证**: 13 passed（1 smoke + 8 protocol + 4 mock），ruff 干净
- **Spec 评审**: ✅ 与 PLAN 逐字一致（code-reviewer subagent）
- **质量评审**: APPROVE + 5 Minor，采纳 2 个：`_index` 加 `field(init=False, repr=False, compare=False)` 防污染 dataclass 接口；补 kwargs 透传测试
- **偏差**: PLAN 的 base.py 有未使用的 `Any` import（ruff F401），implementer 移除——最小必要修正

**教训**:
1. worktree 之间共享全局 Python 环境：editable install 会指向最后一次安装的 worktree，切 worktree 跑测试前需重装
2. 耗尽信号用 IndexError 是"响亮失败"设计——真实 agent loop 有 submit 收尾 + max_steps 兜底，耗尽只意味着测试场景写错

## Task 4 — Agent 主循环（2026-08-15）

- **Worktree**: `../safe-swe-lite-task-04`，分支 `task/04-agent-loop`
- **Implementer**: executor subagent，完整 Task 4 文本 + TDD
- **产出**: `agent/loop.py`（Agent dataclass + run() 主循环）、`tests/test_agent_loop.py`（5→8 tests）
- **验证**: 18→21 passed，ruff 干净
- **Spec 评审**: ✅ 与 PLAN 逐行一致
- **质量评审**: ❌ REJECT（1 Critical + 2 Important + 6 Minor）→ 修复 → 复审 ✅ APPROVE
- **Critical**: 护栏拦截路径不消耗 steps → LLM 持续产出被拦截动作时循环永不终止。修复：`max_blocked=5` 独立计数器 + `guardrail_exhausted` 退出码。评审员给出终止性证明（三计数器单调有界）
- **Important 修复**: guardrail 分支 3 个测试；`format_observation()` 建立 Task 5 ToolResult 格式化契约
- **PLAN 修订**: Task 4 后追加实现后修订记录（见 PLAN.md）

**教训**（重要）:
1. **PLAN 的设计缺陷被评审拦截**：我写 PLAN 时认为"拦截不消耗步数=与 mini-swe-agent 语义一致"，但 mini-swe-agent 实际通过异常路径消耗步骤。设计任何"不消耗主计数器"的路径，必须同时设计专属终止保障
2. 质量评审的价值在 Task 4 完整体现：spec 合规（逐字一致）≠ 代码正确（有 Critical bug）
3. 零覆盖的控制流分支（guardrail）就是 bug 的藏身处——评审员原话"该 Critical 缺陷正是因此漏网"

## Task 5 — 工具系统（2026-08-15）

- **Worktree**: `../safe-swe-lite-task-05`，分支 `task/05-tools`
- **Implementer**: executor subagent，完整 Task 5 文本 + TDD
- **产出**: `tools/__init__.py`（ToolResult + Dispatcher）、file_tools / command_tools / search_tools / submit_tool、`tests/test_tools.py`（10→14 tests）
- **验证**: 31→35 passed，ruff 干净，mypy 干净
- **Spec 评审**: ✅ APPROVE。两个偏差均合理：Windows cmd.exe 不剥单引号导致 `python -c 'exit(3)'` 实际 exit 0（实证后改双引号跨平台写法）；移除未用 ToolResult import
- **质量评审**: ❌ REJECT（1 Critical + 4 Important）→ 修复 → 复审 ✅ APPROVE
- **Critical**: search fallback ReDoS——LLM 病态正则 `(a+)+$` 在无超时的 re.search 中指数挂起；且本机 Python 环境 PATH 无 rg（Git Bash 有、Windows PATH 没有），fallback 是实际生效路径。修复：fallback 移入 `sys.executable -c` 子进程 + 10s 超时。实测 200K 字符病态正则 10.0s 整终止
- **Important 修复**: rg 退出码 2（无效正则）报错而非假 "(no matches)"；Dispatcher 统一 32K 截断；write/edit 加 resolve 与 read 一致；errors="replace" 全覆盖（GBK 输出不炸）
- **评审附带发现**（供 Task 7 用）：`Path('C:/ws') / 'D:/evil.txt'` → `D:/evil.txt`（跨盘符替换 workspace）；`/abs.txt` → 盘根逃逸。围栏的 resolve + is_relative_to 能拦，但必须加这两个显式测试

**教训**:
1. **环境双面性**：Bash 工具里 `rg --version` 有输出 ≠ Python subprocess 能找到 rg——Git Bash 的 PATH 和 Windows PATH 是两回事。工具可用性判断要区分 shell 环境
2. ReDoS 是 LLM 输入类工具的原生威胁：任何执行 LLM 提供字符串的引擎（正则/SQL/shell）都需要超时或长度边界，光靠"LLM 不会写病态正则"是靠不住的
3. 截断收敛在 Dispatcher 单点是正确架构——新工具自动获得保护
4. **ruff 版本漂移（CI 第二轮教训）**：CI 的 lint job 装最新 ruff，默认规则集随版本扩张（BLE001/PLW1510 在新版变默认）。implementer 的"本地 ruff 干净"不可信——本地 ruff 0.15.14 过不了 CI 的检查（6 个错误：I001×2、BLE001、PLW1510×3）。修复：多行 import 格式、`except Exception` 加 `# noqa: BLE001`（有意设计）、3 处 subprocess.run 显式 `check=False`。**教训：lint 验证必须用与 CI 相同的 ruff 版本，或者干脆在 CI 里跑 `ruff check` 作为唯一的 lint 真相源，本地跑不过是浪费**
