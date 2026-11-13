"""Logging setup for the agent."""

from __future__ import annotations
import logging
import os
from pathlib import Path

from agent.config import BASE_PATH


LOG_PATH = BASE_PATH / Path("logs/agent.log")


def configure_logging():
    """Configure logging for the agent."""
    os.makedirs(LOG_PATH.parent, exist_ok=True)
    logging.basicConfig(
        encoding="utf-8",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
            logging.StreamHandler(),          # stdout
        ],
    )
