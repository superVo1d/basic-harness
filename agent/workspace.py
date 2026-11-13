"""Per-session workspace directory for code execution and artifacts."""

from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path

from agent.config import BASE_PATH


_current_session: ContextVar[str] = ContextVar("current_session", default="default")


def set_current_session(session_id: str):
    """Bind the session whose workspace tools should use; returns a reset token."""
    return _current_session.set(session_id or "default")


def reset_current_session(token) -> None:
    _current_session.reset(token)


def workspace_path(session_id: str) -> Path:
    """Workspace dir for a given session (created on demand)."""
    path = BASE_PATH / "data" / "workspaces" / (session_id or "default")
    path.mkdir(parents=True, exist_ok=True)
    return path


def workspace_dir() -> Path:
    """Current session's workspace (created on demand)."""
    return workspace_path(_current_session.get())
