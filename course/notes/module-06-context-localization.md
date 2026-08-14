# 第 6 节笔记：上下文定位

> 教材：AutoCodeRover `app/search/search_backend.py`、`app/search/search_utils.py`

## 直觉

仓库太大不能全塞给 LLM。AutoCodeRover 的答案是：启动时用 AST 建索引，agent 用结构化搜索 API 精确定位，只把相关片段喂给 LLM。

## 索引构建：4 张表

```python
class_index:        类名 → [(文件, 起止行)]       # "User 类在哪"
class_func_index:   (类, 方法) → [(文件, 起止行)] # "User.login 在哪"
function_index:     函数名 → [(文件, 起止行)]      # "check_password 在哪"
class_relation_index: 类名 → [父类名]             # "User 继承了什么"
```

构建方式（`search_utils.py`）：`ast.parse()` 每个 .py 文件 → `ast.walk()` 收集 `ClassDef` / `FunctionDef` 的名字和行号范围。

## 搜索 API 与两阶段分离

```
find_method("login")  → auth.py 第 20-45 行
find_class("User")    → models.py 第 10-80 行
find_usage("check_password") → 3 处调用位置

[Search Agent]      探索代码库，收集上下文
        ↓ context
[Write Patch Agent] 只看到搜索 agent 整理的相关片段，生成补丁
```

修补 agent 从头到尾没见过仓库——防止 LLM 还没理解代码就急着写补丁。

## 预构建索引的缺陷：同步问题

agent 运行中修改代码后，索引不再准确：

| 情况 | 后果 |
|---|---|
| 行号漂移（插入/删除行） | 索引指向的行号全部偏移 |
| 新增符号 | 索引里没有，搜索返回"找不到" |
| 删除符号 | 索引指向旧位置，读到别的代码 |

AutoCodeRover 靠流程设计掩盖了问题：搜索发生在 patch 之前，大多数搜索时代码还没被修改。

## SafeSWE-Lite 的取舍

| AutoCodeRover | SafeSWE-Lite | 理由 |
|---|---|---|
| AST 预构建索引 | 按需 grep（ripgrep） | 实时搜索无同步问题 |
| find_method / find_class | search_pattern 正则搜索 | 简单、语言无关 |
| 探索 + 修补双 agent | 主循环内自然节奏 | 课程要求单 agent harness |
| 定位到类/方法/行号范围 | 定位到文件 + 行号 | grep -n 足够 |

**架构 trade-off：索引换速度，实时搜索换正确性。** 索引查询 O(1) 但会过时；grep 每次 O(文件总大小) 但永远最新。小仓库用 grep 正确且简单。

## 最小定位链（SafeSWE-Lite 的工具设计）

```
list_files      → 理解项目结构
search_pattern  → 定位符号 / 错误信息 / 调用点
read_file       → 只读相关片段（带 offset/limit）
edit_file       → 精确修改
```

## 预习问题（第 7 节）

Agentless 的主张是"很多软件修复任务不需要自主多轮 agent"。它的 pipeline 是 localization → repair → validation 三个固定阶段。如果这个主张成立，为什么课程 A 类还要求必须实现 agent 主循环？SafeSWE-Lite 的 agent loop 相比 Agentless 的固定 pipeline，在什么场景下有优势？
