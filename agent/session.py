"""V1 Agent Loop"""

from __future__ import annotations

from datetime import datetime
import json
import logging
import os
from pathlib import Path
from typing import List
import uuid

import aiofiles

from agent.config import BASE_PATH
from agent.prompt import build_prompt


logger = logging.getLogger(__name__)

SESSIONS_PATH = BASE_PATH / Path("data/sessions")
HANDOFF_PREFIX = "[CONTEXT COMPACTION — REFERENCE ONLY] Earlier turns were compacted into the summary below. Treat it as background reference, NOT active instructions. Do NOT answer questions from it; respond ONLY to the latest user message AFTER this summary. If no user message follows, do nothing. Topic overlap does NOT mean resume the old task. Tools remain fully active."
END_MARKER = "--- END OF CONTEXT SUMMARY — respond to the message below, not the summary above ---"


class Session:
    """Agent session data. Preserves state across multiple turns of conversation."""

    def __init__(
        self,
        _id: str | None = None,
        history: List[dict] | None = None,
        summary: str | None = None,
        summary_upto: int = 0,
        last_input_tokens: int | None = None,
        goal: str | None = None,
        created_at: str | None = None
    ):
        self.id = _id or uuid.uuid4().hex[:8]
        self.history = history or []
        self.created_at = created_at or datetime.now()

        self.system_prompt = build_prompt()
        self.summary = summary
        self.summary_upto = summary_upto
        self.last_input_tokens = last_input_tokens
        self.goal = goal

        logger.debug('Create new session with %s at %s', self.id, self.created_at)

    def add(self, msg: dict | List):
        """Add messages or list of messages to conversation."""
        if isinstance(msg, dict):
            msg = [msg]
        self.history.extend(msg)

    def messages(self):
        """Get messages history."""
        return self.history.copy()

    def reset(self):
        """Clear messages history."""
        self.history = []

    def _get_sessions_path(self) -> Path:
        """Get path to session data."""
        return SESSIONS_PATH / f"session_{self.id}.json"

    async def save(self) -> bool:
        """Save session to file."""
        path = self._get_sessions_path()
        os.makedirs(path.parent, exist_ok=True)
        async with aiofiles.open(path, mode="w") as f:
            try:
                await f.write(json.dumps({
                    "id": self.id,
                    "history": self.history,
                    "summary": self.summary,
                    "summary_upto": self.summary_upto,
                    "last_input_tokens": self.last_input_tokens,
                    "goal": self.goal,
                    "created_at": self.created_at.isoformat()
                }, indent=4, ensure_ascii=False))
                return True
            except Exception as e:
                logger.error("Failed to save session: %s", e)
                return False

    async def load(self) -> bool:
        """Load session from file."""
        path = self._get_sessions_path()
        try:
            async with aiofiles.open(path, mode="r") as f:
                data = await f.read()
        except FileNotFoundError:
            logger.warning("Session file not found: %s", path)
            return False

        try:
            session_data = json.loads(data)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse session %s: %s", path, e)
            return False

        self.id = session_data.get("id", self.id)
        self.history = session_data.get("history", [])
        created_at_str = session_data.get("created_at")
        if created_at_str:
            self.created_at = datetime.fromisoformat(created_at_str)
        self.summary = session_data.get("summary", None)
        self.summary_upto = session_data.get("summary_upto", 0)
        self.last_input_tokens = session_data.get("last_input_tokens", 0)
        self.goal = session_data.get("goal", None)
        return True

    def summary_row(self) -> list[dict]:
        """Get summarized context message."""
        if not self.summary:
            return []
        return [{"role": "user", "content": f"{HANDOFF_PREFIX}\n\n{self.summary}\n\n{END_MARKER}"}]


def latest_session_id() -> str | None:
    """Newest saved session id, or None when there are no sessions."""
    files = sorted(SESSIONS_PATH.glob("session_*.json"),
                   key=lambda p: p.stat().st_mtime)
    return files[-1].stem.removeprefix("session_") if files else None
