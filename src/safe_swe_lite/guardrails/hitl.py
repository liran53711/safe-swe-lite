"""L3 guardrail: HITL state machine for actions needing human approval.

威胁模型：L3 是灰色命令的**软复核层**（best-effort），不是硬安全边界——
前缀匹配可被空格/引号/链式拼写绕过（与 L1 早期同类问题），硬安全由 L1/L4 兜底。
状态机语义：gate 持有待决动作与状态；check() 对已 APPROVED 的动作放行、
已 REJECTED 的拦截、新动作按前缀判定；approve()/reject() 仅在存在 PENDING
动作时有效并迁移到终态。接线契约：mock 模式接线方必须传 auto_approve=True。
"""

from enum import Enum

from safe_swe_lite.agent.protocol import Action
from safe_swe_lite.guardrails.checker import LAYER_L3, GuardrailDecision

DEFAULT_REQUIRE_APPROVAL = ["git push", "pip install", "npm publish", "kubectl delete", "rm "]


class HitlState(str, Enum):
    NO_INTERVENTION = "no_intervention"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class HitlGate:
    def __init__(self, require_approval=None):
        if require_approval is None:
            require_approval = DEFAULT_REQUIRE_APPROVAL
        self.require_approval = require_approval
        self._pending_action: Action | None = None
        self._state: HitlState = HitlState.NO_INTERVENTION

    def check(self, action: Action, auto_approve: bool = False) -> GuardrailDecision:
        # 同一动作已决：尊重既有终态（approve 后重查放行 / reject 后重查拦截）
        if self._pending_action == action:
            if self._state == HitlState.APPROVED:
                return GuardrailDecision(blocked=False, layer=LAYER_L3,
                                         hitl_state=HitlState.APPROVED, reason="approved by human")
            if self._state == HitlState.REJECTED:
                return GuardrailDecision(blocked=True, layer=LAYER_L3,
                                         hitl_state=HitlState.REJECTED, reason="rejected by human")
        if action.name != "run_command":
            return GuardrailDecision(blocked=False, hitl_state=HitlState.NO_INTERVENTION)
        command = action.parameters.get("command", "")
        if not any(command.startswith(p) for p in self.require_approval):
            return GuardrailDecision(blocked=False, hitl_state=HitlState.NO_INTERVENTION)
        # 新待决动作：覆盖旧的未决动作
        self._pending_action = action
        if auto_approve:
            self._state = HitlState.APPROVED
            return GuardrailDecision(blocked=False, layer=LAYER_L3, hitl_state=HitlState.APPROVED,
                                     reason="auto-approved (mock mode)")
        self._state = HitlState.PENDING
        return GuardrailDecision(blocked=True, layer=LAYER_L3, hitl_state=HitlState.PENDING,
                                 reason=f"'{command}' requires human approval")

    def approve(self) -> GuardrailDecision:
        if self._state != HitlState.PENDING or self._pending_action is None:
            return GuardrailDecision(blocked=False, hitl_state=HitlState.NO_INTERVENTION,
                                     reason="no pending action to approve")
        self._state = HitlState.APPROVED
        return GuardrailDecision(blocked=False, layer=LAYER_L3, hitl_state=HitlState.APPROVED)

    def reject(self) -> GuardrailDecision:
        if self._state != HitlState.PENDING or self._pending_action is None:
            return GuardrailDecision(blocked=True, hitl_state=HitlState.NO_INTERVENTION,
                                     reason="no pending action to reject")
        self._state = HitlState.REJECTED
        return GuardrailDecision(blocked=True, layer=LAYER_L3, hitl_state=HitlState.REJECTED,
                                 reason="rejected by human")
