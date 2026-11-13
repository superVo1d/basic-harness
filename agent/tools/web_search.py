"""Agent Vision tool."""

from __future__ import annotations

import json
import logging
from typing import List

from tavily import TavilyClient

from agent.config import Settings
from agent.registry import tool

logger = logging.getLogger(__name__)

settings = Settings()


def _client() -> TavilyClient | None:
    return TavilyClient(api_key=settings.tavily_api_key) if settings.tavily_api_key else None


def _available() -> bool:
    return bool(settings.tavily_api_key)


WEB_SEARCH_SCHEMA = {
    "type": "function",
    "name": "web_search",
    "description": "Search the web. Returns titles, URLs and snippets.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "limit": {"type": "integer", "default": 5, "description": "Max results."},
        },
        "required": ["query"],
    },
}


@tool(name="web_search", schema=WEB_SEARCH_SCHEMA, check_fn=_available)
def web_search(query: str, limit: int = 5) -> str:
    """Search the web for information."""
    client = _client()
    if client is None:
        return json.dumps({"error": "tavily_api_key is not set"}, ensure_ascii=False)
    try:
        result = client.search(query, max_results=limit)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    return json.dumps({"results": result.get("results", [])}, ensure_ascii=False)


WEB_EXTRACT_SCHEMA = {
    "type": "function",
    "name": "web_extract",
    "description": "Extract clean page content from URLs (max 5).",
    "parameters": {
        "type": "object",
        "properties": {
            "urls": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["urls"],
    },
}


@tool(name="web_extract", schema=WEB_EXTRACT_SCHEMA, check_fn=_available)
def web_extract(urls: List[str]) -> str:
    """Extract information from the web."""
    client = _client()
    if client is None:
        return json.dumps({"error": "tavily_api_key is not set"}, ensure_ascii=False)
    try:
        result = client.extract(urls[:5])
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    return json.dumps({"results": result}, ensure_ascii=False)
