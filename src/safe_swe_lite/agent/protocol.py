"""JSON action protocol: the only interface between LLM output and the harness."""

import json

from pydantic import BaseModel, Field

VALID_ACTIONS = {
    "read_file",
    "write_file",
    "edit_file",
    "run_command",
    "search_pattern",
    "list_files",
    "submit",
}


class ProtocolError(Exception):
    """Raised when LLM output cannot be parsed into a valid Action."""


class Action(BaseModel):
    name: str
    parameters: dict = Field(default_factory=dict)


def _strip_fences(message: str) -> str:
    """Strip markdown code fences (```json {...} ```)."""
    message = message.strip()
    if not message.startswith("```"):
        return message
    lines = message.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_balanced_objects(text: str):
    """Yield every balanced top-level {...} span in text, in order.

    Real LLMs prepend prose or embed code blocks (whose braces are NOT valid
    action JSON). Yielding all candidates lets the caller try each one.
    """
    i = 0
    n = len(text)
    while i < n:
        start = text.find("{", i)
        if start == -1:
            return
        depth = 0
        in_string = False
        escape = False
        end = -1
        for j in range(start, n):
            ch = text[j]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
            elif ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        if end == -1:
            return
        yield text[start : end + 1]
        i = end + 1


def parse_action(response: dict) -> Action:
    """Parse a model response dict into an Action."""
    message = response.get("message", "")
    if not isinstance(message, str):
        raise ProtocolError("LLM output is missing 'message' key")
    if "message" not in response:
        raise ProtocolError("LLM output missing 'message' key")

    message = _strip_fences(message)
    try:
        data = json.loads(message)
    except json.JSONDecodeError as exc:
        # 容错第二层：逐个尝试所有平衡 {...} 对象（LLM 的回复可能含
        # 解释文字或代码块——代码块的括号不是合法 action JSON，跳过）
        for candidate in _extract_balanced_objects(message):
            try:
                data = json.loads(candidate)
                break
            except json.JSONDecodeError:
                continue
        else:
            raise ProtocolError(f"LLM output is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ProtocolError("LLM output must be a JSON object")
    if "action" not in data:
        raise ProtocolError("LLM output missing 'action' key")

    name = data["action"]
    if name not in VALID_ACTIONS:
        raise ProtocolError(f"unknown action '{name}'")

    parameters = data.get("parameters", {})
    if not isinstance(parameters, dict):
        raise ProtocolError("'parameters' must be an object")

    return Action(name=name, parameters=parameters)
