"""Guardrail chain: L1 -> L2 -> L3 -> L4, first block wins."""

from safe_swe_lite.agent.protocol import Action
from safe_swe_lite.guardrails.checker import GuardrailDecision, StaticChecker
from safe_swe_lite.guardrails.code_scanner import CodeScanner
from safe_swe_lite.guardrails.hitl import HitlGate
from safe_swe_lite.guardrails.scope_fence import ScopeFence


class GuardrailChain:
    def __init__(self, workspace, require_approval=None, banned_symbols=None, auto_approve: bool = False):
        self.auto_approve = auto_approve
        self.layers = [
            StaticChecker(),
            ScopeFence(workspace=workspace),
            HitlGate(require_approval=require_approval),
            CodeScanner(banned_symbols=banned_symbols),
        ]

    def check(self, action: Action, auto_approve: bool | None = None) -> GuardrailDecision:
        if auto_approve is None:
            auto_approve = self.auto_approve
        passed = GuardrailDecision(blocked=False)
        for layer in self.layers:
            if isinstance(layer, HitlGate):
                decision = layer.check(action, auto_approve=auto_approve)
            else:
                decision = layer.check(action)
            if decision.blocked:
                return decision
            # 全层放行时透传带 HITL 状态的放行决策（如灰命令 auto-approved），
            # 否则返回裸放行决策，保证调用方能读到 approved/pending 语义
            if decision.hitl_state:
                passed = decision
        return passed
