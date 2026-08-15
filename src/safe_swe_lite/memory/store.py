"""Tiered context memory: full history kept; assemble() trims a copy.

摘要选取策略：旧窗口中按 score_observation 取分数最高的 top_summary
条消息进入摘要（不按时间序）——架构级信息（file_read=5）和失败信号
（validation failed=9）比安装日志（=1）更值得保留。
"""

from dataclasses import dataclass, field

from safe_swe_lite.memory.scoring import score_observation

SUMMARY_TAIL_CHARS = 80


@dataclass
class MemoryStore:
    recent_window: int = 10
    top_summary: int = 5
    messages: list = field(default_factory=list)

    def add_message(self, message: dict) -> None:
        """Append a message. Optional 'kind' key enables scoring:
        guardrail / validation / file_read / command."""
        self.messages.append(message)

    def assemble(self) -> list[dict]:
        if self.recent_window <= 0 or len(self.messages) <= self.recent_window:
            return list(self.messages)
        old = self.messages[:-self.recent_window]
        recent = self.messages[-self.recent_window:]
        # 升序排序后取末尾 n 条：分数最高的进摘要，同分时保留较新的消息
        picked = sorted(old, key=score_observation)[-self.top_summary:]
        summary = {
            "role": "system",
            "content": f"[context summary of {len(old)} earlier messages, top {len(picked)} by importance] "
                       + " | ".join(self._summarize(i, m) for i, m in enumerate(picked)),
        }
        return [summary, *recent]

    @staticmethod
    def _summarize(index: int, m: dict) -> str:
        content = str(m.get("content", ""))
        kind = m.get("kind", "?")
        tail = content[-SUMMARY_TAIL_CHARS:] + ("..." if len(content) > SUMMARY_TAIL_CHARS else "")
        return f"[{kind}] {tail}"
