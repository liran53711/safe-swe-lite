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

## Task 6 — 护栏 L1 静态黑名单（2026-08-15，三轮军备竞赛）

- **Worktree**: `../safe-swe-lite-task-06`，分支 `task/06-guardrail-l1`
- **Implementer**: executor subagent × 4 轮（实现 + 3 轮修复）
- **产出**: `guardrails/checker.py`（GuardrailDecision BaseModel + StaticChecker）、`tests/test_guardrails.py`（8→28 tests）
- **验证**: 43→63 passed，ruff 干净
- **Spec 评审**: ✅ APPROVE（implementer 发现 PLAN 自相矛盾：vim 在精确匹配表但测试要求前缀拦截——交互式编辑器必须前缀拦，REPL 只拦裸启动）
- **质量评审**: ❌ REJECT ×3 → 终审 ✅ APPROVE。评审员做真实对抗性测试，每轮都找到新绕过

**三轮军备竞赛的绕过清单（全部已修）**：
| 轮 | 发现 | 修复 |
|---|---|---|
| 1 | `sh -c 'rm -rf /'` 套壳、`echo hi; sudo` 链、radare2 `-c '!rm -rf /'` 白名单逃逸、`.ENV` 大小写、`cat .env` 绕 read_file | 任意位置正则 + requires_approval 路由 + payload 转义检查 + casefold |
| 2 | `rm -Rf /`（大写）、`rm -rf -- /`（--）、`rm / -rf`（getopt 置换）、前缀条目 `echo hi; sudo` 同类 | rm 语义双条件检查（递归标志+破坏性目标） |
| 3 | `echo hi; rm -rf .`（语义检查门控在首词）、`--recursive` 长选项、`~/` 尾随斜杠、`rm "-rf" /` 引号 | 任意位置 RM_TOKEN + fall-through + 长选项 + 边界 lookahead |

**文档化边界**（checker.py docstring）：grep/sed 读 .env、eval 包装器、纯文本误伤、深度混淆——明确委托 L3/L4/沙箱，不再打补丁。

**教训**（本项目最重要的工程课）:
1. **护栏验收标准**：不能只测"规则在预期输入上生效"，必须测"规则在对抗输入上不失效"。原 8 个测试全是前者，三轮 REJECT 全是后者
2. **军备竞赛必须有收口条件**：每轮都能找到新绕过（正则永远有下一个变体），所以 L1 的 docstring 写了四条已知边界——分层防御的意义就是单层不完美但组合可靠。无限打补丁会把 L1 变成正则沼泽
3. **评审员建议的代码也要验证**：评审第一轮给的 rm 正则实测是死代码（不匹配任何变体），implementer 实证后修正。信任但要验证
4. **安全方向的误伤可接受**：`echo "rm -rf /"` 纯文本被拦——误伤的成本是 LLM 收到 reason 换个说法，漏拦的成本是数据丢失。不对称的
5. 遗留 LOW（WebUI 任务前处理）：真实 ToolResult 对象进 trace 需 asdict 才能 JSON 序列化

## Task 7 — 护栏 L2 范围围栏（2026-08-15）

- **Worktree**: `../safe-swe-lite-task-07`，分支 `task/07-scope-fence`
- **Implementer**: executor subagent × 2 轮（实现 + 修复）
- **产出**: `guardrails/scope_fence.py`（28 行）、test_guardrails.py 追加 7→9 个 L2 测试（去 1 重复）
- **验证**: 70→71 passed，ruff 干净
- **Spec 评审**: ✅ APPROVE（跨盘符测试做了平台适配 skip 守卫；发现 PLAN 笔误"5 passed"实为 7 个测试）
- **质量评审**: APPROVE + 3 Important + 4 Minor → 修复 → 复审 ✅ APPROVE
- **Important 修复**: ① `.env.` 尾随点绕过（Windows 文件系统忽略尾随点，实测真读到 .env——Task 6 同类 bug 的变体，`rstrip(" .")` 修复且不用 strip 防误伤 `..env`）；② symlink 逃逸测试补上（resolve 展开后拦截，Windows 真实创建 symlink 实测）；③ 非字符串 path 拦截（isinstance 先于 falsy 判断，`0`/`[]` 也是非字符串）
- **评审员对抗性实测 31 项**：symlink、UNC 路径、盘符大小写、dotdot、绝对路径、跨盘符、尾随空格——全部拦截正确

**教训**:
1. **同类 bug 会在兄弟模块复发**：Task 6 修了尾随空格，Task 7 评审发现尾随点变体。修 bug 时要想"这个 bug 类还有哪些变体"，一次修全
2. **Windows 文件系统语义是隐蔽攻击面**：尾随空格、尾随点、盘符大小写、UNC——护栏必须用 resolve/规范化后的路径判定，且每个平台差异都要有测试
3. 评审员 31 项实测中代码行为全对、缺口在测试覆盖——安全代码"行为对但没测试"等于"行为没有保障"

## Task 8 — 护栏 L3 HITL 状态机（2026-08-15）

- **Worktree**: `../safe-swe-lite-task-08`，分支 `task/08-hitl`
- **Implementer**: executor subagent × 2 轮（实现 + 状态机重写）
- **产出**: `guardrails/hitl.py`（HitlState str-Enum + HitlGate）、checker.py 补 LAYER_L3、test_guardrails.py 追加 5→10 个 L3 测试
- **验证**: 76→81 passed，ruff 干净
- **Spec 评审**: ✅ APPROVE（零偏差）
- **质量评审**: ❌ REJECT → 重写 → 复审 ✅ APPROVE
- **Critical**: **PLAN 的"状态机"其实是无状态决策工厂**——approve()/reject() 与 check() 完全脱钩，`_pending_action` 只写不读，批准后重查同一动作仍 PENDING（规范 HITL 流程 check→approve→recheck→execute 死锁）。重写为真状态机：_state 字段 + 已决终态尊重 + 新 PENDING 覆盖旧动作 + approve/reject 无 PENDING 时 noop
- **评审员边角推演亮点**：非灰色命令不清 pending 槽是防死锁的必要组成；人工拒绝粘性优先于 auto_approve（mock 不能推翻人工拒绝）；所有歧义路径统一偏向"重新询问"而非"自动放行"
- **威胁模型文档化**：L3 是软复核层 best-effort（前缀匹配可被空格/引号/链式绕过），硬安全由 L1/L4 兜底——和 L1 的边界文档化同一纪律

**教训**:
1. **"状态机"类名的代码不一定是状态机**：PLAN 代码片段把状态放进决策返回值而非对象内部，5 个原测试全部只断言单次决策形状——评审员证明"把 approve/reject 改成静态返回，5 个测试照样全绿"。**测试必须区分'看起来像状态机'和'是状态机'**：approve→重查→放行这条闭环测试是判据
2. 单槽记忆（只记一个待决动作）是刻意简化，WebUI 多动作队列时需升级 dict——已记录为 LOW 待办

## Task 9 — 护栏 L4 代码扫描 + GuardrailChain 组合器（2026-08-15，护栏收官）

- **Worktree**: `../safe-swe-lite-task-09`，分支 `task/09-code-scanner`
- **Implementer**: executor subagent × 2 轮（实现 + 修复）
- **产出**: `guardrails/code_scanner.py`（AST 双分支扫描 + 别名解析 + 1MB 上限）、`guardrails/__init__.py`（GuardrailChain）、checker.py 补 LAYER_L4、test_guardrails.py 追加 9+9 个测试
- **验证**: 90→99 passed，ruff 干净
- **Spec 评审**: ✅ APPROVE（implementer 发现 PLAN 自相矛盾：DEFAULT_BANNED 有点分全名 "pickle.loads"，但 Attribute 分支只查裸模块名——按 PLAN 代码 pickle.loads 拦不住）
- **质量评审**: ❌ REJECT（4 Important，全部实测）→ 修复 → 复审 ✅ APPROVE
- **Important 修复**:
  1. **edit_file 从不被扫描**——参数是 old_string/new_string 没有 content 字段，L4 恒放行（端到端实测 write 干净 + edit 插 eval 绕过全部四层）。修复按 action.name 分支取 content/new_string
  2. **ast.parse 无大小上限**——5MB 实测 24s/2.6GB。1MB 上限跳过扫描
  3. **import 别名绕过**——`import subprocess as sp; sp.run()` 一行惯用法废掉整个禁令。修复收集 Import/ImportFrom 别名映射，调用点解析真实模块名（builtins 特判保持身份）
  4. **auto_approve 接线死锁**——loop 调用点传不进去，mock 演示遇灰命令 5 次后 guardrail_exhausted。GuardrailChain 构造函数接收 auto_approve 并透传 hitl_state
- **终审遗留**: builtins.eval 属性形态（`import builtins; builtins.eval(x)`）一行名单修复（我直接改了）；赋值别名绕过（`f = subprocess.run`）文档化为边界（无数据流分析的静态 AST 检查的经典局限）

**护栏四层总结**（main contribution 完成）:

| 层 | 机制 | 测试数 | 军备竞赛轮数 |
|---|---|---|---|
| L1 静态黑名单 | 任意位置正则 + rm 语义双条件 + 引号剥离 | 28+ | 3 轮 |
| L2 范围围栏 | resolve + is_relative_to + 平台路径归一化 | 9 | 1 轮 |
| L3 HITL 状态机 | 真状态机（终态记忆）+ auto_approve 接线 | 10 | 1 轮（状态机重写） |
| L4 代码扫描 | AST 双分支 + 别名解析 + 1MB 上限 | 16 | 1 轮 |

**教训**:
1. **参数契约要读工具实现**：L4 声称覆盖 edit_file，但没人核对过 edit_file 的参数表——`content` vs `new_string` 一字之差，整层失效。护栏层声称覆盖的动作必须逐个对照工具签名
2. 评审员三问的价值：编辑动作扫什么？大文件怎么办？别名怎么处理？——每个都是"读了工具实现才知道"的问题
3. 四层各自的文档化边界共同构成护栏的诚实性：L1 四条、L3 软复核层、L4 赋值别名——"知道哪拦不住"比"声称全拦住"更安全

## Task 10 — 反馈闭环（2026-08-16）

- **Worktree**: `../safe-swe-lite-task-10`，分支 `task/10-feedback`
- **Implementer**: executor subagent × 2 轮（实现 + 修复）
- **产出**: `feedback/validators.py`（PyCompileValidator + TestValidator + format_for_llm）、`feedback/loop.py`（run_with_retry）、test_feedback.py（5→9 tests）
- **验证**: 104→108 passed，ruff + mypy 干净
- **Spec 评审**: ✅ APPROVE（implementer 发现 PLAN 测试与实现片段三处内部矛盾：format_for_llm 头部文案、loc 格式、死 import——按 TDD 以测试为契约）
- **质量评审**: APPROVE + 4 Important + 4 Minor → 修复 → 复审 ✅ APPROVE
- **Important 修复**: ① TimeoutExpired 未捕获会击穿未来 Agent.run；② rglob 扫进 .venv/__pycache__ 产生假阳性失败；③ pytest rc 2/3/4/5（无测试/配置错误）被当"测试失败"空耗重试轮——改为 passed=True 语义；④ execute_write 异常（MockLLM 耗尽/网络错误）时返回最后验证结果 + loop 错误标记而非崩溃
- **核心交付物 0 覆盖教训**：run_with_retry 初始 5 个测试全测 validators，重试循环本体 0 覆盖——评审员指出后补 4 个调用次数精确断言（0/1/3 次）的测试

**教训**:
1. **测试文件与实现片段必须由同一个人对照写**——PLAN 里两段代码由我分别起草，三处不一致（文案/格式/import）。以后 PLAN 的测试和实现代码块要交叉校验后再发布
2. **"核心交付物 0 覆盖"是常见的假完成**：模块写了、测试写了，但测试全在测辅助函数。每个 task 收尾问一句"本 task 的核心 API 有直接测试吗"
3. pytest 退出码语义：rc 1 才是"测试失败"（可反馈），rc 5 是"没有测试"（不可反馈）——把不可修的错误喂给模型重试是浪费轮次

## Task 11 — 记忆：评分 + 分级上下文（2026-08-16）

- **Worktree**: `../safe-swe-lite-task-11`，分支 `task/11-memory`
- **Implementer**: executor subagent × 2 轮（实现 + 修复）
- **产出**: `memory/scoring.py`（纯规则评分）、`memory/store.py`（MemoryStore 分级上下文）、test_memory.py（7→10 tests）
- **验证**: 115→118 passed，ruff 干净
- **Spec 评审**: ✅ APPROVE（零偏差；发现 SCORES 死键冗余）
- **质量评审**: ❌ REJECT（2 High）→ 修复 → 复审 ✅ APPROVE
- **High**: ① 评分与存储完全脱节——score_observation 零调用方，assemble() 用 old[-5:] 时序选取而非评分；50 轮会话的第 1 轮架构信息彻底丢失（REPL 实证）；② 摘要裸 80 字符头部截断（信息在尾部被切掉）+ 冒充 user 消息
- **修复**: assemble() 按 score_observation 取 top-N（平局偏向新消息，升序取尾实现）；_summarize 尾部截断 + [kind] 前缀；摘要 role="system"；recent_window<=0 防御；死键删除

**教训**:
1. **模块内部的接口要自洽**：Task 11 交付的两个文件（评分、存储）互不调用——单独看都对，合起来是断的。每个 task 收尾问"本 task 交付的模块之间有数据流动吗"
2. 摘要的截断方向是信息论问题：消息开头是 greeting、结尾是结果——尾部截断保信息量，头部截断保垃圾

## Task 12 — 配置系统（2026-08-16）

- **Worktree**: `../safe-swe-lite-task-12`，分支 `task/12-config`
- **Implementer**: executor subagent × 2 轮（实现 + 修复）+ 我直接修 1 处 HIGH
- **产出**: `config/loader.py`（5 个 Pydantic 模型 + load_config）、包内 default.yaml、test_config.py（4→8 tests）
- **验证**: 112→116 passed，ruff 干净
- **Spec 评审**: ✅ APPROVE
- **质量评审**: APPROVE（3 Important）→ 修复 → 复审 ❌ REJECT（1 HIGH）→ 修复 ✅
- **Important**: ① 打包路径错误——parents[3] 只在源树成立，且 default.yaml 不进 wheel；修复 importlib.resources + package-data（wheel 布局模拟实测通过）；② 未知键静默忽略——extra="forbid" fail-fast；③ GuardrailConfig 4 个死字段——改名接线 GuardrailChain、删 allowed_dirs（YAGNI）
- **HIGH（复审抓到）**: implementer 声称修复的"顶层非 dict 抛 ValidationError"本身是坏的——from_exception_data 缺 ctx/input 键抛 TypeError。修复一行 + 回归测试。**教训：声称的修复必须配回归测试，评审员实测发现 115 passed 全绿恰恰因为没有这个测试**

**教训**:
1. **配置静默失败比报错更危险**："你以为设了 max_turn=100，实际跑 50"——extra="forbid" 是配置系统的默认正确选择
2. 打包路径算术（parents[N]）在 editable 下蒙蔽人——资源加载必须用 importlib.resources，让 wheel 安装路径天然正确
3. 与 Task 11 相同的教训：两个 task 并行跑在独立 worktree，全局 editable install 冲突——用 PYTHONPATH=src 跑测试是标准解法
