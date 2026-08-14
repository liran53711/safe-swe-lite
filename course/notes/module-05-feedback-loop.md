# 第 5 节笔记：反馈闭环

> 教材：Aider `aider/linter.py`（305 行）

## 直觉

feedback loop 不是"把执行结果告诉 LLM"，而是"把结果翻译成 LLM 最方便用它来修错的格式"。Aider 的 lint 输出不是原始 stderr，而是"错误消息 + 出错行号 + 出错代码上下文"三合一的修复指令。

## Aider linter.py 核心流程

```
lint(fname)
  ├─ 1. filename_to_lang(fname)    识别语言
  ├─ 2. languages.get(lang)        匹配 lint 命令
  ├─ 3. 执行（py_lint 或 subprocess）
  ├─ 4. returncode == 0 → 返回 None（无事发生）
  └─ 5. 有错 → 格式化：
       res = "# Fix any errors below, if possible.\n\n"
       res += lintres.text                          # 错误消息
       res += tree_context(fname, code, lines)      # 出错代码 + █ 标注
```

## Python 的 lint 是三合一

```python
def py_lint(self, fname, rel_fname, code):
    basic_res = basic_lint(...)        # tree-sitter 语法检查
    compile_res = lint_python_compile(...)  # compile() 编译检查
    flake_res = self.flake8_lint(...)  # flake8（仅 E9/F 系列致命规则）
    return LintResult(text=合并文本, lines=合并行号)
```

## LintResult 结构

```python
@dataclass
class LintResult:
    text: str      # 错误消息
    lines: list    # 出错行号（0-indexed）
```

关键：`errors_to_lint_result()` 用正则从原始输出提取文件名+行号，把自由文本变成结构化数据。

## LLM 最终收到的完整格式

```
# Fix any errors below, if possible.

## Running: flake8 --select=E9,F821...
auth.py:23:5: IndentationError: unexpected indent

## See relevant line below marked with █.
auth.py:
20: def login(user, password):
22:     if user:
23: █       return x
```

三个部分：指令头 + 错误消息 + 带标注的代码上下文。

## SafeSWE-Lite 的 ValidationResult 设计

```python
@dataclass
class ValidationResult:
    passed: bool
    validator: str             # "lint" | "typecheck" | "test"
    file: str | None
    line: int | None
    message: str
    context: str | None        # 出错位置周围代码
    details: dict | None       # 校验器特有信息
```

三个校验器的字段示例：

| 校验器 | file | line | details 特有字段 |
|---|---|---|---|
| ruff (lint) | ✓ | ✓ | `code`: "F821", `fixable`: True |
| mypy (typecheck) | ✓ | ✓ | `expected_type`, `actual_type` |
| pytest (test) | ✓ | ✗ (无行号) | `test_name`, `assertion` |

## 有界重试循环

```
write_file → 触发校验
  ├─ 全部通过 → 继续
  └─ 有失败 →
       ├─ 第 1 轮：失败回灌 → LLM 修改 → 重校验
       ├─ 第 2 轮：再错 → 再回灌 → 再修改
       └─ 第 3 轮：还错 → 最终 ValidationResult 作为 observation 交回主循环
```

### 为什么 3 轮上限

1. 防止死循环（agent 无限重复纠错）
2. 边际收益递减：第 1-2 轮修复低级错误（拼写、缩进），第 3 轮修复逻辑问题，第 4 轮后 LLM 通常重复同样的错误
3. 3 轮后不是"报错退出"而是"交回主循环"——让主 LLM 做更高层次的决策（"问题不在这个文件，换策略"）

## 与 SWE-agent 的对比

| | SWE-agent | Aider | SafeSWE-Lite |
|---|---|---|---|
| 回灌内容 | command 原始 stdout | 结构化 lint 结果 | 结构化 ValidationResult |
| 校验触发 | 无自动校验 | 每次编辑后自动 lint | 每次 write_file 后自动校验链 |
| 重试机制 | 无 | 用户驱动 | 自动有界重试（max 3） |
| 失败后的选择 | LLM 自己从输出里找错误 | LLM 收到精确行号 | LLM 收到精确文件+行号+类型 |
