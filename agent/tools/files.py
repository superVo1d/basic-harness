import fnmatch
import json
import re
from pathlib import Path

from agent.registry import tool
from agent.workspace import workspace_path

MAX_MATCH_LINE = 300


READ_FILE_SCHEMA = {
    "type": "function",
    "name": "read_file",
    "description": (
        "Read a text file from the session workspace. Lines are 1-indexed. "
        "Use offset/limit to page large files."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path relative to the workspace."},
            "offset": {"type": "integer", "default": 1, "description": "First line to return (1-indexed)."},
            "limit": {"type": "integer", "default": 2000, "description": "Maximum number of lines."},
        },
        "required": ["path"],
    },
}


def _resolve(session_id: str, rel: str) -> Path | None:
    """Resolve a workspace-relative path, refusing escapes."""
    if not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
        return None
    root = workspace_path(session_id).resolve()
    target = (root / rel).resolve()
    if target != root and root not in target.parents:
        return None
    return target


@tool(name="read_file", schema=READ_FILE_SCHEMA)
def read_file(ctx: dict, path: str, offset: int = 1, limit: int = 2000) -> str:
    """Read a file from the session workspace."""
    target = _resolve((ctx or {}).get("session_id", ""), path)
    if target is None:
        return json.dumps({"error": "invalid path"}, ensure_ascii=False)
    try:
        lines = target.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return json.dumps({"error": f"file not found: {path}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    start = max(1, int(offset)) - 1
    chunk = lines[start:start + max(0, int(limit))]
    return json.dumps({
        "content": "\n".join(chunk),
        "total_lines": len(lines),
        "offset": start + 1,
        "returned": len(chunk),
    }, ensure_ascii=False)


WRITE_FILE_SCHEMA = {
    "type": "function",
    "name": "write_file",
    "description": (
        "Write content to a file in the session workspace (creates parent dirs, "
        "overwrites). Use for scripts, reports and any artifact."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path relative to the workspace."},
            "content": {"type": "string", "description": "Full file content."},
        },
        "required": ["path", "content"],
    },
}


PATCH_SCHEMA = {
    "type": "function",
    "name": "patch",
    "description": (
        "Replace an exact substring in a workspace file. Fails if old_string is not "
        "found, or occurs more than once unless replace_all is true."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path relative to the workspace."},
            "old_string": {"type": "string", "description": "Exact text to replace."},
            "new_string": {"type": "string", "description": "Replacement text."},
            "replace_all": {"type": "boolean", "default": False,
                            "description": "Replace every occurrence instead of requiring uniqueness."},
        },
        "required": ["path", "old_string", "new_string"],
    },
}


SEARCH_FILES_SCHEMA = {
    "type": "function",
    "name": "search_files",
    "description": (
        "Search the session workspace. target='content' matches a regex inside files "
        "(returns file/line/text); target='files' matches paths by glob or substring."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "pattern": {"type": "string", "description": "Regex (content) or glob/substring (files)."},
            "target": {"type": "string", "enum": ["content", "files"], "default": "content"},
            "path": {"type": "string", "default": ".", "description": "Directory to search, relative to the workspace."},
            "limit": {"type": "integer", "default": 50, "description": "Maximum matches."},
        },
        "required": ["pattern"],
    },
}


@tool(name="write_file", schema=WRITE_FILE_SCHEMA)
def write_file(ctx: dict, path: str, content: str) -> str:
    """Write a file into the session workspace."""
    target = _resolve((ctx or {}).get("session_id", ""), path)
    if target is None:
        return json.dumps({"error": "invalid path"}, ensure_ascii=False)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    return json.dumps({"path": path, "bytes": len(content.encode("utf-8"))}, ensure_ascii=False)


@tool(name="patch", schema=PATCH_SCHEMA)
def patch(ctx: dict, path: str, old_string: str, new_string: str, replace_all: bool = False) -> str:
    """Replace an exact substring in a workspace file."""
    target = _resolve((ctx or {}).get("session_id", ""), path)
    if target is None:
        return json.dumps({"error": "invalid path"}, ensure_ascii=False)
    try:
        text = target.read_text(encoding="utf-8")
    except FileNotFoundError:
        return json.dumps({"error": f"file not found: {path}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    count = text.count(old_string)
    if count == 0:
        return json.dumps({"error": "old_string not found"}, ensure_ascii=False)
    if count > 1 and not replace_all:
        return json.dumps({"error": f"old_string occurs {count} times; add context or set replace_all"}, ensure_ascii=False)
    target.write_text(text.replace(old_string, new_string, -1 if replace_all else 1), encoding="utf-8")
    return json.dumps({"path": path, "replaced": count if replace_all else 1}, ensure_ascii=False)


@tool(name="search_files", schema=SEARCH_FILES_SCHEMA)
def search_files(ctx: dict, pattern: str, target: str = "content", path: str = ".", limit: int = 50) -> str:
    """Search files in the session workspace by content or path."""
    session_id = (ctx or {}).get("session_id", "")
    base = _resolve(session_id, path or ".")
    if base is None or not base.exists():
        return json.dumps({"error": f"invalid search path: {path}"}, ensure_ascii=False)
    root = workspace_path(session_id)
    limit = max(1, int(limit))
    matches: list = []

    if target == "files":
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rel = p.relative_to(root).as_posix()
            if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(p.name, pattern) or pattern in rel:
                matches.append(rel)
            if len(matches) >= limit:
                break
        return json.dumps({"matches": matches}, ensure_ascii=False)

    try:
        rx = re.compile(pattern)
    except re.error as e:
        return json.dumps({"error": f"bad regex: {e}"}, ensure_ascii=False)

    for p in sorted(base.rglob("*")):
        if not p.is_file():
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                matches.append({"path": p.relative_to(root).as_posix(), "line": i, "text": line[:MAX_MATCH_LINE]})
                if len(matches) >= limit:
                    break
        if len(matches) >= limit:
            break
    return json.dumps({"matches": matches}, ensure_ascii=False)
