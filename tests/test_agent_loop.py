from safe_swe_lite.agent.loop import Agent
from safe_swe_lite.agent.protocol import Action
from safe_swe_lite.llm.mock import MockLLM


class FakeTools:
    def __init__(self):
        self.executed = []

    def execute(self, action: Action):
        self.executed.append(action)
        return {"output": f"executed {action.name}", "exit_code": 0}


def submit_message(result="done"):
    return {"message": f'{{"action": "submit", "parameters": {{"result": "{result}"}}}}'}


def test_agent_stops_on_submit():
    model = MockLLM(outputs=[submit_message()])
    agent = Agent(model=model, tools=FakeTools(), max_steps=10)
    result = agent.run("fix the bug")
    assert result["exit_status"] == "submitted"
    assert result["submission"] == "done"


def test_agent_executes_actions_before_submit():
    model = MockLLM(outputs=[
        {"message": '{"action": "read_file", "parameters": {"path": "a.py"}}'},
        submit_message("ok"),
    ])
    tools = FakeTools()
    agent = Agent(model=model, tools=tools, max_steps=10)
    agent.run("task")
    assert [a.name for a in tools.executed] == ["read_file"]


def test_agent_stops_at_max_steps():
    model = MockLLM(outputs=[
        {"message": '{"action": "read_file", "parameters": {"path": "a.py"}}'}
    ] * 100)
    agent = Agent(model=model, tools=FakeTools(), max_steps=3)
    result = agent.run("task")
    assert result["exit_status"] == "max_steps_exceeded"


def test_agent_recovers_from_one_format_error():
    model = MockLLM(outputs=[
        {"message": "this is not json"},
        submit_message("recovered"),
    ])
    agent = Agent(model=model, tools=FakeTools(), max_steps=10)
    result = agent.run("task")
    assert result["exit_status"] == "submitted"


def test_agent_stops_after_consecutive_format_errors():
    model = MockLLM(outputs=[{"message": "bad"}] * 10)
    agent = Agent(model=model, tools=FakeTools(), max_steps=10, max_format_errors=3)
    result = agent.run("task")
    assert result["exit_status"] == "format_error"


class AlwaysBlockGuardrail:
    def check(self, action):
        class D:
            blocked = True
            layer = 1
            reason = "test block"
        return D()


def test_blocked_action_not_executed_and_loop_continues():
    model = MockLLM(outputs=[
        {"message": '{"action": "run_command", "parameters": {"command": "bad"}}'},
        submit_message("ok"),
    ])
    tools = FakeTools()
    agent = Agent(model=model, tools=tools, guardrail=AlwaysBlockGuardrail(), max_steps=10)
    result = agent.run("task")
    assert result["exit_status"] == "submitted"
    assert tools.executed == []  # 被拦截的动作从未执行


def test_blocked_actions_do_not_consume_steps():
    model = MockLLM(outputs=[
        {"message": '{"action": "run_command", "parameters": {"command": "bad"}}'},
        submit_message("ok"),
    ])
    tools = FakeTools()
    agent = Agent(model=model, tools=tools, guardrail=AlwaysBlockGuardrail(), max_steps=1)
    result = agent.run("task")
    assert result["exit_status"] == "submitted"  # 拦截不计步，1 步内完成


def test_always_blocked_terminates_with_guardrail_exhausted():
    model = MockLLM(outputs=[
        {"message": '{"action": "run_command", "parameters": {"command": "bad"}}'}
    ] * 100)
    agent = Agent(model=model, tools=FakeTools(), guardrail=AlwaysBlockGuardrail(), max_steps=10)
    result = agent.run("task")
    assert result["exit_status"] == "guardrail_exhausted"
