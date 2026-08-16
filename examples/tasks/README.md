# Task Files

任务文件的 JSON 结构：

- `task`: 任务描述字符串（必填）
- `max_steps`: agent 最大步数（可选，默认取 config.max_turns）
- `workspace`: agent 工作目录（可选，默认 config.workspace = ./examples/sample_project）
- `mock_outputs`: MockLLM 预编程回复列表（可选，默认 config.model.mock_outputs）

**workspace 契约（重要）**：

`fix_bug.json` 会真实编辑 workspace 内的文件。直接运行
`safe-swe-lite run examples/tasks/fix_bug.json`（默认 workspace）会
**修改 tracked 的 sample project 并永久移除其中的演示 bug**。

演示时请使用临时副本：

```bash
cp -r examples/sample_project /tmp/demo-workspace
# 修改 fix_bug.json 的 workspace 键（CLI 目前只接受 task_file 参数，无 workspace 覆盖选项）
```

WebUI（Task 15）必须遵守此契约：每次 demo 在临时副本上运行。
