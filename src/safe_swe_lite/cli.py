"""CLI entry point: run / auth / web."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from pydantic import BaseModel

from safe_swe_lite.agent.loop import Agent
from safe_swe_lite.config.loader import load_config
from safe_swe_lite.guardrails import GuardrailChain
from safe_swe_lite.llm.mock import MockLLM
from safe_swe_lite.tools import Dispatcher


def _jsonable(obj):
    """Recursively convert trace objects to JSON-serializable structures."""
    if isinstance(obj, BaseModel):
        return _jsonable(obj.model_dump(mode="json"))
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if hasattr(obj, "__dataclass_fields__"):
        return _jsonable(asdict(obj))
    return obj


def run_task_from_file(task_file: Path, use_real: bool = False) -> dict:
    """Run a task file and return the JSON-serializable result dict.

    use_real=True 时使用 LiteLLMProvider（真实 LLM）。
    设计决策：真实模式下 guardrail 的 auto_approve 保持 True——CLI 没有交互批准
    通道（人工批准属于 WebUI/终端），因此打印提示
    "real LLM mode: HITL auto-approve enabled for CLI"，真正的 HITL 批准留给未来。
    """
    path = Path(task_file)
    if not path.exists():
        raise FileNotFoundError(f"task file not found: {path}")
    try:
        task_data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"task file is not valid JSON: {e}") from e
    if not isinstance(task_data, dict):
        raise TypeError("task file top-level must be a JSON object")
    if "task" not in task_data:
        raise ValueError("task file missing required key 'task'")
    config = load_config()
    workspace = Path(task_data.get("workspace", config.workspace))
    if use_real:
        from safe_swe_lite.llm.litellm_provider import LiteLLMProvider

        model = LiteLLMProvider()
        print("real LLM mode: HITL auto-approve enabled for CLI", file=sys.stderr)
    else:
        model = MockLLM(outputs=task_data.get("mock_outputs", config.model.mock_outputs))
    tools = Dispatcher(workspace=workspace)
    # CLI 无交互批准通道：auto_approve=True 避免 HITL 阻塞（接线契约，真实模式决策见 docstring）
    chain = GuardrailChain(
        workspace=workspace,
        require_approval=config.guardrails.require_approval or None,
        banned_symbols=config.guardrails.banned_symbols or None,
        auto_approve=True,
    )
    agent = Agent(
        model=model,
        tools=tools,
        guardrail=chain,
        max_steps=task_data.get("max_steps", config.max_turns),
    )
    try:
        result = agent.run(task_data["task"])
    except IndexError:
        return {
            "exit_status": "mock_outputs_exhausted",
            "error": "MockLLM outputs exhausted: the scripted responses ran out before the agent finished",
            "trace": _jsonable(agent._trace),
        }
    return _jsonable(result)


def main() -> None:
    parser = argparse.ArgumentParser(prog="safe-swe-lite")
    sub = parser.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser(
        "run", help="run a task file (mock LLM by default, --real for a live model)"
    )
    run_p.add_argument("task_file", type=Path)
    run_p.add_argument("--real", action="store_true", help="use a real LLM instead of MockLLM")

    sub.add_parser("web", help="start the web UI")

    sub.add_parser("auth", help="configure API key (real LLM mode)")

    args = parser.parse_args()
    if args.command == "run":
        result = run_task_from_file(args.task_file, use_real=args.real)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "web":
        try:
            from safe_swe_lite.web.app import run_server
        except ImportError:
            parser.error("web UI is not available yet (lands in a later task); run 'safe-swe-lite run <task.json>' instead")
        run_server()
    elif args.command == "auth":
        try:
            from safe_swe_lite.llm.litellm_provider import auth_command
        except ImportError:
            parser.error('auth requires the llm extras; install the llm extras: pip install -e ".[llm]"')
        auth_command()


if __name__ == "__main__":
    main()
