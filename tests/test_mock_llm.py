import pytest

from safe_swe_lite.llm.mock import MockLLM


def test_mock_llm_plays_outputs_in_sequence():
    model = MockLLM(outputs=[
        {"message": '{"action": "read_file", "parameters": {"path": "a.py"}}'},
        {"message": '{"action": "submit", "parameters": {"result": "done"}}'},
    ])
    first = model.query([{"role": "user", "content": "task"}])
    second = model.query([{"role": "user", "content": "task"}])
    assert first["message"].startswith('{"action": "read_file"')
    assert second["message"].startswith('{"action": "submit"')


def test_mock_llm_exhausted_outputs_raises():
    model = MockLLM(outputs=[{"message": '{"action": "submit", "parameters": {}}'}])
    model.query([])
    with pytest.raises(IndexError):
        model.query([])


def test_mock_llm_default_empty_outputs():
    model = MockLLM()
    with pytest.raises(IndexError):
        model.query([])


def test_mock_llm_ignores_input_messages():
    model = MockLLM(outputs=[{"message": '{"action": "submit", "parameters": {}}'}])
    result = model.query([{"role": "user", "content": "anything at all"}], temperature=0.0)
    assert result["message"].startswith('{"action": "submit"')
