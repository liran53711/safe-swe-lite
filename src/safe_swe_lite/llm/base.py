"""Model protocol: the single interface the agent uses to talk to any LLM."""

from typing import Protocol


class Model(Protocol):
    """Anything implementing query() can drive the agent loop."""

    def query(self, messages: list[dict], **kwargs) -> dict:
        """Return a model response dict.

        The response must contain a "message" key whose value is a JSON
        string parseable by safe_swe_lite.agent.protocol.parse_action.
        """
        ...
