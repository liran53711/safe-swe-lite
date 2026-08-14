# 第 4 节笔记：历史处理与配置

> 教材：SWE-agent `agent/history_processors.py`、`config/`

## 直觉

全量消息列表不断增长最终会超出 LLM 上下文窗口。历史处理器的思路是：**在传给 LLM 之前先裁剪，但完整消息列表不动（供轨迹记录/日志使用）。**

## 处理器链架构

```
self.messages（全量，用于轨迹/日志）
    ↓ 复制一份
history_processor_1
    ↓
history_processor_2
    ↓
self.model.query(processed)   ← LLM 只看到裁剪后的
```

配置示例：
```yaml
agent:
  history_processors:
    - type: last_n_observations
      n: 5
    - type: closed_window
    - type: cache_control
      last_n_messages: 2
```

处理器是**有序的**——消息依次流过每个处理器，顺序影响结果。

## 三个核心处理器

### LastNObservations（消息级裁剪）

只保留最近 `n` 条 observation 的完整内容。更早的被替换为：
```
"Old environment output: (N lines omitted)"
```

**关键：是替换不是删除。** 被裁剪的 observation 仍然占一个消息位（保持对话结构完整），但内容变成了占位符。

支持的精细控制：
- `always_remove_output_for_tags`: 打上某些 tag 的 observation 无论位置多近都裁剪
- `always_keep_output_for_tags`: 打上某些 tag 的 observation 无论位置多远都保留
- `polling`: 批量化裁剪，隔 `polling` 步才多裁一条（为了减少缓存失效）

### ClosedWindowHistoryProcessor（内容级裁剪）

解决文件重复读取时的 token 浪费。LLM 经常反复打开同一个文件不同版本。

```python
for entry in reversed(history):  # 从后往前
    file = extract_filename(entry)
    if file in windows:
        replace_with_omitted(entry)  # 旧视图 → 省略提示
    windows.add(file)
```

**从后往前**遍历——每个文件只保留最新一次出现的视图。旧视图的文件内容被替换为 `"Outdated window with N lines omitted..."`，但同一条消息里的其他输出（如 pytest 结果）不受影响。

### CacheControlHistoryProcessor（成本优化）

给最近 N 条消息打上 Anthropic cache_control 标记，让 Claude API 缓存这些消息避免重复计费。纯工程优化，和上下文管理无关。

## 两种裁剪粒度对比

| | LastNObservations | ClosedWindowHistoryProcessor |
|---|---|---|
| 裁剪单位 | 整条消息 | 消息内的文件视图片段 |
| 判断标准 | 消息位置（前N条） | 文件是否有更新版本 |
| 被裁后占位符 | 一行省略提示 | "Outdated window..." |
| 同消息的测试输出 | 一起消失 | 保留不动 |

**关键洞察：** 文件视图和测试输出有不同的"保鲜期"。文件改过之后旧视图就过时了，但测试失败的输出无论多老都是回灌给 LLM 的有效信号。两种信息应该被独立处理。

## 配置系统

SWE-agent 使用 YAML + Pydantic 管理配置。`ToolConfig` 类（`tools/tools.py`）在 `model_post_init` 里做了两件事：

1. 从 YAML 加载的所有 bundle 中收集 commands，合并重复检测
2. 生成 `command_docs`——自动把 commands 渲染成 LLM 可读的文档字符串，注入 system prompt

SafeSWE-Lite 采用类似设计：YAML 文件 → Pydantic 加载 → 注入 Agent/Guardrail/Tools 各组件。

## 映射 SafeSWE-Lite

| SWE-agent | SafeSWE-Lite |
|---|---|
| 处理器链 | Memory.assemble() 内部做分级上下文裁剪 |
| LastNObservations (n=5) | 近 10 轮保留原始消息 |
| ClosedWindowHistoryProcessor | 不做文件级裁剪（v1 最小实现） |
| CacheControlHistoryProcessor | 不做（不接 Anthropic API 时不需要） |
| YAML config | YAML config + Pydantic Config 类 |

## 预习问题（第 5 节）

Aider 的反馈闭环：每次 `write_file` 后自动运行 linter，失败就把错误信息喂回 LLM，最多重试 3 轮。这个流程里，"lint 失败"被转换成什么格式的信息回灌给 LLM？这种格式和我们之前看到的 observation 格式有什么本质区别？
