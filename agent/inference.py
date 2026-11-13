"""LLM inference service"""

from __future__ import annotations
import logging
from typing import List

from openai import OpenAI


logger = logging.getLogger(__name__)


AGENT_MODEL = "google/gemma-4-26b-a4b-qat"
VISION_MODEL = "google/gemma-4-26b-a4b-qat"
MODEL_PROVIDER_BASE_URL = "http://127.0.0.1:1234/v1"
MODEL_PROVIDER_TOKEN = "-"

openai_client = OpenAI(
    base_url=MODEL_PROVIDER_BASE_URL,
    api_key=MODEL_PROVIDER_TOKEN
)


def call_model(messages: List[dict], tools: List[dict]) -> dict:
    """Call LLM with defined tools."""
    try:
        response = openai_client.responses.create(
            model=AGENT_MODEL,
            input=messages,
            tools=tools,
        )
        return response
    except Exception as e:
        raise ValueError(f"An error occurred: {e}")


def call_vqa_model(messages: List[dict]) -> dict:
    """Call VQA model."""
    try:
        response = openai_client.responses.create(
            model=VISION_MODEL,
            input=messages,
        )
        return response
    except Exception as e:
        raise ValueError(f"An error occurred: {e}")
