"""L4 guardrail: scan written file content for banned symbols via AST.

威胁模型：L1-L3 只检查动作参数（命令字符串/路径），无法看见 write_file/edit_file
写入的**代码内容**。L4 用 Python ast 解析写入内容，只拦截禁用符号的**真实调用点**
（ast.Call 且 func 是 Name/Attribute），不误伤注释与字符串里的字样。
语法错误交给反馈闭环的 lint 处理，L4 不拦（ast.parse 失败直接放行）。
注意：ast 只能解析 Python 代码，非 .py 文件与非 write/edit 动作直接放行。
边界：超过 1MB 的写入内容跳过扫描（ast.parse 在 5MB 实测 24s/2.6GB），
该边界是刻意取舍——超大生成文件由反馈闭环的 lint/test 覆盖。
"""

import ast

from safe_swe_lite.agent.protocol import Action
from safe_swe_lite.guardrails.checker import LAYER_L4, GuardrailDecision

DEFAULT_BANNED = ["eval", "exec", "subprocess", "pickle.loads", "input", "builtins.eval", "builtins.exec"]

MAX_SCAN_BYTES = 1_000_000  # 1MB：超出时跳过 AST 扫描（解析成本非线性，见 docstring）


class CodeScanner:
    def __init__(self, banned_symbols=None):
        if banned_symbols is None:
            banned_symbols = DEFAULT_BANNED
        self.banned_symbols = banned_symbols

    def check(self, action: Action) -> GuardrailDecision:
        if action.name not in {"write_file", "edit_file"}:
            return GuardrailDecision(blocked=False)
        path = action.parameters.get("path", "")
        if not isinstance(path, str):
            return GuardrailDecision(blocked=False)
        if action.name == "write_file":
            content = action.parameters.get("content", "")
        else:  # edit_file
            content = action.parameters.get("new_string", "")
        if not (path.endswith(".py") and content):
            return GuardrailDecision(blocked=False)
        if not isinstance(content, str):
            return GuardrailDecision(blocked=False)
        if len(content.encode("utf-8", errors="replace")) > MAX_SCAN_BYTES:
            return GuardrailDecision(blocked=False)  # 超大文件跳过 L4，边界见 docstring
        try:
            tree = ast.parse(content)
        except (SyntaxError, TypeError, ValueError):
            return GuardrailDecision(blocked=False)  # 语法错误交给 feedback lint
        # 收集导入别名映射（本地名 -> 真实模块名/全名），调用点解析后判定：
        # `import subprocess as sp; sp.run(...)` 与 `from subprocess import run; run(...)`
        # 均会被解析回 subprocess 族。builtins 导入不改变符号身份（eval 仍是 eval）。
        aliases: dict[str, str] = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    local = alias.asname or alias.name.split(".")[0]
                    aliases[local] = alias.name
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == "*":
                        continue
                    local = alias.asname or alias.name
                    if node.module == "builtins":
                        aliases[local] = alias.name  # builtins 导入不改变符号身份
                    else:
                        aliases[local] = f"{node.module}.{alias.name}" if node.module else alias.name
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            # 直接调用：eval(s) / run(...) → func 是 ast.Name，经别名解析回真实符号
            if isinstance(node.func, ast.Name):
                name = node.func.id
                resolved = aliases.get(name, name)
                if resolved in self.banned_symbols or resolved.split(".")[0] in self.banned_symbols:
                    return GuardrailDecision(
                        blocked=True, layer=LAYER_L4,
                        reason=f"banned symbol '{resolved}' at line {node.lineno}",
                    )
            # 属性调用：subprocess.run(...) / pickle.loads(...) → func 是 ast.Attribute，
            # value 是 Name（subprocess/pickle），attr 是方法名。两种名单形态都要命中：
            # 裸模块名（"subprocess"）与点分全名（"pickle.loads"）。value 经别名解析。
            elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                base = aliases.get(node.func.value.id, node.func.value.id)
                full_name = f"{base}.{node.func.attr}"
                if full_name in self.banned_symbols or base in self.banned_symbols:
                    return GuardrailDecision(
                        blocked=True, layer=LAYER_L4,
                        reason=f"banned symbol '{full_name}' at line {node.lineno}",
                    )
        return GuardrailDecision(blocked=False)
