"""
shared/llm_client.py
Thin wrapper around the Anthropic API for use by all agents.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any

import anthropic

logger = logging.getLogger(__name__)

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY is not set.")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def call_claude(
    system: str,
    user: str,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 8192,
    expect_json: bool = False,
) -> str:
    """
    Call Claude and return the text response.
    If expect_json=True, strips markdown fences before returning.
    """
    client = get_client()
    logger.debug("Calling Claude | model=%s | expect_json=%s", model, expect_json)

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = response.content[0].text

    if expect_json:
        text = _strip_json_fences(text)

    return text


def call_claude_json(
    system: str,
    user: str,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 8192,
) -> Any:
    """Call Claude and parse the response as JSON."""
    raw = call_claude(system=system, user=user, model=model, max_tokens=max_tokens, expect_json=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON response: %s\nRaw: %s", e, raw[:500])
        raise


def _strip_json_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers."""
    text = text.strip()
    for fence in ("```json", "```"):
        if text.startswith(fence):
            text = text[len(fence):]
            break
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()
