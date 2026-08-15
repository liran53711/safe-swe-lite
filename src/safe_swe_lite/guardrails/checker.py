"""L1 guardrail: deterministic static blacklist with three match modes.

Known L1 boundaries (documented, not patched further):
- grep/sed/xxd/strings .env 等非常规读取命令：L1 只覆盖 cat 家族，其余委托 L3/L4
- eval/exec 包装器绕过：委托 L4 代码内容扫描
- 纯文本误伤（echo "rm -rf /"）：安全方向的可接受误伤
- 深度混淆命令（base64 编码后执行等）：需沙箱级隔离，超出 L1 范围
"""

import re

from pydantic import BaseModel

from safe_swe_lite.agent.protocol import Action

LAYER_L1 = 1
LAYER_L2 = 2
LAYER_L3 = 3

DEFAULT_BLOCKLIST = ["rm -rf /", "sudo", "chmod 777", "git push --force", "curl ", "wget ", "> /dev/sda", "mkfs", "dd if="]
# 交互式编辑器无论带不带参数都会挂起无 TTY 的 agent 循环，故按首词前缀拦截
INTERACTIVE_EDITORS = {"vim", "vi", "emacs", "nano"}
DEFAULT_STANDALONE = ["python", "python3", "ipython", "bash", "sh", "/bin/bash", "/bin/sh", "su"]
DEFAULT_BLOCK_UNLESS_REGEX = {"radare2": r"\bradare2\b.*\s+-c\s+"}
PROTECTED_FILES = {".env", ".env.local", ".git-credentials", "id_rsa", "id_ed25519"}
_PROTECTED_CASEFOLD = {name.casefold() for name in PROTECTED_FILES}

# 高危模式：任意位置正则命中即拦截（防前缀匹配绕过，如 `echo hi; rm -rf /`、
# `echo hi; sudo mkfs.ext4 /dev/sda`）。在 startswith 前缀循环之前执行。
# 注：`\bsudo\b` 会误伤纯文本（如 `echo sudo 是命令`），属安全方向可接受的误伤。
# rm 模式的斜杠必须位于操作数边界（空白/命令分隔符/另一斜杠/行尾）：`rm -rf /tmp/x`
# 是子路径放行，`rm -rf //`（POSIX 根）与 `rm -rf /; ls` 拦截。
HIGH_RISK_PATTERNS = [
    r"\brm\s+(-[a-z]*[rf][a-z]*\s+)+/(?=[;&|/\s]|$)",  # rm -rf / 、rm -fr / 、rm -r -f / 等（flags 含 r 与 f）
    r">\s*/dev/sd[a-z]",
    r"dd\s+if=.*of=/dev/",
    r"\bsudo\b",
    r"\bchmod\s+777\b",
    r"\bgit\s+push\s+--force\b",
    r"\b(?:curl|wget)\s+\S",
    r"\bmkfs(?:\.\w+)?\b",
]

# 包装器命令：本身允许运行（如 `python test.py`），但命令体含高危内容时
# L1 硬拦（blocked=True），同时置 requires_approval=True 标记需人工复核（L3 后续实现 override）
WRAPPER_COMMANDS = ["sh", "bash", "python", "python3", "su", "perl", "ruby"]
HIGH_RISK_CONTENT = re.compile(r"(rm\s+-rf|/dev/sd|os\.system|subprocess|;.*rm)")

# rm 语义级检查：单一大正则无法覆盖参数置换形态（`rm / -rf`），改为两个独立判定条件
# 任意位置 rm 令牌：`rm`、`; rm`、`& rm`、`| rm`（`echo hi; rm -rf .` 需命中）
RM_TOKEN = re.compile(r"(?:^|[;&|]\s*)\brm\b")
# -r / -R / -rf / -fr / -Rf 等，以及 GNU 长选项 --recursive / --recursive 的等价拼写
# （`--recursive` 命中；注意 `--force` 内含字母 r 也会被长选项分支匹配，`rm --force /`
# 属安全方向的可接受误伤——GNU rm 无 -r 时无法删除目录，且该形态必须同时命中破坏性目标）
RM_RECURSIVE_FLAG = re.compile(r"(?:^|\s)(?:--[a-zA-Z]*[rR][a-zA-Z]*|-[a-zA-Z]*[rR][a-zA-Z]*)")
# 破坏性目标：/ ~ . .. 作为独立操作数；`~/` `./` `../` 与 `~` `.` `..` 等价（尾随斜杠在边界处）
# 斜杠后必须紧跟空白或行尾（`./build` `~/build` `/tmp/x` 是子路径，放行）
RM_DESTRUCTIVE_TARGET = re.compile(r"(?:^|\s)(?:/(?=\s|$)|~(?=/(?=\s|$)|(?=\s|$))|\.\.?(?:/(?=\s|$)|(?=\s|$)))")


class GuardrailDecision(BaseModel):
    blocked: bool
    layer: int = 0
    reason: str = ""
    requires_approval: bool = False  # L1 硬拦时的附加标记：该动作需人工复核（L3 后续实现 override 语义）
    hitl_state: str = ""  # L3 填充：pending/approved/rejected


class StaticChecker:
    def __init__(self, blocklist=None, standalone=None, block_unless_regex=None):
        if blocklist is None:
            blocklist = DEFAULT_BLOCKLIST
        if standalone is None:
            standalone = DEFAULT_STANDALONE
        if block_unless_regex is None:
            block_unless_regex = DEFAULT_BLOCK_UNLESS_REGEX
        self.blocklist = blocklist
        self.standalone = standalone
        self.block_unless_regex = block_unless_regex

    def check(self, action: Action) -> GuardrailDecision:
        if action.name == "read_file":
            path = action.parameters.get("path", "")
            # 归一化两种分隔符后取 basename：Windows 下 pathlib 认反斜杠，Linux CI 不认；
            # 显式替换保证两个平台判定一致。rstrip(" .") 防 Windows 打开文件时自动剥
            # 尾随空格与点（Windows 文件系统忽略尾随点：read_file(".env.") 实际读到 .env）。
            # 不用 strip()：会误伤 POSIX 合法的前导点文件名（如 ..env 被剥前导点改变语义）
            name = str(path).rstrip(" .").replace("\\", "/").rsplit("/", 1)[-1]
            if name.casefold() in _PROTECTED_CASEFOLD:
                return GuardrailDecision(blocked=True, layer=LAYER_L1, reason=f"reading protected file '{name}'")
            return GuardrailDecision(blocked=False)
        if action.name == "run_command":
            return self._check_command(action.parameters.get("command"))
        return GuardrailDecision(blocked=False)

    def _check_rm_command(self, command: str) -> GuardrailDecision | None:
        if RM_RECURSIVE_FLAG.search(command) and RM_DESTRUCTIVE_TARGET.search(command):
            return GuardrailDecision(blocked=True, layer=LAYER_L1, reason="rm with recursive flag on destructive target")
        return None

    def _check_command(self, command) -> GuardrailDecision:
        if not isinstance(command, str):
            return GuardrailDecision(blocked=True, layer=LAYER_L1, reason="command must be a string")
        if not command:
            return GuardrailDecision(blocked=True, layer=LAYER_L1, reason="empty command")
        command = command.strip()
        if not command:
            return GuardrailDecision(blocked=True, layer=LAYER_L1, reason="empty command")
        # 引号剥离版：仅用于正则检测（`rm "-rf" /` 与 `rm -rf /` 等价），不改变原始 command。
        # standalone 精确匹配除外——剥离引号会改变其语义，故 standalone 始终用原始 command。
        _detection = command.replace('"', "").replace("'", "")
        first_word = command.split()[0]
        # 1. 任意位置高危正则先于 startswith 前缀循环（防 `echo hi; sudo mkfs /dev/sda` 前缀绕过）
        for pattern in HIGH_RISK_PATTERNS:
            if re.search(pattern, _detection):
                return GuardrailDecision(blocked=True, layer=LAYER_L1, reason=f"blocked by high-risk pattern '{pattern}'")
        # 2. 任意位置的 rm 语义级检查（防 `echo hi; rm -rf .` 前缀绕过）：覆盖 -R / -- / GNU 长选项 /
        #    参数置换等等价拼写（`rm -Rf /`、`rm -rf -- /`、`rm / -rf`、`rm --recursive --force /`）。
        #    未命中（返回 None）时 fall through 后续检查，保证 `rm -rf //` 与 `echo hi; rm -rf //`
        #    均由 HIGH_RISK 模式统一判定，避免入口早退造成不一致。
        if RM_TOKEN.search(_detection):
            decision = self._check_rm_command(_detection)
            if decision is not None and decision.blocked:
                return decision
            # rm 语义检查放行（子路径/无破坏性目标）时跳过 startswith 前缀循环：
            # blocklist 的 `rm -rf /` 前缀会误伤 `rm -rf /tmp/x`，且该条目的实质
            # 已由语义检查 + HIGH_RISK 模式覆盖，rm 判定统一由这两者负责。
        else:
            for pattern in self.blocklist:
                if _detection.startswith(pattern):
                    return GuardrailDecision(blocked=True, layer=LAYER_L1, reason=f"blocked by prefix '{pattern}'")
        if command in self.standalone:
            return GuardrailDecision(blocked=True, layer=LAYER_L1, reason=f"blocked standalone command '{command}'")
        if first_word in INTERACTIVE_EDITORS:
            return GuardrailDecision(blocked=True, layer=LAYER_L1, reason=f"blocked interactive editor '{first_word}'")
        if first_word in WRAPPER_COMMANDS and HIGH_RISK_CONTENT.search(_detection):
            return GuardrailDecision(
                blocked=True,
                layer=LAYER_L1,
                reason="wrapped command contains high-risk content",
                requires_approval=True,
            )
        if re.search(r"\b(cat|type|cp|more|less|tail|head)\s+.*\.env\b", _detection):
            return GuardrailDecision(blocked=True, layer=LAYER_L1, reason="reading .env via shell command")
        if first_word in self.block_unless_regex:
            if not re.search(self.block_unless_regex[first_word], _detection):
                return GuardrailDecision(blocked=True, layer=LAYER_L1, reason=f"'{first_word}' requires matching whitelist regex")
            payload = _detection.split("-c", 1)[1] if "-c" in _detection else ""
            if re.search(r"[!;`$()]", payload):
                return GuardrailDecision(blocked=True, layer=LAYER_L1, reason=f"'{first_word}' -c payload contains command escape")
        return GuardrailDecision(blocked=False)
