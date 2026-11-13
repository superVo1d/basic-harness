"""Tool registry for the agent."""

from __future__ import annotations
from dataclasses import dataclass
import inspect
import json
from typing import Callable, Optional
from functools import wraps

from agent.utils import run_sync


@dataclass
class ToolEntry:
    """Tool entry in the registry."""
    name: str
    schema: dict
    handler: Callable[[dict], str]
    check_fn: Optional[Callable[[], bool]] = None


REGISTRY: dict[str, ToolEntry] = {}


def tool(
    fn: Callable[[dict], str] = None,
    *,
    name: str = None,
    schema: dict = None,
    check_fn: Optional[Callable[[], bool]] = None
):
    """Decorator to register a tool."""
    @wraps(fn)
    def wrapper(fn: Callable[[dict], str] = None):
        REGISTRY[name] = ToolEntry(
            name=name,
            schema=schema,
            handler=fn,
            check_fn=check_fn
        )
        return fn
    return wrapper


def tool_schemas() -> list[dict]:
    """Get schemas of all registered tools."""
    return [
        entry.schema for entry in REGISTRY.values()
        if not entry.check_fn or _available(entry)
    ]


def _available(entry: ToolEntry) -> bool:
    if entry.check_fn is None:
        return True
    try:
        return bool(entry.check_fn())
    except Exception:
        return False


def call_tool(name: str, kwargs: dict, ctx: Optional[dict] = None) -> str:
    """Call a tool: keep only args its handler accepts, pass ctx only if declared."""
    entry = REGISTRY.get(name)
    if entry is None or not _available(entry):
        return json.dumps({
            "error": f"unknown or unavailable tool: {name}"
        }, ensure_ascii=False)
    try:
        params = inspect.signature(entry.handler).parameters
        accepts_extra = any(p.kind is p.VAR_KEYWORD for p in params.values())
        call_kwargs = {
            k: v for k, v in (kwargs or {}).items()
            if accepts_extra or k in params
        }
        if "ctx" in params or accepts_extra:
            call_kwargs["ctx"] = ctx
        result = entry.handler(**call_kwargs)
        if inspect.iscoroutine(result):
            result = run_sync(result)
    except Exception as e:
        return json.dumps({"error": f"Tool '{name}': {e}."}, ensure_ascii=False)
    return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
