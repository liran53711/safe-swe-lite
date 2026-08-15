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


def parse_action(response: dict) -> Action:
    """Parse a model response dict into an Action."""
    if "message" not in response:
        raise ProtocolError("LLM output missing 'message' key")

    try:
        data = json.loads(response["message"])
    except json.JSONDecodeError as exc:
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
