from safe_swe_lite.memory.scoring import score_observation
from safe_swe_lite.memory.store import MemoryStore


def test_score_guardrail_block_is_max():
    assert score_observation({"kind": "guardrail", "data": {"blocked": True}}) == 10


def test_score_test_failure_high():
    assert score_observation({"kind": "validation", "data": {"passed": False}}) == 9


def test_score_file_read_medium():
    assert score_observation({"kind": "file_read"}) == 5


def test_score_trivial_low():
    assert score_observation({"kind": "command", "data": {"output": "installed"}}) == 1


def test_memory_assemble_keeps_recent_window_raw():
    mem = MemoryStore(recent_window=3)
    for i in range(10):
        mem.add_message({"role": "user", "content": f"msg{i}"})
    assembled = mem.assemble()
    assert "msg9" in str(assembled)
    assert "msg0" not in str(assembled)  # 远古消息被摘要替代


def test_memory_assemble_contains_summary_of_old():
    mem = MemoryStore(recent_window=2)
    for i in range(5):
        mem.add_message({"role": "user", "content": f"msg{i}"})
    assembled = mem.assemble()
    text = str(assembled)
    assert "summary" in text.lower()


def test_memory_full_history_untouched():
    mem = MemoryStore(recent_window=1)
    for i in range(5):
        mem.add_message({"role": "user", "content": f"msg{i}"})
    assert len(mem.messages) == 5  # 全量保留，assemble 只裁剪副本


def test_assemble_picks_high_score_old_messages():
    mem = MemoryStore(recent_window=2, top_summary=1)
    mem.add_message({"role": "user", "content": "architecture: auth in src/auth.py", "kind": "file_read"})  # score 5
    mem.add_message({"role": "user", "content": "install log", "kind": "command"})  # score 1
    mem.add_message({"role": "user", "content": "recent1"})
    mem.add_message({"role": "user", "content": "recent2"})
    assembled = str(mem.assemble())
    assert "auth" in assembled      # 高分消息进摘要
    assert "install log" not in assembled  # 低分消息被挤出


def test_assemble_summary_is_system_role():
    mem = MemoryStore(recent_window=1, top_summary=1)
    mem.add_message({"role": "user", "content": "important", "kind": "guardrail"})
    mem.add_message({"role": "user", "content": "recent"})
    assembled = mem.assemble()
    assert assembled[0]["role"] == "system"


def test_recent_window_zero_returns_full_history():
    mem = MemoryStore(recent_window=0)
    mem.add_message({"role": "user", "content": "m1"})
    assembled = mem.assemble()
    assert len(assembled) == 1  # 无垃圾摘要
