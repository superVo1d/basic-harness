"""execute_code: run a Python snippet in the session workspace.

Plain subprocess, NOT a sandbox: the child gets a scrubbed environment and runs
with the workspace as its cwd, but there is no filesystem/network isolation. Treat
this as guardrails for a local personal agent, not a security boundary.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys

from agent.registry import tool
from agent.workspace import workspace_dir

logger = logging.getLogger(__name__)

TIMEOUT = 30
MAX_OUTPUT = 8000

# env names safe to pass to the child (by prefix)
_SAFE_ENV_PREFIXES = (
    "PATH", "HOME", "USER", "LANG", "LC_", "TERM", "TMPDIR", "TMP", "TEMP",
    "SHELL", "VIRTUAL_ENV", "CONDA",
)
# substrings that mark a secret -> dropped regardless of the whitelist
_SECRET_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD",
                   "PASSWD", "CREDENTIAL", "AUTH", "SESSION")


EXECUTE_CODE_SCHEMA = {
    "type": "function",
    "name": "execute_code",
    "description": (
        "Run a short Python snippet. Use for computation, data munging or generating "
        "files in the session workspace. The code runs with the workspace as its cwd; "
        "files written there persist as artifacts. Only stdout/stderr is returned, so "
        "keep output short. Not a real sandbox (no network/filesystem isolation)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python source to execute."},
            "timeout": {"type": "integer", "default": TIMEOUT,
                        "description": "Seconds before the run is killed."},
        },
        "required": ["code"],
    },
}


def _is_secret_env_name(name: str) -> bool:
    upper = name.upper()
    return any(marker in upper for marker in _SECRET_MARKERS)


def _scrub_child_env(source_env: dict[str, str]) -> dict[str, str]:
    """Whitelisted, secret-free environment for the child process."""
    env: dict[str, str] = {}
    for name, value in source_env.items():
        if _is_secret_env_name(name):
            continue
        if name.startswith(_SAFE_ENV_PREFIXES):
            env[name] = value
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _clip(text: str) -> str:
    if len(text) <= MAX_OUTPUT:
        return text
    half = MAX_OUTPUT // 2
    return f"{text[:half]}\n... [{len(text) - MAX_OUTPUT} chars omitted] ...\n{text[-half:]}"


def _has_python() -> bool:
    return bool(sys.executable)


@tool(name="execute_code", schema=EXECUTE_CODE_SCHEMA, check_fn=_has_python)
def execute_code(code: str, timeout: int = TIMEOUT) -> str:
    """Run a Python snippet with the session workspace as cwd."""
    workspace = workspace_dir()
    script = workspace / "_cell.py"
    script.write_text(code, encoding="utf-8")
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(workspace),
            env=_scrub_child_env(dict(os.environ)),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"timeout after {timeout}s"}, ensure_ascii=False)
    finally:
        script.unlink(missing_ok=True)

    return json.dumps({
        "exit_code": proc.returncode,
        "stdout": _clip(proc.stdout or ""),
        "stderr": _clip(proc.stderr or ""),
    }, ensure_ascii=False)
