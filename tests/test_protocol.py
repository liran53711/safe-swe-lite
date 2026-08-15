import pytest

from safe_swe_lite.agent.protocol import Action, ProtocolError, parse_action


def test_parse_valid_action():
    response = {"message": '{"action": "read_file", "parameters": {"path": "a.py"}}'}
    action = parse_action(response)
    assert action == Action(name="read_file", parameters={"path": "a.py"})


def test_parse_unknown_tool_raises():
    response = {"message": '{"action": "fly_to_moon", "parameters": {}}'}
    with pytest.raises(ProtocolError, match="unknown action"):
        parse_action(response)


def test_parse_invalid_json_raises():
    with pytest.raises(ProtocolError, match="not valid JSON"):
        parse_action({"message": "not json at all"})


def test_parse_missing_action_key_raises():
    with pytest.raises(ProtocolError, match="missing 'action'"):
        parse_action({"message": '{"parameters": {}}'})


def test_parse_missing_message_key_raises():
    with pytest.raises(ProtocolError, match="missing 'message'"):
        parse_action({})


def test_parse_missing_parameters_defaults_to_empty():
    action = parse_action({"message": '{"action": "submit"}'})
    assert action.parameters == {}


def test_parse_non_dict_parameters_raises():
    with pytest.raises(ProtocolError, match="'parameters' must be an object"):
        parse_action({"message": '{"action": "read_file", "parameters": "bad"}'})


VALID_NAMES = {
    "read_file",
    "write_file",
    "edit_file",
    "run_command",
    "search_pattern",
    "list_files",
    "submit",
}


def test_all_seven_tool_names_accepted():
    for name in VALID_NAMES:
        response = {"message": f'{{"action": "{name}", "parameters": {{}}}}'}
        assert parse_action(response).name == name
