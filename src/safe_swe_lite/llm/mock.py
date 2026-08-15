"""Deterministic mock LLM: plays pre-recorded outputs in sequence."""

from dataclasses import dataclass, field


@dataclass
class MockLLM:
    outputs: list[dict] = field(default_factory=list)
    _index: int = field(default=-1, init=False, repr=False, compare=False)

    def query(self, messages: list[dict], **kwargs) -> dict:
        self._index += 1
        return self.outputs[self._index]
