"""L2 guardrail: workspace scope fence. All file ops must stay inside workspace.

契约：无 path 参数的动作（如 list_files）直接放行，该行为仅安全于工具以 workspace 为根
或 fail-closed；新增工具不得引入非 workspace 默认路径。
"""

from pathlib import Path

from safe_swe_lite.agent.protocol import Action
from safe_swe_lite.guardrails.checker import GuardrailDecision, LAYER_L2

# 新增文件类动作必须在此登记，否则围栏静默放行
FILE_ACTIONS = {"read_file", "write_file", "edit_file", "search_pattern", "list_files"}


class ScopeFence:
    def __init__(self, workspace: Path):
        self.workspace = Path(workspace).resolve()

    def check(self, action: Action) -> GuardrailDecision:
        if action.name not in FILE_ACTIONS:
            return GuardrailDecision(blocked=False)
        path_param = action.parameters.get("path", "")
        # isinstance 检查必须先于 falsy 判断：0 和 [] 是 falsy 非字符串，必须先拦截
        if not isinstance(path_param, str):
            return GuardrailDecision(blocked=True, layer=LAYER_L2, reason="path must be a string")
        if not path_param:
            return GuardrailDecision(blocked=False)  # list_files 无需 path
        candidate = (self.workspace / path_param).resolve()
        if not candidate.is_relative_to(self.workspace):
            return GuardrailDecision(
                blocked=True, layer=LAYER_L2,
                reason=f"path '{path_param}' escapes workspace '{self.workspace}'",
            )
        return GuardrailDecision(blocked=False)
