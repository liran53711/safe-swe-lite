# 参考项目研究

## 首选参考: mini-swe-agent (Princeton NLP)

- **Repo:** https://github.com/SWE-agent/mini-swe-agent
- **论文:** SWE-agent: ACI Enable Automated SE (NeurIPS 2024, arXiv:2405.15793)
- **前身:** SWE-agent (~19.8k stars), mini-swe-agent 是其精简版

### 架构 (三大组件, 各约100行)

| 组件 | 文件 | 职责 |
|---|---|---|
| `DefaultAgent` | `src/minisweagent/agents/default.py` | 主循环: `while True: step()`, step = query → execute |
| `LocalEnvironment` | `src/minisweagent/environments/local.py` | 执行 bash, subprocess.Popen, 超时 SIGKILL |
| `LitellmModel` | `src/minisweagent/models/litellm_model.py` | 封装 litellm.completion(), tools=[BASH_TOOL], 重试+计费 |

### 唯一的工具定义
```python
BASH_TOOL = {
    "type": "function",
    "function": {
        "name": "bash",
        "description": "...",
        "parameters": {
            "type": "object",
            "properties": { "command": {"type": "string"} },
            "required": ["command"]
        }
    }
}
```

### 主循环核心代码 (简化)
```python
class DefaultAgent:
    def __init__(self, model, environment, config):
        self.model = model
        self.environment = environment
        self.messages = []
    
    def run(self, task):
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self.messages.append({"role": "user", "content": task})
        while True:
            response = self.model.query(self.messages)
            actions = self.execute_actions(response)
            # 结果回灌
            self.messages.append({"role": "assistant", "content": response})
            self.messages.append({"role": "user", "content": actions})
```

### 测试策略
- `DeterministicModel` — 预编程返回, 按顺序输出
- `DeterministicToolcallModel` — 预编程 tool_call 返回
- 参数化测试: 每个 test 跨 text/toolcall/response_api 模型类型运行
- 真实 API 测试 (`test_fire.py`): 需花钱
- 交互测试 (`test_interactive.py`): HITL 模式

---

## 完整 SWE-agent 架构

### 主循环 — `DefaultAgent.run()`
```python
def run(self, env, problem_statement, output_dir):
    self.setup(env=env, problem_statement=problem_statement, output_dir=output_dir)
    step_output = StepOutput()
    while not step_output.done:
        step_output = self.step()
        self.save_trajectory()
    return AgentRunResult(info=data["info"], trajectory=data["trajectory"])

def step(self) -> StepOutput:
    step_output = self.forward_with_handling(self.messages)  # 带错误恢复
    self.add_step_to_history(step_output)
    self.add_step_to_trajectory(step_output)
    return step_output

def forward(self, history) -> StepOutput:
    step = StepOutput()
    output = self.model.query(history)                    # 1. 调用 LLM
    step.thought, step.action = self.tools.parse_actions(output)  # 2. 解析动作
    return self.handle_action(step)                       # 3. 执行动作

def handle_action(self, step) -> StepOutput:
    if self.tools.should_block_action(step.action):       # 护栏检查
        raise _BlockedActionError()
    if step.action.strip() == "exit":
        step.done = True
        return step
    step.observation = self._env.communicate(input=run_action)  # 环境执行
    step.state = self.tools.get_state(env=self._env)
    return step
```

### 护栏机制 — `ToolHandler.should_block_action()`
```python
def should_block_action(self, action: str) -> bool:
    if any(action.startswith(f) for f in self.config.filter.blocklist):
        return True                           # 前缀匹配: vim, vi, emacs, nano...
    if action in self.config.filter.blocklist_standalone:
        return True                           # 精确匹配: python, bash, sh...
    if name in self.config.filter.block_unless_regex:
        return not re.search(regex, action)   # 正则白名单
    return False
```

默认 blocklist: `["vim", "vi", "emacs", "nano", "nohup", "gdb", "less", "tail -f", "python -m venv", "make"]`

### Action Parser 体系 (12种)
- `ThoughtActionParser` — 讨论 + ```代码块```
- `FunctionCallingParser` — LiteLLM tool_calls JSON
- `XmlThoughtActionParser` — `<command>` 标签
- `JsonParser` — `{"thought": ..., "command": {...}}`
- 等等

### HistoryProcessor 链
- `LastNObservations` — 只保留最近 N 条 observation (论文核心技术)
- `ClosedWindowHistoryProcessor` — 只保留最新文件视图窗口
- `CacheControlHistoryProcessor` — Anthropic cache control 标记

### Mock LLM 测试
```python
class PredeterminedTestModel(AbstractModel):
    def __init__(self, outputs: list[dict | str]):
        self._outputs = outputs
        self._idx = -1

    def query(self, *args, **kwargs) -> dict:
        self._idx += 1
        output = self._outputs[self._idx]
        if isinstance(output, str):
            _handle_raise_commands(output)  # "raise_cost", "raise_context"
            return {"message": output}
        return {"message": output["message"], "tool_calls": output.get("tool_calls")}
```

特殊字符串 `"raise_cost"`, `"raise_context"`, `"raise_runtime"` 触发对应异常, 测试所有错误路径.

---

## OpenHands SDK (CMU Graham Neubig, 80.7k stars)

### 特色
- 无状态 Agent: 每个 step() 读事件流, 写新事件
- 安全: `LLMSecurityAnalyzer` (LLM 自标注 risk level) + `ConfirmRisky` 策略
- 工作区: Docker/Remote 隔离
- 记忆: Event stream + AgentContext skills + Condenser

---

## Aider (47.4k stars)

### 特色: 最强反馈闭环
- 每次编辑后自动 lint (tree-sitter, 100+语言)
- `--auto-test` 每次编辑后跑测试
- 失败时错误回灌, LLM 自我修正, 最多3轮
- RepoMap: 基于 PageRank 的代码地图

---

## 与项目要求的映射

| 项目要求 | mini-swe-agent | SWE-agent | OpenHands | Aider |
|---|---|---|---|---|
| 自实现主循环 | Yes (简洁) | Yes (完整) | Yes (复杂) | Yes (专精) |
| Mock LLM 测试 | DeterministicModel | PredeterminedTestModel | NoOp 模式 | mock send() |
| 不使用框架 | litellm 仅作 API 客户端 | 同上 | SDK 自包含 | litellm 仅作客户端 |
| 护栏机制 | 无 (最简) | blocklist + 格式检查 | 风险分级 + 确认策略 | git commit + /undo |
| 反馈闭环 | action result 直接回灌 | observation → history | observation events | lint + test + 3轮修正 |
| 记忆 | messages 列表 | messages + HistoryProcessor 链 | Event stream + skills + Condenser | RepoMap + 摘要 |
| 工具 | 1个 bash | bash + ACI 定制工具 | 多工具 + MCP | 无 (纯文本编辑) |

---

## 我的建议

### 最适合你做参考的项目: **SWE-agent (完整版)**

理由:
1. **六个维度都有清晰实现**: 主循环、工具、记忆(HistoryProcessor)、护栏(blocklist)、反馈(observation)、配置(YAML)
2. **Mock 测试体系成熟**: PredeterminedTestModel 完美对应你的"确定性单元测试"要求
3. **护栏是代码不是提示词**: `should_block_action()` 函数可以直接对标你要求的"代码版"
4. **NeurIPS 2024 论文背书**: 学术引用价值高
5. **可以重点深入"治理"或"反馈闭环"维度**

### 架构参考图

```
用户任务
  ↓
┌─────────────────────────────────────┐
│           DefaultAgent              │
│  ┌─────────────────────────────┐    │
│  │ while not done:             │    │
│  │   response = model.query()  │───→ LLM (可 mock)
│  │   thought, action = parse() │    │
│  │   if blocked(action): error │───→ 护栏
│  │   obs = env.execute(action) │───→ 工具执行 (Docker sandbox)
│  │   history.append(obs)       │───→ 反馈回灌
│  │   done = check_stop()       │───→ 停机判断
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
  ↓
提交结果 / 轨迹文件 (.traj)
```
