"""Deterministic importance scoring for observations."""


def score_observation(obs: dict) -> int:
    kind = obs.get("kind", "")
    if kind == "guardrail":
        return 10
    if kind == "validation":
        return 9 if obs.get("data", {}).get("passed") is False else 1
    if kind == "file_read":
        return 5
    return 1
