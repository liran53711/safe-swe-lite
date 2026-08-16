import hashlib
from pathlib import Path

from fastapi.testclient import TestClient

from safe_swe_lite.web.app import REPO_ROOT, create_app


def _file_hash(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_health_endpoint():
    client = TestClient(create_app())
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_index_served():
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200


def test_fix_bug_demo_endpoint_runs_mock():
    client = TestClient(create_app())
    response = client.post("/api/demo/fix-bug")
    assert response.status_code == 200
    data = response.json()
    assert data["exit_status"] in ("submitted", "max_steps_exceeded")
    assert isinstance(data["trace"], list)


def test_blocked_demo_endpoint_blocks_action():
    client = TestClient(create_app())
    response = client.post("/api/demo/blocked")
    assert response.status_code == 200
    data = response.json()
    assert data["exit_status"] == "guardrail_exhausted"
    assert any(t.get("kind") == "guardrail" for t in data["trace"])


def test_demo_does_not_modify_tracked_sample():
    auth = REPO_ROOT / "examples" / "sample_project" / "src" / "auth.py"
    before = _file_hash(auth)
    client = TestClient(create_app())
    client.post("/api/demo/fix-bug")
    client.post("/api/demo/fix-bug")
    assert _file_hash(auth) == before  # 临时副本隔离：原文件哈希不变
