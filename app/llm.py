"""
llm.py — Centralized LLM client for PermitAgent.

Provides a single function that all agents call to get structured JSON
responses from OpenAI. Includes fallback to heuristics when unavailable.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI, OpenAIError

from app.config import OPENAI_API_KEY, LLM_MODEL, OPENAI_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

# Initialize client (lazy — will fail gracefully if key is missing)
_client: OpenAI | None = None
_llm_unavailable = False


def _get_client() -> OpenAI | None:
    """Get or create the OpenAI client. Returns None if no valid key."""
    global _client
    if _llm_unavailable:
        return None
    if _client is not None:
        return _client
    if not OPENAI_API_KEY or OPENAI_API_KEY == "sk-placeholder":
        return None
    try:
        _client = OpenAI(
            api_key=OPENAI_API_KEY,
            timeout=OPENAI_TIMEOUT_SECONDS,
            max_retries=0,
        )
        return _client
    except Exception as e:
        logger.error("Failed to initialize OpenAI client: %s", e)
        return None


def llm_call(
    prompt: str,
    system: str = "",
    temperature: float = 0.2,
    max_tokens: int = 4096,
) -> dict[str, Any] | None:
    """
    Call OpenAI and return parsed JSON.

    Returns a dict if the LLM returns valid JSON, or None if:
    - No API key is configured
    - The API call fails
    - The response is not valid JSON

    Agents should always have heuristic fallback logic for when this
    returns None.
    """
    global _llm_unavailable
    client = _get_client()
    if client is None:
        if not _llm_unavailable:
            logger.warning("No OpenAI API key configured or LLM unavailable — using heuristic fallback.")
        return None

    try:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        text = response.choices[0].message.content.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]).strip()

        return json.loads(text)

    except OpenAIError as e:
        logger.error("OpenAI API error: %s", e)
        _llm_unavailable = True
        return None
    except json.JSONDecodeError:
        logger.error("LLM returned non-JSON response: %s", text[:200])
        return None
    except Exception as e:
        logger.error("Unexpected error in LLM call: %s", e)
        _llm_unavailable = True
        return None
