"""FastAPI web app: mock-only demo endpoints + static UI."""

import json
import os
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from safe_swe_lite.agent.loop import Agent
from safe_swe_lite.cli import _jsonable
from safe_swe_lite.guardrails import GuardrailChain
from safe_swe_lite.llm.mock import MockLLM
from safe_swe_lite.tools import Dispatcher

STATIC_DIR = Path(__file__).resolve().parent / "static"

# 线上强制 mock：真实 LLM 需显式开启
ALLOW_REAL_LLM = os.getenv("SAFE_SWE_LITE_ALLOW_REAL_LLM", "false").lower() == "true"


def _repo_root() -> Path:
    """Locate the repo root across layouts.

    优先级：环境变量覆盖 > 打包的 examples 包（wheel/site-packages 布局）>
    源树相对路径（parents[3] 只在 src 布局成立）。
    """
    override = os.getenv("SAFE_SWE_LITE_ROOT")
    if override:
        return Path(override)
    try:
        import examples
        # namespace package（无 __init__.py 的裸 examples/ 目录）时 __file__ 为 None——
        # 该场景必须回退，否则 Path(None) 抛 TypeError 使整个模块无法导入
        if getattr(examples, "__file__", None):
            return Path(examples.__file__).resolve().parent.parent
    except ImportError:
        pass
    return Path(__file__).resolve().parents[3]


REPO_ROOT = _repo_root()


def _run_task(task_name: str) -> dict:
    """Run a task file's mock script against a TEMPORARY COPY of the sample project.

    workspace 契约（examples/tasks/README.md）：fix_bug 会真实编辑文件，
    每次 demo 必须在临时副本上运行，绝不修改 tracked 的 sample project。
    """
    task_file = REPO_ROOT / "examples" / "tasks" / f"{task_name}.json"
    task = json.loads(task_file.read_text(encoding="utf-8"))
    sample = REPO_ROOT / "examples" / "sample_project"
    with tempfile.TemporaryDirectory(prefix="safe-swe-lite-demo-") as tmpdir:
        workspace = Path(tmpdir) / "sample_project"
        shutil.copytree(sample, workspace)
        model = MockLLM(outputs=task["mock_outputs"])
        tools = Dispatcher(workspace=workspace)
        chain = GuardrailChain(workspace=workspace, auto_approve=True)
        agent = Agent(model=model, tools=tools, guardrail=chain, max_steps=task["max_steps"])
        try:
            result = agent.run(task["task"])
        except IndexError:
            return {
                "exit_status": "mock_outputs_exhausted",
                "error": "MockLLM outputs exhausted: the scripted responses ran out before the agent finished",
                "trace": _jsonable(agent._trace),
            }
        return _jsonable(result)


def create_app() -> FastAPI:
    app = FastAPI(title="SafeSWE-Lite")

    @app.get("/api/health")
    def health():
        return {"status": "ok", "mock_only": not ALLOW_REAL_LLM}

    @app.post("/api/demo/fix-bug")
    def fix_bug():
        return _run_task("fix_bug")

    @app.post("/api/demo/blocked")
    def blocked():
        return _run_task("blocked_dangerous_action")

    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
    return app


def run_server(port: int | None = None):
    import uvicorn
    port = port or int(os.getenv("PORT", "8000"))
    uvicorn.run(create_app(), host="0.0.0.0", port=port)
