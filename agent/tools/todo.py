"""Agent To-Do tool."""

from __future__ import annotations
import json
import logging
from typing import List, Optional
import uuid

from agent.registry import tool


logger = logging.getLogger(__name__)


TODO_SCHEMA = {
    "type": "function",
    "name": "todo_list",
    "description": """
        Track a task list for multi-step work (3+ steps). Enumerate every instance
        for 'all N' tasks so none are dropped. Call with no parameters to read the list. List order is priority.
        Only ONE item in_progress at a time. Break large phases into subtasks via parent.
        Mark completed only after the work is verified done. Always returns the full list.
    """,
    "parameters": {
        "type": "object",
        "properties": {
            "todos": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "content": {
                            "type": "string", "description": "Task description"
                        },
                        "status": {
                            "type": "string",
                            "enum": ["pending", "in_progress", "completed", "cancelled"]
                        },
                        "parent": {
                            "type": "string",
                            "description": "Optional id of a parent item"
                            "(nested subtask)."
                        }
                    },
                    "required": ["id", "content", "status"]
                }
            },
            "merge": {
                "type": "boolean",
                "default": False,
                "description": "true: patch existing by id + add new. "
                "false: replace the whole list."
            }
        },
        "required": []
    }
}


STATE = {
    "todo_list": {
        "todos": [],
        "revision": 0,
    }
}


_VALID_STATUS = ("pending", "in_progress", "completed", "cancelled")


def _normalize_todo(items: List[dict]) -> List[dict]:
    seen, out = set(), []
    for item in items:
        _id = str(item.get("id") or "").strip() or uuid.uuid4().hex[:8]
        if _id in seen:
            continue
        seen.add(_id)
        st = item.get("status") if item.get("status") in _VALID_STATUS else "pending"
        item = {"id": _id, "content": str(
            item.get("content") or "").strip(), "status": st}
        if item.get("parent"):
            item["parent"] = str(item["parent"])
        out.append(item)
    return out


def _todo_status(todos: List[dict]):
    status = {
        "total": len(todos),
        "pending": 0,
        "in_progress": 0,
        "completed": 0,
        "cancelled": 0,
    }
    for item in todos:
        if item["status"] == "pending":
            status["pending"] += 1
        if item["status"] == "in_progress":
            status["in_progress"] += 1
        if item["status"] == "completed":
            status["completed"] += 1
        if item["status"] == "cancelled":
            status["cancelled"] += 1
    return status


@tool(name="todo_list", schema=TODO_SCHEMA)
def todo_list(todos: Optional[List[dict]] = None, merge: bool = False) -> str:
    """Plan before do anything."""
    store = STATE["todo_list"]

    if todos is None:
        return json.dumps({
            **store,
            "summary": _todo_status(store["todos"]),
        }, ensure_ascii=False)

    if not isinstance(todos, list):
        return json.dumps({"error": "todos must be a list"}, ensure_ascii=False)

    items_before = store["todos"]
    if merge is True:
        items_by_id = {item.get("id"): dict(item) for item in items_before}
        for item in todos:
            _id = str(item.get("id") or "").strip()
            if not _id:
                continue
            if _id in items_by_id:
                for key in ('content', 'status', 'parent'):
                    if key in item:
                        items_by_id[_id][key] = item.get(key)
            else:
                items_by_id[_id] = {
                    "id": _id,
                    "content": item.get("content", ""),
                    "status": item.get("status", "pending")
                }
        items = _normalize_todo(list(items_by_id.values()))
    else:
        items = _normalize_todo(todos)

    store['todos'] = items
    if store['todos'] != items_before:
        store['revision'] += 1
    return json.dumps({
        "todos": items,
        "revision": store['revision'],
        "summary": _todo_status(items)
    }, ensure_ascii=False)
