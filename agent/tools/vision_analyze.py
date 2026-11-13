"""Agent Vision tool."""

from __future__ import annotations
import base64
import io
import json
import logging
from typing import List

import aiohttp

from agent.inference import call_vqa_model
from agent.registry import tool
from agent.utils import run_sync


logger = logging.getLogger(__name__)


VISION_ANALYZE_SCHEMA = {
    "type": "function",
    "name": "vision_analyze",
    "description": """
        Describe images by source URL and answer questions about them.
        Provide a detailed description of the image content, including objects,
        people, text, and any other relevant information.
        Use the provided question to focus your analysis and provide a clear and concise answer.
    """,
    "parameters": {
        "type": "object",
        "properties": {
            "sources": {
                "type": "array",
                "items": {
                    "type": "string"
                }
            },
            "question": {
                "type": "string"
            }
        },
        "required": ["sources", "question"]
    }
}


def _is_local_file(path: str) -> bool:
    return not (path.startswith("http://") or path.startswith("https://"))


async def _image_to_url(image_url: str) -> str:
    """Convert image data to data URL."""
    try:
        if _is_local_file(image_url):
            return image_url
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as response:
                    if response.status != 200:
                        raise ValueError(
                            f"Failed to fetch image from {image_url}:\
                                {response.status}")
                    image_data = await response.read()
                    image_bytes = io.BytesIO(image_data)
        return 'data:image/jpeg;base64,' \
            + base64.b64encode(image_bytes.getvalue()).decode("utf-8")
    except Exception as e:
        raise ValueError(f"Error fetching image from {image_url}: {e}")


@tool(name="vision_analyze", schema=VISION_ANALYZE_SCHEMA)
def vision_analyze(sources: List[str], question: str) -> str:
    """Analyze image."""
    content = [
        {
            "type": "input_text",
            "text": question
        },
    ]
    for source in sources:
        try:
            image_url = run_sync(_image_to_url(source))
            content.append({
                "type": "input_image",
                "image_url": image_url
            })
        except Exception as e:
            return json.dumps({
                "error": str(e)
            }, ensure_ascii=False)

    messages = [{"role": "user", "content": content}]

    try:
        response = call_vqa_model(messages=messages)
    except Exception as e:
        return json.dumps({
            "error": str(e)
        }, ensure_ascii=False)

    return json.dumps({
        "response": response.output_text,
    }, ensure_ascii=False)
