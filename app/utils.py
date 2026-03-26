"""
utils.py — Shared utility functions for the PermitAgent pipeline.
"""

from __future__ import annotations

import json
import uuid
from typing import Any


def generate_scene_id() -> str:
    """Generate a unique scene identifier."""
    return f"scene_{uuid.uuid4().hex[:8]}"


def placeholder_llm_call(prompt: str, system: str = "") -> dict[str, Any]:
    """
    Placeholder for an LLM API call.

    In production, this would call OpenAI / Anthropic / local model.
    For now it returns an empty dict so the pipeline can run end-to-end
    without external dependencies.

    TODO: Replace with real LLM integration.
    """
    # Log the prompt length for debugging
    _ = len(prompt)
    return {}


def load_json_file(path: str) -> Any:
    """Load and parse a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def safe_get(data: dict, *keys: str, default: Any = None) -> Any:
    """Safely traverse nested dicts."""
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, default)
        else:
            return default
    return current
