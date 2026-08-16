"""Agent main loop: organize context -> query LLM -> parse -> guard -> execute -> record."""

from contextlib import suppress
from dataclasses import dataclass, field

from safe_swe_lite.agent.protocol import ProtocolError, parse_action

SYSTEM_PROMPT = (
    "You are a coding agent operating inside a project workspace. "
    "You can take actions by responding with ONLY a single JSON object — no prose, no code blocks. "
    'Format: {"action": "<tool_name>", "parameters": {...}}. '
    "Available actions: "
    "read_file (parameters: path, offset?, limit?) — read a file; "
    "write_file (path, content) — create or overwrite a file; "
    "edit_file (path, old_string, new_string) — replace a unique string in a file; "
    "run_command (command) — run a shell command, e.g. pytest; "
    "search_pattern (pattern) — search file contents; "
    "list_files () — list the workspace tree; "
    "submit (result) — finish the task and report the result. "
    "Think step by step: read relevant files first, run tests to observe failures, "
    "edit code, re-run tests, and submit when done."
)


def format_observation(result) -> str:
    """Format a tool result for the LLM observation message.

    Contract for Task 5: the dispatcher returns a ToolResult with
    success/output/error fields. Real ToolResult objects will define
    __str__ or be handled here; plain dicts (current test doubles) fall
    through unchanged.
    """
    if isinstance(result, dict):
        return str(result)
    return str(result)


@dataclass
class Agent:
    model: object
    tools: object
    max_steps: int = 50
    max_format_errors: int = 3
    max_blocked: int = 5
    guardrail: object = None
    validators: object = None  # 后续 Task 接入（feedback 维度）
    memory: object = None  # 后续 Task 接入（memory 维度）
    _messages: list = field(default_factory=list)
    _trace: list = field(default_factory=list)

    def run(self, task: str, on_step=None) -> dict:
        """Run the agent loop.

        on_step(action, result, decision) — 每步执行后回调（可选）：
        工具执行后带 result（decision 为 None），guardrail 拦截时带
        decision（result 为 None）。回调内异常被吞掉，打印逻辑错误
        不应杀死 agent 循环。
        """

        def notify(action, result=None, decision=None):
            if on_step is None:
                return
            # 打印逻辑错误不应杀死 agent 循环：异常被吞掉
            with suppress(Exception):
                on_step(action, result, decision)

        self._messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]
        self._trace = []
        steps = 0
        format_errors = 0
        blocked = 0
        while steps < self.max_steps:
            try:
                response = self.model.query(self._messages)
                action = parse_action(response)
                format_errors = 0
            except ProtocolError as e:
                format_errors += 1
                if format_errors >= self.max_format_errors:
                    return {"exit_status": "format_error", "error": str(e), "trace": self._trace}
                self._messages.append({"role": "user", "content": f"Format error: {e}. Respond with valid JSON."})
                continue
            self._messages.append({"role": "assistant", "content": action.name})
            if action.name == "submit":
                return {
                    "exit_status": "submitted",
                    "submission": str(action.parameters.get("result", "")),
                    "trace": self._trace,
                }
            if self.guardrail is not None:
                decision = self.guardrail.check(action)
                if decision is not None and decision.blocked:
                    blocked += 1
                    if blocked >= self.max_blocked:
                        return {
                            "exit_status": "guardrail_exhausted",
                            "reason": "too many blocked actions",
                            "trace": self._trace,
                        }
                    self._messages.append({
                        "role": "user",
                        "content": f"Action blocked by guardrail layer {decision.layer}: {decision.reason}",
                    })
                    trace_data = decision.model_dump(mode="json") if hasattr(decision, "model_dump") else decision
                    self._trace.append({"kind": "guardrail", "data": trace_data})
                    notify(action, None, decision)
                    continue
            result = self.tools.execute(action)
            self._messages.append({"role": "user", "content": f"Observation: {format_observation(result)}"})
            self._trace.append({"kind": "observation", "data": result})
            notify(action, result, None)
            steps += 1
        return {"exit_status": "max_steps_exceeded", "trace": self._trace}
